"""BIO version of the weak labels for the BiLSTM-CRF rung (P5.3, E11).

    uv run python -m finsight.weaklabel.bio     # adds bio_*.jsonl to the Kaggle dataset folder

The SQuAD rows (one question, one answer span per row) become tagged token sequences: every
distinct context is one sequence, each field's answer span is tagged ``B-<field>`` then
``I-<field>``, everything else ``O``. Unanswerable rows add nothing but an all-``O`` stretch.
Two fields that tag the same tokens (fresh issue and total issue size on a pure fresh issue)
cannot share one tag per token, so the later one gets its own copy of the sequence.

Train gets tokens and tags. Dev keeps the SQuAD rows (the BiLSTM-CRF is scored with the same
EM, F1 and NVM code as the QA rungs): each dev sequence lists the rows it answers.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.weaklabel.package import DATASET_NAME, SLICE_SEED, SLICE_SIZE

# A number with its commas and decimals stays one token ("19,000.00"); words; single symbols.
TOKEN = re.compile(r"\d+(?:,\d+)*(?:\.\d+)?|\w+|[^\w\s]")


def tokenize(text: str) -> list[tuple[str, int, int]]:
    """``(token, start, end)`` with character offsets into ``text``."""
    return [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(text)]


def tag_span(
    tokens: list[tuple[str, int, int]], tags: list[str], field: str, start: int, end: int
) -> bool:
    """Tag the tokens inside [start, end) in place; False if a token is already tagged."""
    inside = [i for i, (_, s, e) in enumerate(tokens) if s >= start and e <= end]
    if not inside or any(tags[i] != "O" for i in inside):
        return False
    for n, i in enumerate(inside):
        tags[i] = ("B-" if n == 0 else "I-") + field
    return True


def to_bio(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Train sequences: ``{id, ipo_id, tokens, offsets, tags}``; same context, same sequence."""
    by_context: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_context[(row["ipo_id"], row["context"])].append(row)
    out: list[dict[str, Any]] = []
    for (ipo_id, context), group in by_context.items():
        tokens = tokenize(context)
        copies: list[list[str]] = [["O"] * len(tokens)]
        for row in group:
            if not row["answers"]["text"]:
                continue
            start = row["answers"]["answer_start"][0]
            end = start + len(row["answers"]["text"][0])
            if not any(tag_span(tokens, tags, row["field_id"], start, end) for tags in copies):
                copies.append(["O"] * len(tokens))
                tag_span(tokens, copies[-1], row["field_id"], start, end)
        for n, tags in enumerate(copies):
            out.append(
                {
                    "id": f"{group[0]['id']}#{n}",
                    "ipo_id": ipo_id,
                    "tokens": [t for t, _, _ in tokens],
                    "offsets": [[s, e] for _, s, e in tokens],
                    "tags": tags,
                }
            )
    return out


def to_dev(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dev sequences: one per context, with the SQuAD rows it has to answer."""
    by_context: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_context[(row["ipo_id"], row["context"])].append(row)
    out = []
    for (ipo_id, context), group in by_context.items():
        tokens = tokenize(context)
        out.append(
            {
                "id": group[0]["id"],
                "ipo_id": ipo_id,
                "context": context,
                "tokens": [t for t, _, _ in tokens],
                "offsets": [[s, e] for _, s, e in tokens],
                "rows": [
                    {"id": r["id"], "field_id": r["field_id"], "answers": r["answers"]}
                    for r in group
                ],
            }
        )
    return out


def _slice(seqs: list[dict[str, Any]], n: int, positive) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    import random

    if len(seqs) <= n:
        return seqs
    rng = random.Random(SLICE_SEED)
    pos = [i for i, s in enumerate(seqs) if positive(s)]
    neg = [i for i, s in enumerate(seqs) if not positive(s)]
    n_pos = round(n * len(pos) / len(seqs))
    picked = rng.sample(pos, min(n_pos, len(pos))) + rng.sample(neg, min(n - n_pos, len(neg)))
    return [seqs[i] for i in sorted(picked)]


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_files(source: Path, out: Path) -> dict[str, int]:
    def read(name: str) -> list[dict[str, Any]]:
        lines = (source / name).read_text(encoding="utf-8").splitlines()
        return [json.loads(x) for x in lines if x]

    train_rows, dev_rows = read("train.jsonl"), read("dev.jsonl")
    train, dev = to_bio(train_rows), to_dev(dev_rows)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "bio_train.jsonl", train)
    _write(out / "bio_dev.jsonl", dev)
    train_has = lambda s: any(t != "O" for t in s["tags"])  # noqa: E731
    dev_has = lambda s: any(r["answers"]["text"] for r in s["rows"])  # noqa: E731
    _write(out / f"bio_train_{SLICE_SIZE}.jsonl", _slice(train, SLICE_SIZE, train_has))
    _write(out / f"bio_dev_{SLICE_SIZE}.jsonl", _slice(dev, SLICE_SIZE // 4, dev_has))
    return {"train_sequences": len(train), "dev_sequences": len(dev)}


def main() -> int:
    paths = get_settings().paths
    counts = build_files(
        paths.processed_dir / "weaklabel", paths.processed_dir / "kaggle" / DATASET_NAME
    )
    print(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
