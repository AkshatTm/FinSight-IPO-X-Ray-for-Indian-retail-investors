"""Reference scores for the risk level on the rolling window (C2.8, C-ADR-03).

Every collected IPO gets a risk-level score (``finsight.risklevel.compute``). For a document
dated ``as_of`` the deciles it is placed against come from the scores of the IPOs inside the
rolling reference window (``finsight.splits.ipos_before``), not from a fixed list of years.
The level thresholds (bottom and top third) are fitted on ``train`` and ``dev`` IPOs only; a
``test`` or ``bench`` IPO never shapes a threshold (C-ADR-02).

Scores live in a small CSV (``ipo_id,score``) written by ``scripts/corpus_points.py``.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from finsight.splits import RefKind, SplitsFile, ipos_before

FIT_SLICES = frozenset({"train", "dev"})
MIN_FIT_IPOS = 30  # fewer than this and terciles are noise


def write_scores(scores: Mapping[str, float], path: Path) -> None:
    """``ipo_id,score`` rows sorted by id (LF endings)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ipo_id", "score"])
        for ipo_id in sorted(scores):
            w.writerow([ipo_id, f"{scores[ipo_id]:.4f}"])


def read_scores(path: Path) -> dict[str, float]:
    """The score table (empty when the file does not exist yet)."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["ipo_id"]: float(r["score"]) for r in csv.DictReader(fh)}


def window_scores(
    scores: Mapping[str, float],
    splits: SplitsFile,
    as_of: date,
    years: int | None = None,
    *,
    kind: RefKind = "eval",
    exclude_ipo: str | None = None,
    exclude_company: str | None = None,
) -> list[float]:
    """Scores of the reference IPOs for a document dated ``as_of`` (those that have a score)."""
    entries = ipos_before(
        splits, as_of, years, kind=kind, exclude_ipo=exclude_ipo, exclude_company=exclude_company
    )
    return [scores[e.ipo_id] for e in entries if e.ipo_id in scores]


def deciles(values: Sequence[float] | np.ndarray) -> list[float]:
    """Scores at percentiles 0, 10, ..., 100 (the form ``risklevel.percentile`` takes)."""
    if len(values) == 0:
        raise ValueError("no reference scores")
    return [
        round(float(q), 4)
        for q in np.percentile(np.asarray(values, dtype=float), range(0, 101, 10))
    ]


def fit_thresholds(
    scores: Mapping[str, float], splits: SplitsFile, min_n: int = MIN_FIT_IPOS
) -> dict[str, Any]:
    """Bottom-third and top-third score cut-offs from ``train`` + ``dev`` IPOs only.

    Raises:
        ValueError: with too few IPOs, or when the scores are so concentrated that the two
            cut-offs coincide (no honest three-way split exists).
    """
    ids = [e.ipo_id for e in splits.ipos if e.slice in FIT_SLICES and e.ipo_id in scores]
    if len(ids) < min_n:
        raise ValueError(f"only {len(ids)} train/dev IPOs have a score; need at least {min_n}")
    values = np.asarray([scores[i] for i in ids], dtype=float)
    low, high = (round(float(np.percentile(values, p)), 4) for p in (100 / 3, 200 / 3))
    if low >= high:
        raise ValueError(f"scores are too concentrated: low_below {low} >= high_from {high}")
    return {
        "thresholds": {"low_below": low, "high_from": high},
        "reference_quantiles": deciles(values),
        "corpus_n": len(ids),
        "fit_ipos": sorted(ids),
    }


_LINES = {
    "provisional": re.compile(r"^provisional:.*$", re.M),
    "computed_on": re.compile(r"^computed_on:.*$", re.M),
    "corpus_n": re.compile(r"^corpus_n:.*$", re.M),
    "thresholds": re.compile(r"^thresholds:.*$", re.M),
    "reference_quantiles": re.compile(r"^reference_quantiles:.*$", re.M),
}


def apply_fit(text: str, fit: Mapping[str, Any], git_sha: str, window_years: int) -> str:
    """The config text with the fitted values written in (comments kept, ``provisional: false``).

    ``computed_on`` is a git sha (not a date): the commit whose scores the fit used.
    """
    th = fit["thresholds"]
    new = {
        "provisional": "provisional: false",
        "computed_on": f"computed_on: {git_sha}",
        "corpus_n": f"corpus_n: {fit['corpus_n']}",
        "thresholds": (
            f"thresholds: {{ low_below: {th['low_below']}, high_from: {th['high_from']} }}"
        ),
        "reference_quantiles": f"reference_quantiles: {list(fit['reference_quantiles'])}",
    }
    for key, pattern in _LINES.items():
        if len(pattern.findall(text)) != 1:
            raise ValueError(f"config must have exactly one top-level '{key}:' line")
        text = pattern.sub(new[key], text)
    if re.search(r"^window_years:", text, re.M):
        text = re.sub(r"^window_years:.*$", f"window_years: {window_years}", text, flags=re.M)
    else:
        text = re.sub(
            r"^(provisional:.*)$", rf"\1\nwindow_years: {window_years}", text, count=1, flags=re.M
        )
    return text
