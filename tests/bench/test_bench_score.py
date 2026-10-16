"""Task A / B scoring in ``scripts/bench_score.py``: model answers scored by the E14 rules."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import bench_score  # noqa: E402
import summary_eval  # noqa: E402

from finsight.redflags import evaluate, inputs_from_gold  # noqa: E402


def _fa(status: str, value: str = "", unit: str = "", page: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(status=status, value=value, unit=unit, page=page)


def _gold(key: str, raw: str, unit: str, status: str = "found", period: str = "latest") -> dict:
    return {"key": key, "period": period, "value_raw": raw, "unit": unit, "status": status,
            "page": 30}  # fmt: skip


def _score(gold: dict, fa: SimpleNamespace | None) -> dict:
    row = bench_score.model_row(gold["key"], gold["period"], fa)
    return bench_score.score_pred(gold, bench_score.pred_from_row(row))


def test_money_in_another_unit_matches() -> None:
    g = _gold("revenue", "17,538", "₹ million")
    assert _score(g, _fa("found", "1,753.8", "₹ crore", 30))["correct"]
    r = _score(g, _fa("found", "17,538", "₹ crore", 31))
    assert not r["correct"]
    assert r["scale_error"]
    assert r["page_match"] is False


def test_loss_in_brackets_and_minus_sign_agree() -> None:
    g = _gold("profit_after_tax", "(8,049.41)", "₹ million")
    assert _score(g, _fa("found", "-8,049.41", "₹ million"))["correct"]


def test_blank_gold_needs_the_same_status() -> None:
    g = _gold("general_purposes_pct_of_fresh", "[●]", "", status="placeholder", period="final")
    assert _score(g, _fa("placeholder", "[●]"))["correct"]
    assert not _score(g, _fa("found", "25", "%"))["correct"]
    missing = _gold("customer_top1_pct", "", "%", status="not_found")
    assert _score(missing, None)["correct"]  # no answer for an absent fact is right


def test_stated_zero_and_percentages() -> None:
    g = _gold("pledged_promoter_pct", "0 (Nil)", "%", status="stated_zero", period="final")
    assert _score(g, _fa("stated_zero", "Nil", "%"))["correct"]
    pct = _gold("promoter_holding_post_pct", "85.00 (computed)", "%", period="final")
    assert _score(pct, _fa("found", "85.02", "%"))["correct"]
    assert not _score(pct, _fa("found", "75", "%"))["correct"]


def test_score_pred_agrees_with_e14_score_row() -> None:
    """For the pipeline's own prediction both scorers give the same verdict."""
    g = _gold("net_worth", "48,553.47", "₹ million")
    pred = summary_eval.Pred("found", summary_eval.gold_value(g), 30)

    class _Summary:  # only the attribute ``predicted`` reads for net_worth
        pass

    original = summary_eval.predicted
    try:
        summary_eval.predicted = lambda *_: pred  # type: ignore[assignment]
        e14 = summary_eval.score_row(g | {"ipo_id": "x"}, _Summary())  # type: ignore[arg-type]
    finally:
        summary_eval.predicted = original
    assert e14["correct"] == bench_score.score_pred(g, pred)["correct"] is True


def test_model_rows_feed_the_red_flag_engine() -> None:
    rows = [
        bench_score.model_row("profit_after_tax", p, _fa("found", v, "₹ million"))
        for p, v in (("latest", "(100)"), ("latest-1", "(90)"), ("latest-2", "(80)"))
    ]
    flags = {f.id: f.status for f in evaluate(inputs_from_gold("x", rows)).flags}
    assert flags["RF01"] == "concern"  # a loss in each of the last 3 years


def test_failures_pick_round_robin() -> None:
    rows = {
        "s1": {"A": [{"item_id": f"a{i}", "correct": False} for i in range(5)], "C": [],
               "G": [], "D": [], "B": []},
        "s2": {"A": [], "C": [{"item_id": "c1", "correct": False}], "G": [], "D": [], "B": []},
    }  # fmt: skip
    picked = bench_score.failures(rows, n=3)
    first, second = sorted(
        (f"a{i}" for i in range(5)), key=lambda x: hashlib.sha256(x.encode()).hexdigest()
    )[:2]  # a fixed shuffle, the same on every run
    assert [(p["system"], p["item_id"]) for p in picked] == [
        ("s1", first),
        ("s2", "c1"),
        ("s1", second),
    ]
    assert bench_score.failures(rows, n=3) == picked
