"""Gold-150 / gold-50 sampling, sheets and scoring (C2.4, C2.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from finsight.risks.gold_sets import (
    CATEGORY_COLUMNS,
    agreement,
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
    # same text layout as the classifier's training rows (teacher_data.original_text)
    assert gold[0]["text"] == f"Title: {rows[0]['title']}\n\n{rows[0]['text']}"
    assert "band" not in gold[0]
    banded, _ = category_gold(rows, pre, ["legal", "financial", "market"], {rows[0]["risk_id"]: 4})
    assert [g["band"] for g in banded] == [4, None, None]
    rows[0]["category"] = "nope"
    with pytest.raises(ValueError, match="not one of"):
        category_gold(rows, pre, ["legal"])


def test_rewrite_sheet_blind_and_score() -> None:
    risks = pick(_by_ipo(), 2, 2)
    out = {
        s: {c.risk_id: {"text": f"{s} text", "check": ""} for c in risks}
        for s in ("base", "student", "teacher")
    }
    del out["base"][risks[0].risk_id]  # that risk is dropped for every system
    out["base"][risks[1].risk_id]["check"] = "too_long"  # rejected, but still rated
    rows, key = rewrite_sheet(risks, out)
    assert len(rows) == 9
    assert set(key) == {r["sheet_id"] for r in rows}
    assert "system" not in rows[0]
    assert "check" not in rows[0]
    for r in rows:
        r["faithful"] = "yes" if key[r["sheet_id"]]["system"] == "teacher" else "partly"
        r["plain_english_1to5"] = "4"
    res = score_rewrites(rows, key)
    assert res["teacher"]["faithful_yes_share"] == 1.0
    assert res["base"]["faithful"] == {"partly": 3}
    assert res["base"]["plain_english_mean"] == 4
    assert res["base"]["post_checks"] == {"passed": 2, "too_long": 1}
    assert res["base"]["passed_checks_share"] == 0.6667
    assert res["teacher"]["passed_checks_share"] == 1.0
    rows[0]["faithful"] = ""
    with pytest.raises(ValueError, match="unrated"):
        score_rewrites(rows, key)


def test_csv_roundtrip(tmp_path: Path) -> None:
    rows = category_sheet(pick(_by_ipo(), 1, 2), {})
    p = tmp_path / "s.csv"
    write_csv(rows, CATEGORY_COLUMNS, p)
    assert read_csv(p) == rows
    assert b"\r\n" not in p.read_bytes()


def test_agreement_per_gold_category() -> None:
    gold = {"a": "legal", "b": "legal", "c": "market", "d": "market"}
    pred = {"a": "legal", "b": "market", "c": "market"}  # d has no prediction
    out = agreement(gold, pred, ["legal", "market", "financial"])
    assert (out["n"], out["missing"], out["agree"], out["share"]) == (3, 1, 2, 0.6667)
    assert out["per_category"]["legal"] == {
        "n": 2, "agree": 1, "share": 0.5, "model_said": {"market": 1}
    }  # fmt: skip
    assert out["per_category"]["market"]["share"] == 1.0
    assert "financial" not in out["per_category"]
