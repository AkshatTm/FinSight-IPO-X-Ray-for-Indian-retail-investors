"""Amounts in a table passage, read with the table's unit header (ADR-044).

``retrieve.chunk.table_text`` writes a table as one passage: a first line ``[Table, ₹ in
million]`` (the ``header_scale`` that ``parse.tables`` stored in tables.json), then one row
per line with the cells joined by `` | ``. The numbers in such a table are bare ("9,272"), so
``parse_amounts`` skips them like any bare number in prose. Here each cell is read on its own:

- A bare number becomes money in the header unit, but only when the header states a scale
  word (million, crore, lakh ...). Under a plain ``₹`` header the columns mix rupees and
  share counts (capital structure), so bare cells stay unread there.
- The number must follow a label cell in its row: serial numbers ("1.") are not amounts.
- A bare year ("2025") is a column heading, and a row that states its own unit ("per share",
  "%", "(in ₹)", "number of") is not in the header unit: both are skipped.
- The metric of a cell comes from its own row label, never from the row above.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsight.core.schemas import Money
from finsight.normalize import AmountSpan, parse_amount, parse_amounts
from finsight.verify.metrics import find_metrics

SEPARATOR = " | "
_HEADER = re.compile(r"\[Table, ([^\]\n]+)\]\n")
_LABEL = re.compile(r"[^\W\d_]{2,}")  # two letters in a row, in any script
_YEAR = re.compile(r"(?:19|20)\d\d")
_OWN_UNIT = re.compile(
    r"₹|%|\bper\s+(?:equity\s+)?share\b|\bper\s+cent\b|\bpercent|\bratio\b|\bnumber\s+of\b|"
    r"\bnos?\b\.?|\btimes\b|\bdays\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TableAmount:
    span: AmountSpan
    metrics: tuple[str, ...]
    unit: str | None  # the header unit, when the cell itself printed none


def table_scale(text: str) -> str | None:
    """The unit header of a table passage ("₹ in million"), or None for any other passage."""
    m = _HEADER.match(text)
    return m.group(1).strip() if m else None


def _scales_bare_numbers(header_scale: str) -> bool:
    probe = parse_amount("1", header_scale=header_scale)
    return isinstance(probe, Money) and probe.scale_word is not None


def _cells(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """(start, end) of each cell of the row ``text[start:end]``, without the padding."""
    out, at = [], start
    for part in text[start:end].split(SEPARATOR):
        lead = len(part) - len(part.lstrip())
        out.append((at + lead, at + lead + len(part.strip())))
        at += len(part) + len(SEPARATOR)
    return out


def table_amounts(text: str) -> list[TableAmount] | None:
    """Every amount of a table passage with the metrics its row label names; None if no table."""
    scale = table_scale(text)
    if scale is None:
        return None
    explicit = parse_amounts(text)
    read_bare = _scales_bare_numbers(scale)
    out: list[TableAmount] = []
    row_start = text.index("\n") + 1
    for line in text[row_start:].split("\n"):
        row_end = row_start + len(line)
        label = ""
        for start, end in _cells(text, row_start, row_end):
            cell = text[start:end]
            metrics = tuple(dict.fromkeys(h.metric for h in find_metrics(label)))
            inside = [s for s in explicit if start <= s.start < end]
            for s in inside:
                out.append(TableAmount(s, metrics, None))
            if inside:
                continue
            if read_bare and label and not _YEAR.fullmatch(cell) and not _OWN_UNIT.search(label):
                amount = parse_amount(cell, header_scale=scale)
                if isinstance(amount, Money):
                    out.append(TableAmount(AmountSpan(amount, start, end), metrics, scale))
                    continue
            if _LABEL.search(cell):
                label = f"{label} {cell}".strip()
        row_start = row_end + 1
    return sorted(out, key=lambda t: t.span.start)
