"""The audit sample: 50 positives, stratified by field, for Akshat to mark by hand.

Each row shows the passage around the answer with the answer between « and », and an empty
``label`` to fill with ``correct | wrong_span | wrong_value | ambiguous`` (05 section 3). The
result is weak-label precision with a 95 % Wilson interval (P2.4 / E1).
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

AUDIT_SEED = 2026
MIN_PER_FIELD = 10
WINDOW = 300  # characters of passage kept on each side of the answer
LABELS = ("correct", "wrong_span", "wrong_value", "ambiguous")


def _allocate(available: dict[str, int], n: int) -> dict[str, int]:
    """A floor of MIN_PER_FIELD each (or all there are), the rest in proportion to what's left."""
    floor = min(MIN_PER_FIELD, n // max(len(available), 1))
    take = {f: min(k, floor) for f, k in available.items()}
    left = n - sum(take.values())
    spare = {f: available[f] - take[f] for f in available}
    total_spare = sum(spare.values())
    if left <= 0 or total_spare == 0:
        return take
    shares = {f: left * s / total_spare for f, s in spare.items()}
    extra = {f: int(v) for f, v in shares.items()}
    order = sorted(shares, key=lambda f: shares[f] - extra[f], reverse=True)
    for f in order[: left - sum(extra.values())]:
        extra[f] += 1
    return {f: min(available[f], take[f] + extra[f]) for f in available}


def _highlight(row: dict[str, Any]) -> str:
    start = row["answers"]["answer_start"][0]
    text = row["answers"]["text"][0]
    end = start + len(text)
    ctx = row["context"]
    lo, hi = max(0, start - WINDOW), min(len(ctx), end + WINDOW)
    return f"{'…' if lo else ''}{ctx[lo:start]}«{text}»{ctx[end:hi]}{'…' if hi < len(ctx) else ''}"


def sample_audit(rows: list[dict[str, Any]], n: int = 50) -> list[dict[str, Any]]:
    """``n`` positive SQuAD rows, stratified by field, same result every time."""
    by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in sorted(rows, key=lambda r: r["id"]):
        if r["answers"]["text"]:
            by_field[r["field_id"]].append(r)
    counts = _allocate({f: len(v) for f, v in by_field.items()}, n)
    rng = random.Random(AUDIT_SEED)
    picked: list[dict[str, Any]] = []
    for field_id in sorted(by_field):
        picked += rng.sample(by_field[field_id], counts[field_id])
    return [
        {
            "id": r["id"],
            "ipo_id": r["ipo_id"],
            "field_id": r["field_id"],
            "question": r["question"],
            "answer": r["answers"]["text"][0],
            "answers": r["answers"],
            "passage": _highlight(r),
            "label": "",
            "notes": "",
        }
        for r in picked
    ]


def write_audit(path: Path, sample: list[dict[str, Any]], force: bool = False) -> Path:
    """Never overwrite an audit Akshat may already be filling in, unless ``force``."""
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; pass --force-audit to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in sample:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
