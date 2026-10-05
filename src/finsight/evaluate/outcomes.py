"""Outcome validation of the risk level (C2.8, E21): does the score say anything about what
happened after listing?

This module is **evaluation only**. Listing outcomes (prices, gains) must never reach the product,
a threshold fit or a prompt: ``tests/evaluate/test_outcomes_guard.py`` fails if any module outside
``finsight.evaluate`` imports it. The score used here is the **risk-points-only** variant (the
corpus years have no tables, so no red flags), which is weaker than the score the product shows;
the result says so (``LIMITATION``). Whatever the numbers show is reported as it is.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

LIMITATION = (
    "risk-points-only score (no red flags: the corpus years have no tables), a weaker variant of "
    "the score the product shows; one outcome measure; correlation is not a prediction and "
    "FinSight gives no investment advice"
)
MIN_N = 20


def _ranks(values: Sequence[float]) -> np.ndarray:
    """Average ranks (ties share the mean rank)."""
    a = np.asarray(values, dtype=float)
    order = a.argsort(kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman rank correlation (``nan`` when either side is constant)."""
    rx, ry = _ranks(x), _ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def permutation_p(x: Sequence[float], y: Sequence[float], n: int = 2000, seed: int = 2026) -> float:
    """Two-sided permutation p-value of the Spearman correlation (seeded)."""
    observed = abs(spearman(x, y))
    rng = random.Random(seed)
    ys = list(y)
    hits = 0
    for _ in range(n):
        rng.shuffle(ys)
        if abs(spearman(x, ys)) >= observed:
            hits += 1
    return (hits + 1) / (n + 1)


def level_table(
    scores: Mapping[str, float], outcomes: Mapping[str, float], low: float, high: float
) -> list[dict[str, Any]]:
    """Outcome summary per level (low / medium / high), using the fitted thresholds."""
    groups: dict[str, list[float]] = {"low": [], "medium": [], "high": []}
    for ipo_id, s in scores.items():
        if ipo_id in outcomes:
            groups["low" if s < low else "high" if s >= high else "medium"].append(outcomes[ipo_id])
    return [
        {
            "level": level,
            "n": len(v),
            "mean": round(float(np.mean(v)), 3) if v else None,
            "median": round(float(np.median(v)), 3) if v else None,
        }
        for level, v in groups.items()
    ]


def validate(
    scores: Mapping[str, float],
    outcomes: Mapping[str, float],
    thresholds: Mapping[str, float],
    outcome_name: str = "listing_gain_pct",
) -> dict[str, Any]:
    """E21 record: Spearman rho with a permutation p-value and the per-level table.

    Raises:
        ValueError: with fewer than ``MIN_N`` IPOs that have both a score and an outcome.
    """
    ids = sorted(set(scores) & set(outcomes))
    if len(ids) < MIN_N:
        raise ValueError(f"only {len(ids)} IPOs have both a score and an outcome; need {MIN_N}")
    x, y = [scores[i] for i in ids], [outcomes[i] for i in ids]
    rho = spearman(x, y)
    return {
        "outcome": outcome_name,
        "n": len(ids),
        "spearman_rho": None if rho != rho else round(rho, 4),
        "permutation_p": round(permutation_p(x, y), 4),
        "by_level": level_table(scores, outcomes, thresholds["low_below"], thresholds["high_from"]),
        "variant": "risk-points-only",
        "limitation": LIMITATION,
    }
