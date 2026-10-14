"""C2.2: the bake-off sample, blind sheet and scoring (no models, no Colab)."""

from pathlib import Path

import pytest

from finsight.risks.bakeoff import (
    TIE,
    build_sheet,
    critical_drop_rate,
    pick,
    read_sheet,
    sample_risks,
    score,
    wilson,
    write_sheet,
)
from finsight.risks.filters import Kept
from finsight.risks.teacher import TeacherOutput
from finsight.risks.teacher_input import Candidate


def cand(company: str, i: int, year: int) -> Candidate:
    return Candidate(
        f"{company}-{year}#r{i}", f"{company}-{year}", company, year, f"T{i}", "w " * 60
    )


def kept(rid: str, text: str = "plain") -> Kept:
    out = TeacherOutput(
        category="financial", seriousness_1to5=3, hard_fact=True, simple=text, numbers_copied=[]
    )
    return Kept(rid, f"original of {rid}", out)


def test_sample_is_spread_over_years_and_companies_and_deterministic() -> None:
    cands = [cand(f"C{c}", i, 2019 + c % 6) for c in range(60) for i in range(8)]
    a = sample_risks(cands, 120)
    b = sample_risks(list(reversed(cands)), 120)
    assert len(a) == 120
    assert [c.risk_id for c in a] == [c.risk_id for c in b]
    years = {c.year for c in a}
    assert years == set(range(2019, 2025))
    assert len({c.company for c in a}) >= 60  # round robin: every company before a second risk


def test_sheet_is_blind_paired_and_shuffled(tmp_path: Path) -> None:
    ids = [f"x#r{i}" for i in range(80)]
    kept_by = {
        "qwen-14b": [kept(r, "a") for r in ids],
        "qwen-32b": [kept(r, "b") for r in ids[:70]],
    }
    rows, key = build_sheet(kept_by, n_risks=50)
    assert len(rows) == 100
    assert "model" not in rows[0]  # the sheet never names the model
    assert all(set(r) & {"model", "teacher"} == set() for r in rows)
    # paired: each chosen risk appears once per model, and only risks both models kept
    per_risk: dict[str, set[str]] = {}
    for v in key.values():
        per_risk.setdefault(v["risk_id"], set()).add(v["model"])
    assert all(models == {"qwen-14b", "qwen-32b"} for models in per_risk.values())
    assert all(int(r.split("r")[-1]) < 70 for r in per_risk)
    # shuffled: the first ten rows are not all one model
    assert len({key[r["sheet_id"]]["model"] for r in rows[:10]}) == 2
    write_sheet(rows, tmp_path / "s.csv")
    assert len(read_sheet(tmp_path / "s.csv")) == 100


def rated(key: dict, rule) -> list[dict[str, str]]:
    return [
        {
            "sheet_id": sid,
            **dict(zip(("faithful", "category_correct"), rule(v["model"], i), strict=True)),
        }
        for i, (sid, v) in enumerate(key.items())
    ]


REPORTS = {
    "qwen-14b": {"kept": 280, "total": 300, "dropped": {"number_mismatch": 12}},
    "qwen-32b": {"kept": 285, "total": 300, "dropped": {"number_mismatch": 3}},
}


def test_score_maps_blind_ratings_back_to_models() -> None:
    key = {
        f"s{i:03d}": {"model": "qwen-14b" if i % 2 else "qwen-32b", "risk_id": f"r{i}"}
        for i in range(100)
    }
    rows = rated(key, lambda m, i: ("yes", "yes") if m == "qwen-32b" else ("partly", "no"))
    res = score(rows, key, REPORTS, {"qwen-14b": 100.0, "qwen-32b": 300.0})
    assert res["models"]["qwen-32b"]["faithful_yes_share"] == 1.0
    assert res["models"]["qwen-14b"]["faithful_yes_share"] == 0.0
    assert res["models"]["qwen-14b"]["category_correct_share"] == 0.0
    assert res["pick"]["model"] == "qwen-32b"
    assert res["models"]["qwen-32b"]["drop_rate_total"] == pytest.approx(0.05)
    assert res["models"]["qwen-14b"]["drop_rate_critical"] == pytest.approx(0.04)


def test_unrated_rows_are_refused() -> None:
    key = {"s001": {"model": "qwen-14b", "risk_id": "r1"}}
    with pytest.raises(ValueError, match="unrated"):
        score([{"sheet_id": "s001", "faithful": "", "category_correct": "yes"}], key, REPORTS, {})


def models(
    y14: float, y32: float, d14: float = 0.05, d32: float = 0.05, s14: float = 1, s32: float = 2
):
    return {
        "a": {"faithful_yes_share": y14, "drop_rate_critical": d14, "seconds": s14},
        "b": {"faithful_yes_share": y32, "drop_rate_critical": d32, "seconds": s32},
    }


def test_pick_rule_in_order() -> None:
    assert TIE == 0.05  # C-ADR-05 as accepted by Akshat
    assert pick(models(0.70, 0.90))["model"] == "b"  # quality first
    assert pick(models(0.90, 0.70))["model"] == "a"
    # within the tie band: lower critical drop rate wins
    assert pick(models(0.80, 0.80 + TIE / 2, d14=0.02, d32=0.08))["model"] == "a"
    assert pick(models(0.80, 0.80 + TIE, d14=0.02, d32=0.08))["model"] == "a"  # edge is a tie
    # still tied: the faster run
    assert pick(models(0.80, 0.80, 0.05, 0.05, s14=300, s32=100))["model"] == "b"


def test_pick_rule_with_three_models() -> None:
    m = {
        "qwen3.8": {"faithful_yes_share": 0.86, "drop_rate_critical": 0.06, "seconds": 70},
        "gemma4": {"faithful_yes_share": 0.90, "drop_rate_critical": 0.03, "seconds": 140},
        "qwen3-32b": {"faithful_yes_share": 0.70, "drop_rate_critical": 0.00, "seconds": 80},
    }
    res = pick(m)
    # qwen3-32b is outside the band (0.20 behind) even with the fewest critical drops
    assert res["tied"] == ["gemma4", "qwen3.8"]
    assert res["model"] == "gemma4"
    m["qwen3.8"]["drop_rate_critical"] = 0.03  # equal critical drops: faster wins
    assert pick(m)["model"] == "qwen3.8"
    m["gemma4"]["faithful_yes_share"] = 0.95  # 0.09 ahead: quality alone decides
    assert pick(m) == {"model": "gemma4", "tied": ["gemma4"],
                       "because": "faithful=yes share higher by 0.090 (> 0.05)"}  # fmt: skip


def test_critical_drop_rate_counts_numbers_and_certainty_only() -> None:
    rep = {"total": 300, "kept": 270,
           "dropped": {"number_mismatch": 9, "certainty_changed": 3, "too_long": 18}}  # fmt: skip
    assert critical_drop_rate(rep) == 0.04
    assert critical_drop_rate({"total": 0}) is None


def test_three_model_sheet_has_150_blind_rows() -> None:
    ids = [f"x#r{i}" for i in range(90)]
    kept_by = {m: [kept(r, m) for r in ids] for m in ("gemma", "qwen38", "qwen32")}
    rows, key = build_sheet(kept_by)
    assert len(rows) == 150
    assert {v["model"] for v in key.values()} == {"gemma", "qwen38", "qwen32"}
    per_risk: dict[str, set[str]] = {}
    for v in key.values():
        per_risk.setdefault(v["risk_id"], set()).add(v["model"])
    assert len(per_risk) == 50
    assert all(len(ms) == 3 for ms in per_risk.values())
    assert len({key[r["sheet_id"]]["model"] for r in rows[:10]}) >= 2


def test_wilson_interval_is_sane() -> None:
    lo, hi = wilson(40, 50)
    assert lo < 0.8 < hi
    assert wilson(0, 0) == (0.0, 0.0)
