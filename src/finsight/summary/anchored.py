"""Header-anchored tables: the litigation summary, peer table and shareholding patterns (C3.1b).

These tables print "Nil", "N.A." and ``[●]`` as often as figures, and their cells hold text
such as "USD 2 million" or "9^^", so the right-edge clustering of ``layout`` does not fit them.
Here a table starts at a header line the caller names; each data line splits at its first value
cell into a label and cells (words closer than ``CELL_GAP`` form one cell); columns are the
x-ranges where cells of different lines overlap; a column's header is the header-band text over
it. The table ends at running text or a large gap. Nothing is inferred: a cell is kept as printed.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

from finsight.core.schemas import Page, Word
from finsight.summary.layout import Line, lines_of, union_bbox

CELL_GAP = 6.0  # words closer than this form one cell ("USD 2 million", "[ ● ] #")
HEADER_GAP = 14.0  # header lines are at most this far apart
HEADER_LINES = 18  # the header band is at most this many lines
DATA_GAP = 50.0  # data lines further apart than this end the table (a page number below)
LABEL_GAP = 13.0  # a label-only line this close below a data line continues its label

_MARKS = r"[*^#@†‡$]*"
_VALUE = re.compile(
    r"^[(\[]?\s*(?:[-–—]|nil|n\.?\s?a\.?|not applicable|negligible|[●•]|"
    r"\(?-?\d[\d,]*(?:\.\d+)?\)?\s*%?)\s*[)\]]?\s*"
    + _MARKS
    + r"\s*(?:\(\d{1,2}\))?\s*"
    + _MARKS
    + "$",
    re.IGNORECASE,
)
_ENUM = re.compile(r"^(?:\(?[A-Za-z]\d?\)|\(?[ivxIVX]{1,4}\)|\d{1,2}[.)]|[A-Za-z][.)])$")
_DANGLING = re.compile(r"\b(?:our|the|of|and|&|by|against|in|for|to|with)$|[,(/-]$", re.IGNORECASE)
_MONEY_WORDS = re.compile(r"\d.*\b(?:million|billion|crore|lakh|thousand|mn|bn)\b", re.IGNORECASE)


def is_cell_value(text: str) -> bool:
    """A printed value: a figure, a percentage, a dash, Nil, N.A., ``[●]`` or "USD 2 million"."""
    t = " ".join(text.split())
    return bool(_VALUE.match(t) or (_MONEY_WORDS.search(t) and len(t.split()) <= 10))


@dataclass
class Cell:
    """Neighbouring words of one data line, read as one value."""

    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def x0(self) -> float:
        return self.words[0].bbox[0]

    @property
    def x1(self) -> float:
        return self.words[-1].bbox[2]


@dataclass
class AnchoredColumn:
    """An x-range where cells of several lines overlap, and the header text over it."""

    x0: float
    x1: float
    header: str = ""


@dataclass
class AnchoredRow:
    """One data line: its label (with a continuation below) and its cells by column."""

    top: float
    label: str
    label_words: list[Word]
    cells: dict[int, Cell] = field(default_factory=dict)
    group: str = ""  # the last label-only heading above the row ("Promoters", "Directors")


@dataclass
class AnchoredTable:
    """A header-anchored table on one page."""

    page: int
    header_text: str
    columns: list[AnchoredColumn]
    rows: list[AnchoredRow]

    def column(self, *patterns: str, rightmost: bool = False) -> int | None:
        """The first (or last) column whose header matches every pattern."""
        regs = [re.compile(p, re.IGNORECASE) for p in patterns]
        hits = [k for k, c in enumerate(self.columns) if all(r.search(c.header) for r in regs)]
        if not hits:
            return None
        return hits[-1] if rightmost else hits[0]


_TRAILER = re.compile(
    r"^(?:[*^#@†‡$]+|\(\d{1,2}\)|%|\]|\)|million|billion|crores?|lakhs?|thousand)$", re.IGNORECASE
)


def _cells(words: list[Word]) -> list[Cell]:
    """Group words into cells: a close word joins the cell before it unless that cell is already
    a whole value and the word starts a new one ("N.A." then "USD 2 million")."""
    cells: list[Cell] = []
    for w in words:
        if (
            cells
            and w.bbox[0] - cells[-1].x1 < CELL_GAP
            and (not is_cell_value(cells[-1].text) or _TRAILER.match(w.text))
        ):
            cells[-1].words.append(w)
        else:
            cells.append(Cell([w]))
    return cells


def split_line(line: Line) -> tuple[list[Word], list[Cell]]:
    """(label words, value cells): the line splits at its first value word after the label.

    A leading enumerator ("1.", "(A)", "(C1)") is part of the label.
    """
    words = line.words
    for i, w in enumerate(words):
        if i == 0 and _ENUM.match(w.text):
            continue
        if is_cell_value(w.text):
            return words[:i], _cells(words[i:])
    return words, []


def _value_cells(cells: list[Cell]) -> int:
    return sum(is_cell_value(c.text) for c in cells)


def _running_text(line: Line, page_width: float) -> bool:
    """A line of prose: long, with no wide gaps between words."""
    ws = line.words
    if len(ws) < 8:
        return False
    gaps = [b.bbox[0] - a.bbox[2] for a, b in itertools.pairwise(ws)]
    wide = sum(g >= 12 for g in gaps)
    return wide <= 1 and ws[-1].bbox[2] - ws[0].bbox[0] > page_width * 0.45


def _columns(rows: list[tuple[Line, list[Word], list[Cell]]]) -> list[AnchoredColumn]:
    spans = sorted((c.x0, c.x1) for _, _, cells in rows for c in cells if is_cell_value(c.text))
    merged: list[list[float]] = []
    for x0, x1 in spans:
        if merged and x0 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    return [AnchoredColumn(x0=a, x1=b) for a, b in merged]


def _column_of(cell: Cell, columns: list[AnchoredColumn]) -> int | None:
    best, best_overlap = None, 0.0
    for k, col in enumerate(columns):
        overlap = min(cell.x1, col.x1) - max(cell.x0, col.x0)
        if overlap > best_overlap or (overlap == best_overlap and best is None and overlap >= 0):
            best, best_overlap = k, overlap
    return best


def read_anchored(
    page: Page,
    start: str | re.Pattern[str],
    require: tuple[str, ...] = (),
    min_cells: int = 2,
) -> AnchoredTable | None:
    """The table whose header band contains ``start`` (and every ``require`` pattern).

    Args:
        page: The page to read.
        start: A pattern one header word or phrase matches ("criminal", "P/E").
        require: Patterns the header band text must also match.
        min_cells: Value cells a line needs to start the data rows.
    """
    pat = re.compile(start, re.IGNORECASE) if isinstance(start, str) else start
    needs = [re.compile(r, re.IGNORECASE) for r in require]
    lines = lines_of(page.words)
    for i, line in enumerate(lines):
        if not pat.search(line.text):
            continue
        table = _read_from(page, lines, i, needs, min_cells)
        if table is not None:
            return table
    return None


def _read_from(
    page: Page, lines: list[Line], hit: int, needs: list[re.Pattern[str]], min_cells: int
) -> AnchoredTable | None:
    # Header band: up to 3 lines above the hit that sit close and are not prose, then down to
    # the first line with enough value cells.
    first = hit
    while (
        first > 0
        and hit - first < 3
        and lines[first].top - lines[first - 1].top <= HEADER_GAP
        and not _running_text(lines[first - 1], page.width)
    ):
        first -= 1
    data_start = None
    for j in range(hit + 1, min(len(lines), hit + HEADER_LINES)):
        _, cells = split_line(lines[j])
        if _value_cells(cells) >= min_cells:
            data_start = j
            break
    if data_start is None:
        return None
    band = lines[first:data_start]
    band_text = " ".join(ln.text for ln in band)
    if not all(r.search(band_text) for r in needs):
        return None
    parsed: list[tuple[Line, list[Word], list[Cell]]] = []
    last_top = lines[data_start].top
    for line in lines[data_start:]:
        if line.top - last_top > DATA_GAP or _running_text(line, page.width):
            break
        label, cells = split_line(line)
        if any(len(c.words) >= 6 and not is_cell_value(c.text) for c in cells):
            break  # prose in the value columns: the notes under the table
        parsed.append((line, label, cells))
        if cells:
            last_top = line.top
    data = [p for p in parsed if p[2]]
    columns = _columns(data)
    for col in columns:
        col.header = " ".join(
            w.text
            for ln in band
            for w in ln.words
            if min(w.bbox[2], col.x1) - max(w.bbox[0], col.x0) > 0
        )
    rows: list[AnchoredRow] = []
    group, prev_top = "", -1e9
    for line, label, cells in parsed:
        if not cells:
            text = " ".join(w.text for w in label)
            dangling = bool(rows) and bool(_DANGLING.search(rows[-1].label))
            if rows and line.top - prev_top <= LABEL_GAP and (text[:1].islower() or dangling):
                rows[-1].label = f"{rows[-1].label} {text}".strip()
                rows[-1].label_words.extend(label)
                prev_top = line.top
            elif re.search(r"[A-Za-z]{3}", text):
                group = text
            continue
        prev_top = line.top
        row = AnchoredRow(
            top=line.top, label=" ".join(w.text for w in label), label_words=list(label),
            group=group,
        )  # fmt: skip
        for cell in cells:
            k = _column_of(cell, columns)
            if k is not None and k not in row.cells:
                row.cells[k] = cell
        rows.append(row)
    return AnchoredTable(page=page.number, header_text=band_text, columns=columns, rows=rows)


def cell_box(row: AnchoredRow, *cells: Cell | None) -> tuple[float, float, float, float] | None:
    """The box around a row's label and some of its cells (evidence)."""
    words = [*row.label_words, *(w for c in cells if c is not None for w in c.words)]
    return union_bbox(words)
