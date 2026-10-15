"""Financial tables rebuilt from a page's word boxes (rows, right-aligned columns, header band).

RHP summary tables are usually unruled, and their page text comes out column by column, so the
table is rebuilt from geometry: words on the same baseline form a line; the right edges of the
numbers in those lines cluster into columns (figures are right-aligned); a line with numbers in
two or more columns is a data row whose words left of the columns are its label; the lines just
above the first data row (up to the unit line, e.g. "(₹ in million)") are the column headers.
A header phrase belongs to every column it overlaps, so merged headers ("As at and for the
Financial Year" over three columns) reach each of them.
"""

from __future__ import annotations

import itertools
import re
import statistics
from dataclasses import dataclass, field

from finsight.core.schemas import BBox, Page, Word
from finsight.parse import detect_header_scale

LINE_TOL = 3.0  # words whose tops differ by at most this share a line (values sit 1 pt off)
CLUSTER_GAP = 6.0  # right edges closer than this belong to one column
CELL_TOL = 9.0  # a number belongs to a column if its right edge is this close
DASH_TOL = 14.0  # dashes are centred, not right-aligned: allow more slack to the left
MIN_COLUMN_ROWS = 3  # a column needs numbers in this many lines
BLOCK_GAP = 60.0  # data lines further apart than this start a new table
HEADER_SPAN = 110.0  # column headers sit at most this far above the first data row
CONT_GAP = 14.0  # a label continues on the next line when it is this close
PHRASE_GAP = 6.0  # header words closer than this form one phrase

_NUMBER = re.compile(r"^\(?[-–—]?\d(?:[\d,]*\d)?(?:\.\d+)?\)?[*^#@†‡]*$")
_DASH = re.compile(r"^(?:[-–—]|nil|NIL|Nil)[*^#@†‡]*$")
_PLACEHOLDER = re.compile(r"^\[?[●•]\]?[*^#@†‡]*$")
_YEAR_CELL = re.compile(r"^(?:19|20)\d\d[*^#@†‡]*$")
_DAY_CELL = re.compile(r"^\d{1,2},?$")
_MONTH = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\b", re.IGNORECASE
)
_HEADER_LABELS = re.compile(r"^(particulars|s\.?|no\.?|sr\.?|sl\.?)$", re.IGNORECASE)


def is_value_token(text: str) -> bool:
    """A figure, a nil dash or a ``[●]`` placeholder as printed in a table cell."""
    t = text.strip()
    return bool(_NUMBER.match(t) or _DASH.match(t) or _PLACEHOLDER.match(t))


def is_placeholder(text: str) -> bool:
    """``[●]``: a blank the final Prospectus fills in."""
    return bool(_PLACEHOLDER.match(text.strip()))


def is_nil(text: str) -> bool:
    """A dash or "Nil": the document states zero."""
    return bool(_DASH.match(text.strip()))


@dataclass
class Line:
    """Words sharing a baseline, left to right."""

    top: float
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class Column:
    """A right-aligned figure column and the header text printed over it."""

    right: float
    left: float = 0.0
    header: str = ""


@dataclass
class Row:
    """One data row: its label (own line, continuation below, lines above) and its cells."""

    top: float
    label: str
    label_below: str
    label_above: str
    label_words: list[Word]
    cells: dict[int, Word] = field(default_factory=dict)

    def labels(self) -> list[str]:
        """Candidate labels to match, most specific first."""
        own = self.label
        out = [" ".join(p for p in (own, self.label_below) if p)]
        if self.label_above:
            out.append(" ".join(p for p in (self.label_above, own) if p))
        out.append(own)
        return [s for s in dict.fromkeys(out) if s]


@dataclass
class GridTable:
    """A table rebuilt from one page."""

    page: int
    columns: list[Column]
    rows: list[Row]
    unit: str | None


def lines_of(words: list[Word]) -> list[Line]:
    """Group words into lines by their top edge, top to bottom."""
    lines: list[Line] = []
    for w in sorted(words, key=lambda w: (w.bbox[1], w.bbox[0])):
        if lines and w.bbox[1] - lines[-1].top <= LINE_TOL:
            lines[-1].words.append(w)
        else:
            lines.append(Line(top=w.bbox[1], words=[w]))
    for line in lines:
        line.words.sort(key=lambda w: w.bbox[0])
    return lines


def _figures(line: Line, min_x: float) -> list[Word]:
    return [w for w in line.words if w.bbox[0] >= min_x and is_value_token(w.text)]


def _cluster(edges: list[float]) -> list[tuple[float, int]]:
    """(median right edge, count) per cluster of close right edges."""
    out: list[list[float]] = []
    for x in sorted(edges):
        if out and x - out[-1][-1] <= CLUSTER_GAP:
            out[-1].append(x)
        else:
            out.append([x])
    return [(statistics.median(c), len(c)) for c in out]


def _column_of(word: Word, columns: list[Column]) -> int | None:
    x1 = word.bbox[2]
    dash = is_nil(word.text) or is_placeholder(word.text)
    best, best_d = None, 1e9
    for i, col in enumerate(columns):
        d = col.right - x1
        ok = -CELL_TOL <= d <= DASH_TOL if dash else abs(d) <= CELL_TOL
        if ok and abs(d) < best_d:
            best, best_d = i, abs(d)
    return best


def _is_header_line(line: Line, cells: dict[int, Word]) -> bool:
    """A row of years ("2025*", "2024") or dates ("31 December 2024") over the columns."""
    texts = [w.text.strip() for w in cells.values()]
    if all(_YEAR_CELL.match(t) for t in texts):
        return True
    dated = _MONTH.search(line.text) is not None
    return dated and all(_YEAR_CELL.match(t) or _DAY_CELL.match(t) for t in texts)


def _phrases(words: list[Word]) -> list[tuple[float, float, str]]:
    out: list[list[Word]] = []
    for w in words:
        if out and w.bbox[0] - out[-1][-1].bbox[2] <= PHRASE_GAP:
            out[-1].append(w)
        else:
            out.append([w])
    return [(p[0].bbox[0], p[-1].bbox[2], " ".join(w.text for w in p)) for p in out]


def _blocks(lines: list[Line], min_x: float) -> list[list[int]]:
    """Indices of lines with 2+ figures, split where they are far apart."""
    blocks: list[list[int]] = []
    last_top = -1e9
    for i, line in enumerate(lines):
        if len(_figures(line, min_x)) < 2:
            continue
        if not blocks or line.top - last_top > BLOCK_GAP:
            blocks.append([])
        blocks[-1].append(i)
        last_top = line.top
    return blocks


def read_tables(page: Page) -> list[GridTable]:
    """Every figure table on ``page`` (usually one), rebuilt from its words."""
    lines = lines_of(page.words)
    min_x = page.width * 0.25
    tables: list[GridTable] = []
    for block in _blocks(lines, min_x):
        table = _read_block(page, lines, block, min_x)
        if table is not None:
            tables.append(table)
    return tables


def _read_block(page: Page, lines: list[Line], block: list[int], min_x: float) -> GridTable | None:
    edges = [
        w.bbox[2]
        for i in block
        for w in _figures(lines[i], min_x)
        if not (is_nil(w.text) or is_placeholder(w.text))
    ]
    columns = [Column(right=x) for x, n in _cluster(edges) if n >= MIN_COLUMN_ROWS]
    if len(columns) < 2:
        return None
    span = range(max(0, block[0] - 4), min(len(lines), block[-1] + 5))
    all_cells: dict[int, dict[int, Word]] = {}
    for i in span:
        cells: dict[int, Word] = {}
        for w in _figures(lines[i], min_x):
            k = _column_of(w, columns)
            if k is not None and k not in cells:
                cells[k] = w
        all_cells[i] = cells
    # Footnote marks such as "(1)" next to a label are figures too, but in no column.
    first_left = min(
        (w.bbox[0] for i in block for w in all_cells[i].values()), default=columns[0].right
    )
    # Data rows and their label words (left of the first column).
    parsed: dict[int, tuple[dict[int, Word], list[Word]]] = {}
    pure_label: set[int] = set()
    for i in span:
        label_words = [w for w in lines[i].words if w.bbox[2] < first_left - 1]
        parsed[i] = (all_cells[i], label_words)
        if label_words and len(label_words) == len(lines[i].words):
            pure_label.add(i)
    data = [i for i in range(block[0], block[-1] + 1) if len(parsed[i][0]) >= 2]
    header_lines = [i for i in data if _is_header_line(lines[i], parsed[i][0])]
    data = [i for i in data if i not in header_lines]
    if not data:
        return None
    label_right = max((w.bbox[2] for i in data for w in parsed[i][1]), default=first_left - 1)
    spacing = statistics.median([b.right - a.right for a, b in itertools.pairwise(columns)])
    for k, col in enumerate(columns):
        col.left = max(label_right, col.right - spacing) if k == 0 else columns[k - 1].right
    unit = _header_band(lines, data[0], columns, label_right)
    if unit is None:
        unit = _page_unit(lines, data[0])
    rows = _rows(lines, parsed, data, pure_label)
    return GridTable(page=page.number, columns=columns, rows=rows, unit=unit)


def _header_band(
    lines: list[Line], first: int, columns: list[Column], label_right: float
) -> str | None:
    """Fill each column's header from the lines above the first data row; return the unit."""
    top = lines[first].top
    parts: dict[int, list[str]] = {k: [] for k in range(len(columns))}
    unit = None
    for i in range(first - 1, -1, -1):
        line = lines[i]
        if top - line.top > HEADER_SPAN:
            break
        if found := detect_header_scale(line.text):
            unit = found
            break
        label_area = [
            w
            for w in line.words
            if w.bbox[2] <= label_right + 1 and not _HEADER_LABELS.match(w.text)
        ]
        words = [w for w in line.words if w.bbox[2] > label_right + 1]
        if len(label_area) >= 3 and words:
            break  # running text above the table
        if label_area:
            continue  # a sub-heading in the label column ("A. Cash flows from operating ...")
        for x0, x1, text in _phrases(words):
            for k, col in enumerate(columns):
                if min(x1, col.right + 2) - max(x0, col.left + 2) > 3:
                    parts[k].insert(0, text)
    for k, col in enumerate(columns):
        col.header = " ".join(parts[k])
    return unit


def _page_unit(lines: list[Line], first: int) -> str | None:
    """The nearest unit line above the table on the same page."""
    for i in range(first - 1, -1, -1):
        if found := detect_header_scale(lines[i].text):
            return found
    return None


def _rows(
    lines: list[Line],
    parsed: dict[int, tuple[dict[int, Word], list[Word]]],
    data: list[int],
    pure_label: set[int],
) -> list[Row]:
    def label_only(i: int) -> bool:
        return i in pure_label

    def continues(i: int) -> bool:
        """A wrapped label goes on in lower case ("Revenue from" / "operations")."""
        first = lines[i].words[0].text
        return label_only(i) and (first[:1].islower() or first[:1] in "(&/")

    def text(words: list[Word]) -> str:
        return " ".join(w.text for w in words)

    rows: list[Row] = []
    for i in data:
        cells, label_words = parsed[i]
        below: list[str] = []
        j, prev = i + 1, lines[i].top
        while j < len(lines) and continues(j) and lines[j].top - prev <= CONT_GAP:
            below.append(text(parsed[j][1]))
            prev = lines[j].top
            j += 1
        above: list[str] = []
        j, prev = i - 1, lines[i].top
        while j >= 0 and label_only(j) and prev - lines[j].top <= CONT_GAP:
            above.insert(0, text(parsed[j][1]))
            prev = lines[j].top
            j -= 1
        rows.append(
            Row(top=lines[i].top, label=text(label_words), label_below=" ".join(below),
                label_above=" ".join(above), label_words=label_words, cells=cells)
        )  # fmt: skip
    return rows


def union_bbox(words: list[Word]) -> BBox | None:
    """The box around ``words``."""
    if not words:
        return None
    return (
        min(w.bbox[0] for w in words),
        min(w.bbox[1] for w in words),
        max(w.bbox[2] for w in words),
        max(w.bbox[3] for w in words),
    )
