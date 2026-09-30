"""Capped views of a parsed document: how Claude Code "sees" a PDF without reading it.

Every function returns at most ``MAX_LINES`` lines, each at most ``MAX_WIDTH`` characters
(CLAUDE.md, ADR-030). ``write_samples`` saves at most ``MAX_SAMPLES`` truncated snippets
to ``data/samples/`` so they can be committed and used as test inputs.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from finsight.core.schemas import ParsedDoc

MAX_LINES = 40
MAX_WIDTH = 160
MAX_SAMPLES = 30
SAMPLE_CHARS = 300


def _cap(lines: list[str]) -> list[str]:
    clipped = [ln if len(ln) <= MAX_WIDTH else ln[: MAX_WIDTH - 1] + "…" for ln in lines]
    if len(clipped) > MAX_LINES:
        return [*clipped[: MAX_LINES - 1], f"… {len(clipped) - MAX_LINES + 1} more lines cut"]
    return clipped


def stats(doc: ParsedDoc) -> list[str]:
    chars = [len(p.text) for p in doc.pages]
    scanned = [p.number for p in doc.pages if p.is_scanned]
    printed = [p for p in doc.pages if p.printed_page]
    first_printed = printed[0] if printed else None
    return _cap(
        [
            f"{doc.ipo_id} [{doc.doc_type}] pages={doc.n_pages} sha256={doc.sha256[:12]}",
            f"chars/page median={statistics.median(chars):.0f} min={min(chars)} max={max(chars)}",
            f"scanned pages: {len(scanned)} {scanned[:15]}",
            f"pages with a printed number: {len(printed)}"
            + (
                f" (first: PDF p{first_printed.number} = printed '{first_printed.printed_page}')"
                if first_printed
                else ""
            ),
            f"empty-text pages: {sum(c == 0 for c in chars)}",
        ]
    )


def page_lines(doc: ParsedDoc, page: int, n: int = 20) -> list[str]:
    if not 1 <= page <= doc.n_pages:
        return [f"page {page} out of range 1..{doc.n_pages}"]
    p = doc.pages[page - 1]
    head = f"-- PDF p{p.number} (printed {p.printed_page!r}) scanned={p.is_scanned}"
    return _cap([head, *p.text.splitlines()[: max(0, min(n, MAX_LINES - 1))]])


def grep(doc: ParsedDoc, pattern: str, context: int = 60) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    hits: list[str] = []
    for p in doc.pages:
        flat = " ".join(p.text.split())
        for m in regex.finditer(flat):
            start, end = max(0, m.start() - context), min(len(flat), m.end() + context)
            hits.append(f"p{p.number}: …{flat[start:end]}…")
    return _cap(hits) if hits else [f"no match for {pattern!r}"]


def write_samples(doc: ParsedDoc, pattern: str, out: Path, context: int = 120) -> int:
    """Save up to ``MAX_SAMPLES`` truncated matches as JSONL; return how many were written."""
    regex = re.compile(pattern, re.IGNORECASE)
    rows = []
    for p in doc.pages:
        flat = " ".join(p.text.split())
        for m in regex.finditer(flat):
            start = max(0, m.start() - context)
            rows.append(
                {
                    "ipo_id": doc.ipo_id,
                    "doc": doc.doc_type,
                    "page": p.number,
                    "printed_page": p.printed_page,
                    "text": flat[start : start + SAMPLE_CHARS],
                }
            )
            if len(rows) >= MAX_SAMPLES:
                break
        if len(rows) >= MAX_SAMPLES:
            break
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
        newline="\n",
    )
    return len(rows)
