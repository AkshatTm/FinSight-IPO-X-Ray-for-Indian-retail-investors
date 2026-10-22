"""Outstanding litigation (RF08): criminal case count and total amount from the summary table.

The Summary of the Offer Document prints one row per party and direction ("By our Company",
"Against our Directors") with a column per kind of case and an "Aggregate amount involved"
column. ``criminal_cases`` is the sum of the criminal column, ``amount_total`` the sum of the
amount column in rupees; a "Total" row is used as printed when there is one. Amounts in another
currency ("USD 2 million"), footnote marks and "Not quantifiable" are left out and named in the
evidence. All cells "Nil" or "-" make a ``stated_zero``; the table spills onto the next page.
When the summary has no such table, the Outstanding Litigation chapter's first table is read.
"""

from __future__ import annotations

import re
from decimal import Decimal

from finsight.core.schemas import Count, Money, Page, PageEvidence, ParsedDoc, Section, SummaryValue
from finsight.normalize import parse_amount
from finsight.summary.anchored import AnchoredTable, Cell, cell_box, read_anchored
from finsight.summary.financials import _pages, _section_pages, summary_pages
from finsight.summary.layout import is_nil, is_placeholder, unit_of
from finsight.summary.litigation_prose import criminal_from_sections

_HINT = re.compile(r"criminal", re.IGNORECASE)
_AMOUNT_HEADER = r"aggregate|amount"
_FOREIGN = re.compile(r"\b(?:USD|US\$|EUR|GBP|SGD|AED|JPY|CHF|AUD|CAD)\b|\$|€|£", re.IGNORECASE)
_NOTE_MARK = re.compile(r"^\(\d{1,2}\)$")
_TOTAL = re.compile(r"^\s*(?:grand\s+)?total\b", re.IGNORECASE)
_MARKS = re.compile(r"[*^#@†‡$]+")
MAX_PAGES = 3  # the summary table runs over at most this many pages


def _tables(pages: list[Page]) -> list[AnchoredTable]:
    """The first litigation table and its continuations on the following pages."""
    found: list[AnchoredTable] = []
    for page in pages:
        if not _HINT.search(page.text):
            if found:
                break
            continue
        table = read_anchored(page, _HINT, require=(_AMOUNT_HEADER,))
        if table is None or table.column("criminal") is None:
            if found:
                break
            continue
        if found and page.number != found[-1].page + 1:
            break
        found.append(table)
        if len(found) >= MAX_PAGES:
            break
    return found


def _clean(text: str) -> str:
    return _MARKS.sub("", text).strip()


def _count(cell: Cell | None) -> int | str | None:
    """A criminal-column cell: an int, 0 for Nil / N.A., "placeholder", or None if unreadable."""
    if cell is None:
        return None
    text = _clean(cell.text)
    if is_placeholder(text):
        return "placeholder"
    if is_nil(text) or re.fullmatch(r"n\.?\s?a\.?|not applicable", text, re.IGNORECASE):
        return 0
    if re.fullmatch(r"\d[\d,]*", text):
        return int(text.replace(",", ""))
    return None


def _evidence(
    doc_id: str, table: AnchoredTable, rows: list[str], cells: list[Cell]
) -> PageEvidence:
    first = table.rows[0] if table.rows else None
    box = cell_box(first, *cells[:1]) if first is not None else None
    return PageEvidence(doc_id=doc_id, page=table.page, bbox=box, sentence="; ".join(rows)[:600])


def extract_litigation(
    doc: ParsedDoc, sections: list[Section], doc_id: str
) -> dict[str, SummaryValue]:
    """``{"criminal_cases": …, "amount_total": …}``; empty when nothing was read.

    Without a litigation table, the criminal cases are counted from the chapter's sub-headings
    (``litigation_prose``, approximate and labelled so); no amount is read from prose.
    """
    tables = _tables(_pages(doc, summary_pages(sections, "litigation")))
    if not tables:
        tables = _tables(_pages(doc, _section_pages(sections, "outstanding_litigation", 15)))
    if not tables:
        counted = criminal_from_sections(doc, sections, doc_id)
        return {"criminal_cases": counted} if counted is not None else {}
    return {
        "criminal_cases": _criminal(tables, doc_id),
        "amount_total": _amount(tables, doc_id),
    }


def _rows_to_use(table: AnchoredTable) -> list[int]:
    totals = [i for i, r in enumerate(table.rows) if _TOTAL.match(r.label)]
    return totals[-1:] if totals else list(range(len(table.rows)))


def _criminal(tables: list[AnchoredTable], doc_id: str) -> SummaryValue:
    total, seen, placeholder = 0, 0, False
    parts: list[str] = []
    for t in tables:
        col = t.column("criminal")
        for i in _rows_to_use(t):
            row = t.rows[i]
            cell = row.cells.get(col) if col is not None else None
            n = _count(cell)
            if n is None or cell is None:
                continue
            if n == "placeholder":
                placeholder = True
                continue
            assert isinstance(n, int)
            total += n
            seen += 1
            parts.append(f"{row.label or row.group}: {cell.text}")
    pages = "-".join(dict.fromkeys(str(t.page) for t in tables))
    ev = _evidence(
        doc_id, tables[0], [f"[criminal proceedings, sum of {seen} rows, p{pages}]", *parts], []
    )
    if seen == 0:
        status = "placeholder" if placeholder else "not_found"
        return SummaryValue(
            key="criminal_cases", evidence=ev if placeholder else None, status=status
        )
    value = Count(value=total, raw=str(total), unit="cases")
    status = "found" if total > 0 else "stated_zero"
    return SummaryValue(
        key="criminal_cases", value=value, period="latest", evidence=ev, status=status
    )


def _amount(tables: list[AnchoredTable], doc_id: str) -> SummaryValue:
    unit = next((u for t in tables if (u := unit_of(t.header_text))), None)
    total, seen, numbers = Decimal(0), 0, 0
    parts: list[str] = []
    left_out: list[str] = []
    for t in tables:
        col = t.column(_AMOUNT_HEADER, rightmost=True)
        if col is None:
            continue
        foreign = False
        for i in _rows_to_use(t):
            row = t.rows[i]
            cell = row.cells.get(col)
            if cell is None:
                continue
            text = _clean(cell.text)
            continuation = row.label[:1].islower() or not row.label
            if _FOREIGN.search(cell.text) or (foreign and continuation):
                foreign = True
                left_out.append(f"{row.label or 'cont.'}: {cell.text}")
                continue
            foreign = False
            if _NOTE_MARK.match(text) or not text:
                continue
            if is_nil(text) or re.fullmatch(r"n\.?\s?a\.?|not applicable", text, re.IGNORECASE):
                seen += 1
                continue
            amount = parse_amount(text, unit) if unit else None
            if not isinstance(amount, Money) or amount.value_inr is None:
                left_out.append(f"{row.label}: {cell.text}")
                continue
            total += amount.value_inr
            seen += 1
            numbers += 1
            parts.append(f"{row.label or row.group}: {cell.text}")
    if seen == 0 or unit is None:
        return SummaryValue(key="amount_total", status="not_found")
    scale = unit.split(" in ")[-1] if " in " in unit else None
    divisor = _scale(scale)
    shown = (total / divisor).normalize() if divisor else total
    raw = f"{shown:,f}"
    value = Money(value_inr=total, currency="INR", raw=raw, scale_word=scale, precision=2)
    pages = "-".join(dict.fromkeys(str(t.page) for t in tables))
    head = f"[aggregate amount involved, sum of {numbers} figures, p{pages}, {unit}]"
    tail = [f"left out: {'; '.join(left_out)}"] if left_out else []
    ev = _evidence(doc_id, tables[0], [head, *parts, *tail], [])
    status = "found" if numbers else "stated_zero"
    return SummaryValue(
        key="amount_total", value=value, period="latest", evidence=ev, status=status
    )


def _scale(word: str | None) -> Decimal | None:
    if word is None:
        return None
    probe = parse_amount("1", f"₹ in {word}")
    return probe.value_inr if isinstance(probe, Money) and probe.value_inr else None
