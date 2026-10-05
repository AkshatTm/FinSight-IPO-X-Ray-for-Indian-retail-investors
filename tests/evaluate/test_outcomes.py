"""C2.8: outcome validation (E21) and the guard that keeps outcomes out of the product."""

import math
from pathlib import Path

import pytest

from finsight.evaluate.outcomes import (
    LIMITATION,
    MIN_N,
    level_table,
    permutation_p,
    spearman,
    validate,
)

SRC = Path(__file__).resolve().parents[2] / "src" / "finsight"


def test_spearman_known_values() -> None:
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 2, 2, 3], [1, 2, 2, 3]) == pytest.approx(1.0)  # ties share a rank
    assert math.isnan(spearman([1, 1, 1], [1, 2, 3]))  # a constant side has no rank order


def test_permutation_p_is_small_for_a_real_trend_and_large_for_noise() -> None:
    x = list(range(30))
    assert permutation_p(x, [v * 2 for v in x], n=300) < 0.01
    noise = [(v * 7919) % 31 for v in x]
    assert permutation_p(x, noise, n=300) > 0.05
    assert permutation_p(x, noise, n=300) == permutation_p(x, noise, n=300)  # seeded


def test_level_table_uses_the_fitted_thresholds() -> None:
    scores = {"a": 0.1, "b": 0.3, "c": 0.5, "d": 0.9}
    outcomes = {"a": 10.0, "b": 20.0, "c": 30.0, "d": 40.0, "e": 99.0}  # e has no score
    rows = {r["level"]: r for r in level_table(scores, outcomes, 0.2, 0.5)}
    assert rows["low"]["n"] == 1
    assert rows["medium"]["n"] == 1
    assert rows["high"] == {"level": "high", "n": 2, "mean": 35.0, "median": 35.0}


def test_validate_reports_what_the_data_shows_and_the_limitation() -> None:
    ids = [f"ipo-{i}" for i in range(40)]
    scores = {i: n / 40 for n, i in enumerate(ids)}
    outcomes = {i: -float(n) for n, i in enumerate(ids)}  # higher score, worse outcome
    res = validate(scores, outcomes, {"low_below": 0.33, "high_from": 0.66})
    assert res["spearman_rho"] == pytest.approx(-1.0)
    assert res["n"] == 40
    assert res["variant"] == "risk-points-only"
    assert res["limitation"] == LIMITATION
    assert "no investment advice" in res["limitation"]


def test_validate_refuses_tiny_samples() -> None:
    few = {f"i{n}": float(n) for n in range(MIN_N - 1)}
    with pytest.raises(ValueError, match="need"):
        validate(few, few, {"low_below": 0.3, "high_from": 0.6})


def test_nothing_outside_evaluate_imports_outcomes() -> None:
    """Listing outcomes must never reach the product, a threshold fit or a prompt."""
    offenders = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC)
        if rel.parts[0] == "evaluate":
            continue
        text = path.read_text(encoding="utf-8")
        if "evaluate.outcomes" in text or "from finsight.evaluate import outcomes" in text:
            offenders.append(str(rel))
    assert offenders == []


def test_the_fitting_script_never_touches_outcomes() -> None:
    text = (SRC.parents[1] / "scripts" / "corpus_points.py").read_text(encoding="utf-8")
    code = text.split('"""', 2)[2]  # skip the docstring, which names the other script
    assert "outcomes" not in code
