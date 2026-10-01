"""Metrics (05 section 4): EM, token F1, NVM, list F1, and honest uncertainty.

NVM (normalized value match) is the primary extractor metric: money, counts and ranges match by
``normalize.equal`` (so ₹ 4,720 million equals ₹ 472 crore but ₹ 10 million never equals ₹ 10
crore), names match ignoring case, lists match as sets. Uncertainty is a bootstrap that resamples
whole IPOs (1,000 times), because the unit that varies is the IPO, not the field; the weak-label
audit uses a Wilson interval.
"""

from __future__ import annotations

import json
import math
import random
import re
import string
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from finsight.core.schemas import ListValue, TableValue, TextValue, Value
from finsight.normalize import equal

N_RESAMPLES = 1000
AUDIT_LABELS = ("correct", "wrong_span", "wrong_value", "ambiguous")
_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = set(string.punctuation)


# ----------------------------------------------------------------------------- text
def normalize_text(text: str) -> str:
    """SQuAD normalisation: lower case, no punctuation, no articles, single spaces."""
    lowered = "".join(ch for ch in text.lower() if ch not in _PUNCT)
    return " ".join(_ARTICLES.sub(" ", lowered).split())


def exact_match(pred: str, gold: str) -> bool:
    return normalize_text(pred) == normalize_text(gold)


def token_f1(pred: str, gold: str) -> float:
    p, g = normalize_text(pred).split(), normalize_text(gold).split()
    if not p and not g:
        return 1.0
    common = sum((Counter(p) & Counter(g)).values())
    if common == 0:
        return 0.0
    precision, recall = common / len(p), common / len(g)
    return 2 * precision * recall / (precision + recall)


# ----------------------------------------------------------------------------- values
def _key(text: str) -> str:
    return "".join(text.split()).casefold()


def list_f1(pred: Sequence[str], gold: Sequence[str]) -> float:
    """F1 between two lists of names, matched case-folded and as sets."""
    p, g = {_key(x) for x in pred}, {_key(x) for x in gold}
    if not p and not g:
        return 1.0
    hit = len(p & g)
    if hit == 0:
        return 0.0
    precision, recall = hit / len(p), hit / len(g)
    return 2 * precision * recall / (precision + recall)


def nvm(pred: Value | None, gold: Value | None) -> bool:
    """Normalized value match. ``None`` is "no answer": it matches only another ``None``."""
    if pred is None or gold is None:
        return pred is None and gold is None
    if isinstance(pred, TextValue) and isinstance(gold, TextValue):
        return _key(pred.text) == _key(gold.text)
    if isinstance(pred, ListValue) and isinstance(gold, ListValue):
        return {_key(i) for i in pred.items} == {_key(i) for i in gold.items}
    if isinstance(pred, TableValue) and isinstance(gold, TableValue):
        return {_key(r[0]) for r in pred.rows} == {_key(r[0]) for r in gold.rows}
    if isinstance(pred, TextValue | ListValue | TableValue) or isinstance(
        gold, TextValue | ListValue | TableValue
    ):
        return False
    if pred.kind == "placeholder" or gold.kind == "placeholder":
        return pred.kind == gold.kind
    if pred.kind == "range" and gold.kind == "range":
        return equal(pred.low, gold.low) and equal(pred.high, gold.high)
    return pred.kind == gold.kind and equal(pred, gold)


# ----------------------------------------------------------------------------- intervals
def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % Wilson score interval for a proportion (0, 0 when ``n`` is 0)."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _mean(per_ipo: dict[str, list[float]], ipos: Sequence[str]) -> float:
    values = [v for i in ipos for v in per_ipo[i]]
    return sum(values) / len(values) if values else 0.0


def _percentile(sorted_values: list[float], q: float) -> float:
    return sorted_values[min(len(sorted_values) - 1, max(0, int(q * len(sorted_values))))]


def bootstrap_ci(
    per_ipo: dict[str, list[float]], n_resamples: int = N_RESAMPLES, seed: int = 2026
) -> tuple[float, float, float]:
    """``(mean, low, high)``: mean score over all items, 95 % interval from resampling IPOs."""
    ipos = sorted(per_ipo)
    rng = random.Random(seed)
    means = sorted(_mean(per_ipo, [rng.choice(ipos) for _ in ipos]) for _ in range(n_resamples))
    return _mean(per_ipo, ipos), _percentile(means, 0.025), _percentile(means, 0.975)


def paired_bootstrap(
    a: dict[str, list[float]],
    b: dict[str, list[float]],
    n_resamples: int = N_RESAMPLES,
    seed: int = 2026,
) -> tuple[float, float, float]:
    """``(a - b, low, high)`` with the same resampled IPOs drawn for both rungs (paired)."""
    if set(a) != set(b):
        raise ValueError("both rungs must be scored on the same IPOs")
    ipos = sorted(a)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_resamples):
        draw = [rng.choice(ipos) for _ in ipos]
        diffs.append(_mean(a, draw) - _mean(b, draw))
    diffs.sort()
    return _mean(a, ipos) - _mean(b, ipos), _percentile(diffs, 0.025), _percentile(diffs, 0.975)


# ----------------------------------------------------------------------------- audit (E1)
def audit_precision(path: Path) -> dict[str, Any]:
    """Weak-label precision from the audit Akshat filled in; unlabelled rows are not counted."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    for r in rows:
        if r["label"] and r["label"] not in AUDIT_LABELS:
            raise ValueError(f"unknown audit label {r['label']!r}; use one of {AUDIT_LABELS}")
    done = [r for r in rows if r["label"]]
    correct = sum(r["label"] == "correct" for r in done)

    def block(items: list[dict[str, Any]]) -> dict[str, Any]:
        ok = sum(r["label"] == "correct" for r in items)
        return {"n": len(items), "correct": ok, "precision": ok / len(items) if items else 0.0,
                "wilson_95": wilson_interval(ok, len(items))}  # fmt: skip

    fields = sorted({r["field_id"] for r in done})
    return {
        "n": len(rows),
        "labelled": len(done),
        "correct": correct,
        "precision": correct / len(done) if done else 0.0,
        "wilson_95": wilson_interval(correct, len(done)),
        "by_label": dict(Counter(r["label"] for r in done)),
        "by_field": {f: block([r for r in done if r["field_id"] == f]) for f in fields},
    }
