"""Resumable teacher run (B03 §3.4): raw answers appended to a JSONL checkpoint in batches.

Standard library only: ``scripts/make_teacher_notebook.py`` copies this file into the Kaggle
notebook, so the loop tested here is the loop that runs on the GPU. A rerun skips every
``risk_id`` already in the output file (the resume flag is simply running it again).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

Generate = Callable[[list[list[dict[str, str]]]], list[str]]  # chats in, raw texts out


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Rows of a JSON Lines file (nothing if the file is missing)."""
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # a line cut short by a stopped session; that risk is redone


def done_ids(path: Path) -> set[str]:
    """Risk ids already answered, so a resumed run skips them."""
    return {str(row["risk_id"]) for row in read_jsonl(path) if "risk_id" in row}


def _append(path: Path, rows: list[dict[str, Any]]) -> None:
    cut = False
    if path.exists() and path.stat().st_size > 0:
        with path.open("rb") as f:
            f.seek(-1, os.SEEK_END)
            cut = f.read(1) != b"\n"
    with path.open("a", encoding="utf-8") as f:
        if cut:  # keep the stopped session's half line on its own, so it stays unreadable
            f.write("\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def run_teacher(
    items: Iterable[dict[str, Any]],
    generate: Generate,
    out_path: Path,
    *,
    every: int = 100,
    limit: int | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Send each item's ``messages`` to ``generate`` in batches of ``every`` and checkpoint.

    Args:
        items: dicts with ``risk_id`` and ``messages`` (chat format).
        generate: one call per batch; returns one raw text per chat, in order.
        out_path: JSONL checkpoint; rows are ``{risk_id, raw, **meta}``.
        every: batch size, and so the checkpoint interval.
        limit: stop after this many new items (pilot and smoke runs).
        meta: copied into every row (model, prompt_version).

    Returns:
        ``{"skipped": already done, "written": new rows}``.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = done_ids(out_path)
    skipped = written = 0
    batch: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal written
        if not batch:
            return
        raws = generate([it["messages"] for it in batch])
        if len(raws) != len(batch):
            raise ValueError(f"generate returned {len(raws)} answers for {len(batch)} chats")
        _append(
            out_path,
            [
                {"risk_id": it["risk_id"], "raw": r, **(meta or {})}
                for it, r in zip(batch, raws, strict=True)
            ],
        )
        written += len(batch)
        print(f"checkpoint: {written} new rows in {out_path.name}", flush=True)
        batch.clear()

    for item in items:
        rid = str(item["risk_id"])
        if rid in done:
            skipped += 1
            continue
        if limit is not None and written + len(batch) >= limit:
            break
        done.add(rid)
        batch.append(item)
        if len(batch) >= every:
            flush()
    flush()
    return {"skipped": skipped, "written": written}
