"""Classifier scores (B04 E16): macro-F1, per-class F1, confusion. Standard library only.

``scripts/make_classifier_notebooks.py`` pastes this file into the Kaggle notebooks, so the
epoch the notebook keeps is chosen with exactly the metric the laptop reports.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any


def scores(gold: Sequence[str], pred: Sequence[str], labels: Sequence[str]) -> dict[str, Any]:
    """Macro-F1 over ``labels`` (a class absent from gold and pred counts as F1 0 only if
    it was predicted or expected; classes with no support and no predictions are left out)."""
    if len(gold) != len(pred):
        raise ValueError("gold and pred differ in length")
    index = {lab: i for i, lab in enumerate(labels)}
    confusion = [[0] * len(labels) for _ in labels]
    for g, p in zip(gold, pred, strict=True):
        confusion[index[g]][index[p]] += 1
    per_class: dict[str, dict[str, float | int]] = {}
    for lab, i in index.items():
        tp = confusion[i][i]
        fp = sum(confusion[j][i] for j in range(len(labels))) - tp
        fn = sum(confusion[i]) - tp
        if tp + fp + fn == 0:
            continue
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[lab] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
    n = len(gold)
    return {
        "n": n,
        "accuracy": sum(confusion[i][i] for i in range(len(labels))) / n if n else 0.0,
        "macro_f1": sum(c["f1"] for c in per_class.values()) / len(per_class) if per_class else 0.0,
        "per_class": per_class,
        "labels": list(labels),
        "confusion": confusion,
    }


def company_bucket(company: str, seed: int = 2026) -> float:
    """A stable number in [0, 1) per company, so a split never puts one company on both sides."""
    digest = hashlib.sha256(f"{seed}:{company.strip().lower()}".encode()).hexdigest()
    return int(digest[:12], 16) / 16**12
