"""Bench statistics (C04 §6): IPO-cluster bootstrap intervals, paired differences, McNemar.

Items inside one document are correlated, so intervals resample whole IPOs
(``evaluate.bootstrap_ci`` / ``evaluate.paired_bootstrap``, 1,000 draws, seed 2026). McNemar's
exact test is a secondary check on paired binary outcomes.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from math import comb
from typing import Any

from finsight.evaluate import bootstrap_ci, paired_bootstrap


def per_ipo(rows: Iterable[Mapping[str, Any]], field: str) -> dict[str, list[float]]:
    """``{ipo_id: [0/1 or score, ...]}`` for rows where ``field`` is not ``None``."""
    out: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        v = r.get(field)
        if v is not None:
            out[str(r["ipo_id"])].append(float(v))
    return dict(out)


def metric(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, Any]:
    """Mean of ``field`` with its IPO-cluster 95 % interval, the item count and IPO count."""
    groups = per_ipo(rows, field)
    n = sum(len(v) for v in groups.values())
    if n == 0:
        return {"mean": None, "low": None, "high": None, "n": 0, "n_ipos": 0}
    mean, low, high = bootstrap_ci(groups)
    return {"mean": round(mean, 3), "low": round(low, 3), "high": round(high, 3), "n": n,
            "n_ipos": len(groups)}  # fmt: skip


def paired(
    a_rows: Sequence[Mapping[str, Any]],
    b_rows: Sequence[Mapping[str, Any]],
    field: str,
    key: str = "item_id",
) -> dict[str, Any] | None:
    """A minus B on the items both scored, with the IPO-cluster interval and McNemar's p."""
    a = {r[key]: r for r in a_rows if r.get(field) is not None}
    b = {r[key]: r for r in b_rows if r.get(field) is not None}
    common = sorted(set(a) & set(b))
    if not common:
        return None
    ga = per_ipo([a[k] for k in common], field)
    gb = per_ipo([b[k] for k in common], field)
    diff, low, high = paired_bootstrap(ga, gb)
    only_a = sum(bool(a[k][field]) and not bool(b[k][field]) for k in common)
    only_b = sum(bool(b[k][field]) and not bool(a[k][field]) for k in common)
    verdict = "better" if low > 0 else "worse" if high < 0 else "on par"
    return {"diff": round(diff, 3), "low": round(low, 3), "high": round(high, 3),
            "n": len(common), "only_a": only_a, "only_b": only_b,
            "mcnemar_p": round(mcnemar_exact(only_a, only_b), 4), "verdict": verdict}  # fmt: skip


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts ``b`` and ``c``."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2**n
    return float(min(1.0, 2 * tail))
