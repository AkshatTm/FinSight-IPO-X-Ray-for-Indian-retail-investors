"""Gold-150 / gold-50 sampling, sheets and scoring (C2.4, C2.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from finsight.risks.gold_sets import (
    CATEGORY_COLUMNS,
    category_gold,
    category_sheet,
    pick,
    read_csv,
    rewrite_sheet,
    score_rewrites,
    write_csv,
)
from finsight.risks.teacher_input import Candidate

BODY = " ".join(["word"] * 60)


def _by_ipo(n_ipos: int = 12, per: int = 20) -> dict[str, list[Candidate]]:
    return {
        f"ipo{i:02d}": [
            Candidate(f"ipo{i:02d}#r{j:02d}", f"ipo{i:02d}", f"Co {i}", 2024, f"T{j}", BODY)
            for j in range(per)
        ]
        for i in range(n_ipos)
    }


def test_pick_counts_disjoint_and_deterministic() -> None:
    by = _by_ipo()
    a = pick(by, 10, 15)
    assert len(a) == 150
    assert len({c.ipo_id for c in a}) == 10
    assert a == pick(by, 10, 15)
    b = pick(by, 2, 5, exclude_ipos={c.ipo_id for c in a})
    assert not {c.ipo_id for c in a} & {c.ipo_id for c in b}


def test_pick_skips_short_and_raises_when_too_few() -> None:
    by = _by_ipo(3, 5)
    by["ipo00"] = [Candidate("x#1", "ipo00", "C", 2024, "t", "too short")] * 5
    with pytest.raises(ValueError, match="eligible"):
        pick(by, 3, 5)
    assert len(pick(by, 2, 5)) == 10


def test_category_sheet_and_gold() -> None:
    risks = pick(_by_ipo(), 1, 3)
    pre = {risks[0].risk_id: "legal", risks[1].risk_id: "financial"}
    rows = category_sheet(risks, pre)
    assert [r["category"] for r in rows] == ["legal", "financial", ""]
    rows[1]["category"] = "legal"
    rows[2]["category"] = "market"
    gold, stats = category_gold(rows, pre, ["legal", "financial", "market"])
    assert [g["label"] for g in gold] == ["legal", "legal", "market"]
    assert stats == {"n": 3, "changed_from_prefill": 2, "changed_share": 0.6667}
    rows[0]["category"] = "nope"
    with pytest.raises(ValueError, match="not one of"):
        category_gold(rows, pre, ["legal"])


def test_rewrite_sheet_blind_and_score() -> None:
    risks = pick(_by_ipo(), 2, 2)
    out = {s: {c.risk_id: f"{s} text" for c in risks} for s in ("base", "student", "teacher")}
    del out["base"][risks[0].risk_id]  # that risk is dropped for every system
    rows, key = rewrite_sheet(risks, out)
    assert len(rows) == 9
    assert set(key) == {r["sheet_id"] for r in rows}
    assert "system" not in rows[0]
    for r in rows:
        r["faithful"] = "yes" if key[r["sheet_id"]]["system"] == "teacher" else "partly"
        r["plain_english_1to5"] = "4"
    res = score_rewrites(rows, key)
    assert res["teacher"]["faithful_yes_share"] == 1.0
    assert res["base"]["faithful"] == {"partly": 3}
    assert res["base"]["plain_english_mean"] == 4
    rows[0]["faithful"] = ""
    with pytest.raises(ValueError, match="unrated"):
        score_rewrites(rows, key)


def test_csv_roundtrip(tmp_path: Path) -> None:
    rows = category_sheet(pick(_by_ipo(), 1, 2), {})
    p = tmp_path / "s.csv"
    write_csv(rows, CATEGORY_COLUMNS, p)
    assert read_csv(p) == rows
    assert b"\r\n" not in p.read_bytes()
