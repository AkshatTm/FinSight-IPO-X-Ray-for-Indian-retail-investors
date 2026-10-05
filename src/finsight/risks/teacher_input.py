"""Pick the risks the teacher will label (C2.1 export, C03 §3 C2.3).

Only ``train``-slice IPOs are passed in by the caller (the script reads the split). Rules:
title + body of 40-600 words, identical titles of one company counted once, at most
``per_company_cap`` risks per company, a target of ``min(n_risks, achievable)`` and extra
sampling weight for 2024+ documents (a document dated 2024 or later is closer to what users
upload). Sampling is seeded, so the same split gives the same file.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Candidate:
    """One risk offered to the teacher."""

    risk_id: str
    ipo_id: str
    company: str
    year: int
    title: str
    body: str

    @property
    def words(self) -> int:
        """Word count of title + body."""
        return len(f"{self.title} {self.body}".split())

    def as_row(self) -> dict[str, Any]:
        """The ``risks.jsonl`` row the teacher notebook reads."""
        return {
            "risk_id": self.risk_id, "ipo_id": self.ipo_id, "company": self.company,
            "year": self.year, "title": self.title, "body": self.body,
        }  # fmt: skip


@dataclass
class Selection:
    """The chosen candidates and how the choice went (printed and written to the manifest)."""

    chosen: list[Candidate]
    achievable: int  # after word limits, de-duplication and the per-company cap
    target: int
    dropped: dict[str, int]


def select(
    candidates: Iterable[Candidate],
    *,
    n_risks: int = 12000,
    per_company_cap: int = 25,
    min_words: int = 40,
    max_words: int = 600,
    recent_from_year: int = 2024,
    recent_weight: float = 2.0,
    seed: int = 2026,
) -> Selection:
    """Apply the rules above; deterministic for a given ``seed`` and input order."""
    rng = random.Random(seed)
    dropped = {"too_short": 0, "too_long": 0, "duplicate_title": 0, "over_company_cap": 0}
    by_company: dict[str, list[Candidate]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for c in sorted(candidates, key=lambda c: (c.ipo_id, c.risk_id)):
        if c.words < min_words:
            dropped["too_short"] += 1
            continue
        if c.words > max_words:
            dropped["too_long"] += 1
            continue
        key = (c.company.lower(), " ".join(c.title.lower().split()))
        if key in seen:
            dropped["duplicate_title"] += 1
            continue
        seen.add(key)
        by_company[c.company.lower()].append(c)
    pool: list[Candidate] = []
    for _, items in sorted(by_company.items()):
        rng.shuffle(items)
        pool.extend(items[:per_company_cap])
        dropped["over_company_cap"] += max(0, len(items) - per_company_cap)
    target = min(n_risks, len(pool))
    if len(pool) <= n_risks:
        chosen = sorted(pool, key=lambda c: (c.ipo_id, c.risk_id))
    else:  # weighted sampling without replacement (Efraimidis-Spirakis keys)
        keyed = [
            (rng.random() ** (1.0 / (recent_weight if c.year >= recent_from_year else 1.0)), c)
            for c in pool
        ]
        keyed.sort(key=lambda kc: -kc[0])
        chosen = sorted((c for _, c in keyed[:n_risks]), key=lambda c: (c.ipo_id, c.risk_id))
    return Selection(chosen, achievable=len(pool), target=target, dropped=dropped)
