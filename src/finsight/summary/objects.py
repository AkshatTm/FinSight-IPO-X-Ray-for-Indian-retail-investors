"""Objects of the Offer (RF07) and related-party transactions (RF09).

* ``general_purposes_pct``: the "General corporate purposes" row of the objects table (Summary,
  then the Objects of the Offer chapter). An RHP prints ``[●]`` until the price is set, which
  is a ``placeholder``. When the row and the "Gross Proceeds" row (else the "Net Proceeds" /
  "Total" row) both print amounts, the share is their ratio; the evidence names the rows used.
  A printed percentage in the row is used as printed.
  A pure offer for sale (no fresh issue, "will not receive any proceeds") has no such row: it
  is a ``stated_zero``, with the sentence that says so.
* ``rpt_total``: a "Total" row of the related-party transactions table in the Summary, latest
  full fiscal year column. Many RHPs list the transactions without a total: then nothing is
  added up and the value is not found.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from finsight.core.schemas import (
    Money,
    Page,
    PageEvidence,
    ParsedDoc,
    Percent,
    Section,
    SummaryValue,
)
from finsight.normalize import parse_amount
from finsight.parse import is_pure_ofs
from finsight.summary.anchored import Cell, is_cell_value, split_line
from finsight.summary.financials import (
    _RATIO,
    RowRule,
    _pages,
    _ranked,
    _section_pages,
    _value,
    find_row,
    summary_pages,
)
from finsight.summary.layout import Line, is_placeholder, lines_of, read_tables, union_bbox, unit_of

_GCP = re.compile(r"general\s+corporate\s+purposes?", re.IGNORECASE)
# The row label, not a sentence such as "... towards general corporate purposes shall not exceed".
_GCP_ROW = re.compile(
    r"^(?:\(?[a-z0-9]{1,3}[.)]\s*)?general\s+corporate\s+purposes?\W*(?:\(\d{1,2}\)\W*)*$",
    re.IGNORECASE,
)
_NO_PROCEEDS = re.compile(
    r"[^.]{0,200}will not receive any (?:of the )?proceeds (?:from|of) the Offer[^.]{0,120}\.?",
    re.IGNORECASE,
)
_MARKS = re.compile(r"[*^#@†‡]+|\(\d{1,2}\)")
_GROSS = re.compile(r"gross\s+proceeds", re.IGNORECASE)
_NET = re.compile(r"^(?:total\s+)?net\s+proceeds|^total\b", re.IGNORECASE)
_NOTE = re.compile(r"^\(\d{1,2}\)$|^[*^#@†‡]+$")
_RPT = re.compile(r"related[\s-]+party\s+transactions?", re.IGNORECASE)
_RPT_TOTAL = RowRule(
    re.compile(r"^total(?:\s+(?:of\s+)?related[\s-]+party\s+transactions?)?\b", re.IGNORECASE),
    re.compile(_RATIO + r"|revenue|income", re.IGNORECASE),
)


def _amount_cells(line: Line) -> tuple[str, list[Cell]]:
    label, cells = split_line(line)
    keep = [c for c in cells if is_cell_value(c.text) and not _NOTE.match(c.text.strip())]
    return " ".join(w.text for w in label), keep


def _page_unit(lines: list[Line], upto: int) -> str | None:
    for j in range(upto, -1, -1):
        if found := unit_of(lines[j].text):
            return found
    return None


def _money(cell: Cell, unit: str | None) -> Money | None:
    amount = parse_amount(_MARKS.sub("", cell.text).strip(), unit)
    return amount if isinstance(amount, Money) and amount.value_inr else None


def _gcp_on_page(page: Page, doc_id: str) -> SummaryValue | None:
    lines = lines_of(page.words)
    for i, line in enumerate(lines):
        label, cells = _amount_cells(line)
        if not _GCP_ROW.match(label) or not cells:
            continue
        cell = cells[-1]
        ev = PageEvidence(
            doc_id=doc_id, page=page.number, bbox=union_bbox(list(line.words)),
            sentence=f"{label}: {cell.text}",
        )  # fmt: skip
        if is_placeholder(_MARKS.sub("", cell.text).strip()):
            return SummaryValue(
                key="general_purposes_pct_of_fresh", evidence=ev, status="placeholder"
            )
        if cell.text.strip().endswith("%"):
            try:
                pct = Decimal(re.sub(r"[^\d.]", "", cell.text))
            except InvalidOperation:
                return None
            return SummaryValue(
                key="general_purposes_pct_of_fresh", value=Percent(value=pct, raw=cell.text),
                period="final", evidence=ev, status="found",
            )  # fmt: skip
        unit = _page_unit(lines, i)
        gcp = _money(cell, unit)
        base = _base(lines, i, unit)
        if gcp is None or base is None or gcp.value_inr is None:
            return None
        name, total = base
        assert total.value_inr is not None
        pct = (gcp.value_inr / total.value_inr * 100).quantize(Decimal("0.01"))
        ev = ev.model_copy(
            update={"sentence": f"[computed: {label} {cell.text} / {name} {total.raw}] = {pct}%"}
        )
        return SummaryValue(
            key="general_purposes_pct_of_fresh", value=Percent(value=pct, raw=f"{pct}%"),
            period="final", evidence=ev, status="found",
        )  # fmt: skip
    return None


def _base(lines: list[Line], i: int, unit: str | None) -> tuple[str, Money] | None:
    """The Gross Proceeds amount near the GCP row, else the Net Proceeds / Total row below it."""
    window = range(max(0, i - 25), min(len(lines), i + 8))
    for pattern in (_GROSS, _NET):
        for j in window:
            if j == i:
                continue
            label, cells = _amount_cells(lines[j])
            if pattern is _NET and j < i:
                continue
            if pattern.search(label) and cells and (m := _money(cells[-1], unit)):
                return label, m
    return None


def general_purposes(doc: ParsedDoc, sections: list[Section], doc_id: str) -> SummaryValue | None:
    """General corporate purposes as a share of the fresh issue (%), or its placeholder."""
    pages = _pages(doc, summary_pages(sections)) + _pages(
        doc, _section_pages(sections, "objects_of_the_offer", 30)
    )
    for page in pages:
        if _GCP.search(page.text) and (found := _gcp_on_page(page, doc_id)):
            return found
    for page in pages:
        if is_pure_ofs(page.text):
            m = _NO_PROCEEDS.search(" ".join(page.text.split()))
            sentence = m.group(0) if m else "The Offer is entirely an Offer for Sale."
            return SummaryValue(
                key="general_purposes_pct_of_fresh", value=Percent(value=Decimal(0), raw="N.A."),
                period="final", status="stated_zero",
                evidence=PageEvidence(doc_id=doc_id, page=page.number, sentence=sentence[:300]),
            )  # fmt: skip
    return None


def related_party_total(
    doc: ParsedDoc, sections: list[Section], doc_id: str
) -> SummaryValue | None:
    """A printed total of related-party transactions, latest full fiscal year, from the Summary."""
    pages = _pages(doc, summary_pages(sections))
    for k, page in enumerate(pages):
        if not _RPT.search(page.text):
            continue
        for p in pages[k : k + 3]:
            if (
                p is not page
                and not _RPT.search(p.text)
                and not re.search(r"\btotal\b", p.text, re.I)
            ):
                break
            for table in read_tables(p):
                row = find_row(table, [_RPT_TOTAL])
                if row is None:
                    continue
                ranked = _ranked(table)
                col = ranked.column("latest")
                if col is None:
                    continue
                if (v := _value("rpt_total", "latest", table, row, col, doc_id)) is not None:
                    return v
        return None
    return None
