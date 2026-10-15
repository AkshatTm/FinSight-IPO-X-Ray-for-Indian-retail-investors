"""Customer concentration (RF10): the top customer's and top 10 customers' share of revenue.

RHPs print these in Risk Factors or Our Business as a small table: a row "Top 10 customers" with
a percentage per period. The period headers are read as for the financial tables (``layout``'s
header band, ``periods.rank_years``) and the latest full fiscal year column is used; a stub
period is never taken for a year. Only printed percentages count; the share is not computed.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from finsight.core.schemas import PageEvidence, ParsedDoc, Percent, Section, SummaryValue, Word
from finsight.summary.anchored import Cell
from finsight.summary.financials import _pages, _ranked, _section_pages
from finsight.summary.layout import Column, GridTable, Line, _header_band, lines_of, union_bbox

TOP10 = re.compile(r"\btop\s*(?:10|ten)\s+(?:customers?|clients?)\b", re.IGNORECASE)
TOP1 = re.compile(
    r"\b(?:top\s*(?:1|one)|largest|single largest|biggest)\s+(?:customer|client)\b", re.IGNORECASE
)
_PCT = re.compile(r"^\(?\d{1,3}(?:\.\d+)?\s*%\)?[*^#@†‡]*$")
SECTIONS = ("risk_factors", "our_business", "management_s_discussion_and_analysis", "summary")


def _pct_cells(cells: list[Cell]) -> list[Cell]:
    return [c for c in cells if _PCT.match(c.text.replace(" ", ""))]


def _split(line: Line) -> tuple[list[Word], list[Cell]]:
    """(label, percentage cells): the label runs up to the first percentage ("Top 10 customers")."""
    for i, w in enumerate(line.words):
        if _PCT.match(w.text):
            return line.words[:i], _pct_cells([Cell([x]) for x in line.words[i:]])
    return line.words, []


def _value(text: str) -> Decimal | None:
    try:
        return Decimal(re.sub(r"[^\d.]", "", text))
    except InvalidOperation:
        return None


def _first_row(lines: list[Line], i: int) -> int:
    """The first line of the block of percentage rows that line ``i`` belongs to."""
    first = i
    while first > 0 and lines[first].top - lines[first - 1].top <= 14:
        _, cells = _split(lines[first - 1])
        if len(cells) < 2:
            break
        first -= 1
    return first


def _latest(lines: list[Line], i: int, cells: list[Cell], margin: float) -> int | None:
    """Index into ``cells`` of the latest full fiscal year column, or ``None``."""
    if len(cells) == 1:
        return None  # one figure with no column to date it
    columns = [Column(right=c.x1) for c in cells]
    for k, col in enumerate(columns):
        col.left = columns[k - 1].right if k else col.right - (cells[0].x1 - cells[0].x0) - 20
    table = GridTable(page=0, columns=columns, rows=[], unit=None)
    _header_band(lines, _first_row(lines, i), columns, margin)
    return _ranked(table).column("latest")


def _share(
    doc: ParsedDoc, sections: list[Section], doc_id: str, pattern: re.Pattern[str], key: str
) -> SummaryValue | None:
    pages = []
    for sid in SECTIONS:
        pages.extend(_pages(doc, _section_pages(sections, sid, 120)))
    for page in pages:
        if not pattern.search(" ".join(page.text.split())):
            continue
        lines = lines_of(page.words)
        for i, line in enumerate(lines):
            label, pcts = _split(line)
            label_text = " ".join(w.text for w in label)
            if not pattern.search(label_text) or not pcts:
                continue
            margin = label[0].bbox[0] if label else line.words[0].bbox[0]
            k = _latest(lines, i, pcts, margin)
            if k is None:
                continue
            cell = pcts[k]
            value = _value(cell.text)
            if value is None:
                continue
            ev = PageEvidence(
                doc_id=doc_id, page=page.number, bbox=union_bbox([*label, *cell.words]),
                sentence=f"[latest full fiscal year column] {label_text}: {cell.text}",
            )  # fmt: skip
            return SummaryValue(
                key=key, value=Percent(value=value, raw=cell.text), period="latest",
                evidence=ev, status="found",
            )  # fmt: skip
    return None


def extract_customers(
    doc: ParsedDoc, sections: list[Section], doc_id: str
) -> tuple[SummaryValue | None, SummaryValue | None]:
    """(top customer share, top 10 customers share) of revenue, latest full fiscal year."""
    return (
        _share(doc, sections, doc_id, TOP1, "customer_top1_pct"),
        _share(doc, sections, doc_id, TOP10, "customer_top10_pct"),
    )
