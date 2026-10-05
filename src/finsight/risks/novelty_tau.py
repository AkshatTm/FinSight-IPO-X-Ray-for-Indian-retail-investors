"""Choosing the novelty threshold tau from rated pairs (C2.6, E22).

A risk counts as "the same risk" as a past one when their cosine similarity is at least tau
(``finsight.risks.novelty``). The threshold was a placeholder (0.80). Here a rater judges pairs
of (new risk, nearest past risk of another company) without seeing the similarity, and tau is
the **lowest** similarity at which the pairs at or above it are judged "same" at least
``MIN_PRECISION`` of the time. The rule is fixed here, before any rating (``RULE``).

Pairs come from ``dev`` IPOs against the reference window of each one (never ``test`` or
``bench``); the caller builds them (``scripts/novelty_pairs.py``).
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from finsight.risks.bakeoff import wilson
from finsight.risks.bank import normalise

MIN_PRECISION = 0.90
MIN_PAIRS = 10  # at or above tau; fewer rated pairs than this cannot support a threshold
LOW, HIGH = 0.60, 1.0001  # pairs below LOW are never "the same risk" candidates
GRID = tuple(round(0.60 + 0.05 * i, 2) for i in range(8))  # 0.60 ... 0.95
RULE = (
    f"tau = the lowest similarity such that, among rated pairs with similarity >= tau, the share "
    f"judged 'same' is at least {MIN_PRECISION:.0%} and there are at least {MIN_PAIRS} such pairs. "
    "'unsure' ratings are left out. Fixed before rating."
)
SHEET_COLUMNS = (
    "pair_id", "a_company", "a_title", "a_text", "b_company", "b_title", "b_text", "same_risk",
)  # fmt: skip


@dataclass(frozen=True)
class Pair:
    """One new risk and its nearest past risk of another company."""

    query_id: str  # "<ipo_id>#<rid>"
    ref_ipo_id: str
    ref_title: str
    similarity: float
    a_company: str = ""
    a_title: str = ""
    a_text: str = ""
    b_company: str = ""
    b_text: str = ""

    @property
    def pair_id(self) -> str:
        """Stable short id (hash of the two ends)."""
        raw = f"{self.query_id}|{self.ref_ipo_id}|{self.ref_title}"
        return "p" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


def nearest_other(
    queries: np.ndarray, ref: np.ndarray, ref_keys: Sequence[str], query_key: str
) -> list[tuple[int, float]]:
    """For each query row the best reference row of a different company: ``(index, cosine)``.

    Args:
        queries: ``(q, d)`` vectors of the new risks (need not be unit length).
        ref: ``(r, d)`` vectors of the reference window.
        ref_keys: Company key of each reference row.
        query_key: Company key of the issuer; its own rows are never matched.
    """
    keep = np.array([k != query_key for k in ref_keys], dtype=bool)
    if not keep.any() or len(queries) == 0:
        return []
    rows = np.flatnonzero(keep)
    sims = normalise(queries) @ normalise(ref[rows]).T
    best = sims.argmax(axis=1)
    return [(int(rows[j]), float(sims[i, j])) for i, j in enumerate(best)]


def sample_pairs(
    pairs: Sequence[Pair], n: int = 100, bins: int = 8, seed: int = 2026
) -> list[Pair]:
    """About ``n`` pairs spread evenly over similarity bins from ``LOW`` to 1.0.

    Even spread (not proportional) so the high-similarity end, where tau lives, gets enough
    pairs. Deterministic for a seed; a sparse bin gives what it has.
    """
    edges = np.linspace(LOW, HIGH, bins + 1)
    rng = random.Random(seed)
    per_bin = max(1, n // bins)
    chosen: list[Pair] = []
    for lo, hi in itertools.pairwise(edges):
        pool = sorted((p for p in pairs if lo <= p.similarity < hi), key=lambda p: p.pair_id)
        rng.shuffle(pool)
        chosen += pool[:per_bin]
    rng.shuffle(chosen)
    return chosen


def write_sheet(pairs: Sequence[Pair], sheet: Path, key: Path) -> None:
    """Blind sheet (no similarity) and the secret key ``pair_id -> similarity``."""
    sheet.parent.mkdir(parents=True, exist_ok=True)
    with sheet.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(SHEET_COLUMNS)
        for p in pairs:
            w.writerow([p.pair_id, p.a_company, p.a_title, p.a_text, p.b_company, p.ref_title,
                        p.b_text, ""])  # fmt: skip
    key.write_text(
        json.dumps({p.pair_id: round(p.similarity, 4) for p in pairs}, indent=1) + "\n",
        encoding="utf-8",
    )


def read_ratings(sheet: Path, key: Path) -> list[tuple[float, str]]:
    """``(similarity, 'yes' | 'no' | 'unsure')`` for every rated row of the sheet."""
    sims = json.loads(key.read_text(encoding="utf-8"))
    out = []
    with sheet.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            label = (row.get("same_risk") or "").strip().lower()
            if label in {"yes", "no", "unsure"}:
                out.append((float(sims[row["pair_id"]]), label))
    return out


def precision_at(rated: Sequence[tuple[float, str]], tau: float) -> tuple[int, int]:
    """``(yes, judged)`` among rated pairs with similarity >= tau (unsure left out)."""
    hit = [lab for sim, lab in rated if sim >= tau and lab != "unsure"]
    return sum(1 for lab in hit if lab == "yes"), len(hit)


def choose_tau(rated: Sequence[tuple[float, str]]) -> float | None:
    """The lowest similarity meeting ``RULE`` (``None`` when no similarity does)."""
    best = None
    for tau in sorted({sim for sim, lab in rated if lab != "unsure"}, reverse=True):
        yes, n = precision_at(rated, tau)
        if n >= MIN_PAIRS and yes / n >= MIN_PRECISION:
            best = tau
    return None if best is None else round(best, 4)


def result(rated: Sequence[tuple[float, str]], placeholder: float) -> dict[str, Any]:
    """The E22 record: chosen tau, its precision with a 95 % interval, and the curve."""
    tau = choose_tau(rated)
    curve = []
    for g in GRID:
        yes, n = precision_at(rated, g)
        curve.append({"tau": g, "n": n, "same": yes, "precision": round(yes / n, 4) if n else None})
    out: dict[str, Any] = {
        "rule": RULE,
        "n_rated": len(rated),
        "n_unsure": sum(1 for _, lab in rated if lab == "unsure"),
        "placeholder_tau": placeholder,
        "tau": tau,
        "curve": curve,
        "label_source": "human:akshat (single rater, pairs shown without similarity)",
    }
    if tau is None:
        out["note"] = "no similarity met the rule; keep the placeholder and rate more pairs"
    else:
        yes, n = precision_at(rated, tau)
        out.update(precision_at_tau=round(yes / n, 4), n_at_tau=n, ci95=wilson(yes, n))
    return out
