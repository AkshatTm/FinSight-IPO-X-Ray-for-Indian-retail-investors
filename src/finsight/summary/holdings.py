"""Promoter holdings (RF06, RF13): post-offer share, pledged share and whether a promoter exists.

* ``promoter_holding_post``: the Summary's "aggregate pre-Offer and post-Offer shareholding"
  table, rightmost post-offer % column, over the Promoter and Promoter Group rows (their
  "Total" rows when printed, else the sum of the member rows). An RHP prints ``[●]`` here until
  the price is set: the value is then a ``placeholder``, never a guess.
* ``pledged_pct``: the Capital Structure shareholding pattern (SEBI Table I), column XIII(b)
  "shares pledged or otherwise encumbered as a % of total shares held", row (A) Promoter and
  Promoter Group; a dash there is a ``stated_zero``. Without the table, a sentence such as "None
  of the Equity Shares held by our Promoters are pledged" is a ``stated_zero``.
* ``promoter_identifiable``: ``False`` only when the document says the company has no
  identifiable promoter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from finsight.compare import cell_number
from finsight.core.schemas import (
    Money,
    Page,
    PageEvidence,
    ParsedDoc,
    Percent,
    Section,
    SummaryValue,
)
from finsight.summary.anchored import (
    AnchoredRow,
    AnchoredTable,
    Cell,
    cell_box,
    read_anchored,
    read_continuation,
)
from finsight.summary.financials import _pages, _section_pages, summary_pages
from finsight.summary.layout import is_nil, is_placeholder, lines_of

_POST = re.compile(r"post-?\s?offer", re.IGNORECASE)
_PRE = r"pre-?\s?offer"
_PROMOTER = re.compile(r"promoter", re.IGNORECASE)
_OTHER = re.compile(
    r"selling|public|investor|\btop\s*\d+|\bother|additional|shareholders?\b|employee",
    re.IGNORECASE,
)
_TOTAL = re.compile(r"\btotal\b", re.IGNORECASE)
_MARKS = re.compile(r"[*^#@†‡$]+|\(\d{1,2}\)")
_NO_PROMOTER = re.compile(
    r"\b(?:our company|the company|we)\s+(?:does not have|do not have|has no|have no)\s+"
    r"(?:an?y?\s+)?identifiable\s+promoters?",
    re.IGNORECASE,
)
_NONE_PLEDGED = re.compile(
    r"none of the (?:equity )?shares held by (?:any of )?(?:our|the) promoters?[^.]{0,80}?"
    r"(?:are|is|have been)\s+(?:currently\s+)?(?:pledged|encumbered)",
    re.IGNORECASE,
)
_PLEDGE_HINT = re.compile(r"encumbered|pledged", re.IGNORECASE)
_ROW_A = re.compile(r"^\(?A\)?\s*promoter|promoter\s+(?:and|&)\s+promoter\s+group", re.IGNORECASE)
MAX_PAGES = 3


@dataclass
class Holdings:
    """The promoter inputs and the average cost of acquisition."""

    promoter_holding_post: SummaryValue | None
    pledged_pct: SummaryValue | None
    promoter_identifiable: bool
    waca: list[SummaryValue] = field(default_factory=list)


def _clean(text: str) -> str:
    return _MARKS.sub("", text).replace("%", "").strip()


def _percent(cell: Cell) -> Decimal | None:
    text = _clean(cell.text)
    if is_nil(text) or re.fullmatch(r"negligible", text, re.IGNORECASE):
        return Decimal(0)
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


def _post_tables(pages: list[Page]) -> list[AnchoredTable]:
    found: list[AnchoredTable] = []
    for page in pages:
        if found and page.number != found[-1].page + 1:
            break
        if not (_POST.search(page.text) and re.search(_PRE, page.text, re.IGNORECASE)):
            if found:
                break
            continue
        table = read_anchored(page, _POST, require=(_PRE,), min_cells=4)
        if table is None or table.column("post", r"%|percent") is None:
            if found:
                break
            continue
        found.append(table)
        if len(found) >= MAX_PAGES:
            break
    return found


def _heading(row: AnchoredRow) -> str | None:
    """A row that is really a group heading ("Promoter Group" with a stray footnote)."""
    if (
        len(row.cells) <= 1
        and re.search(r"[A-Za-z]{4}", row.label)
        and not _TOTAL.search(row.label)
    ):
        return row.label
    return None


def _promoter_rows(tables: list[AnchoredTable]) -> list[tuple[AnchoredTable, AnchoredRow, int]]:
    """(table, row, post column) for the rows under a promoter heading."""
    zone = bool(re.search(r"promoters?\W*$", tables[0].header_text, re.IGNORECASE))
    group = ""
    out: list[tuple[AnchoredTable, AnchoredRow, int]] = []
    for t in tables:
        col = t.column("post", r"%|percent", rightmost=True)
        if col is None:
            continue
        for row in t.rows:
            heading = _heading(row)
            if row.group != group or heading:
                group = row.group
                text = heading or row.group
                if _PROMOTER.search(text):
                    zone = True
                elif _OTHER.search(text):
                    zone = False
            if heading or not zone or col not in row.cells:
                continue
            out.append((t, row, col))
    return out


def promoter_post(doc: ParsedDoc, sections: list[Section], doc_id: str) -> SummaryValue | None:
    """Promoter and Promoter Group post-offer shareholding (%), from the Summary table."""
    tables = _post_tables(_pages(doc, summary_pages(sections)))
    if not tables:
        return None
    rows = _promoter_rows(tables)
    totals = [r for r in rows if _TOTAL.search(r[1].label)]
    use = totals or rows
    if not use:
        return None
    t0, r0, c0 = use[0]
    parts = [f"{r.label or 'row'}: {r.cells[c].text}" for _, r, c in use]
    head = f"[post-offer shareholding (%), {'total rows' if totals else f'sum of {len(use)} rows'}]"
    ev = PageEvidence(
        doc_id=doc_id, page=t0.page, bbox=cell_box(r0, r0.cells[c0]),
        sentence="; ".join([head, *parts])[:600],
    )  # fmt: skip
    if any(is_placeholder(_clean(r.cells[c].text)) for _, r, c in use):
        return SummaryValue(key="promoter_holding_post_pct", evidence=ev, status="placeholder")
    values = [_percent(r.cells[c]) for _, r, c in use]
    if any(v is None for v in values):
        return SummaryValue(key="promoter_holding_post_pct", status="not_found")
    total = sum((v for v in values if v is not None), Decimal(0))
    value = Percent(value=total, raw=f"{total}%")
    status = "found" if total > 0 else "stated_zero"
    return SummaryValue(
        key="promoter_holding_post_pct", value=value, period="post-offer", evidence=ev,
        status=status,
    )  # fmt: skip


def pledged(doc: ParsedDoc, sections: list[Section], doc_id: str) -> SummaryValue | None:
    """Share of promoter shares pledged or encumbered (%), from the shareholding pattern."""
    pages = _pages(doc, _section_pages(sections, "capital_structure", 300))
    for page in pages:
        if not (_PLEDGE_HINT.search(page.text) and re.search(r"\(A\)", page.text)):
            continue
        table = read_anchored(page, _PLEDGE_HINT, require=(r"shareholder",), min_cells=4)
        if table is None:
            continue
        col = table.column(r"encumbered|pledged", r"%|\(b\)")
        row = next((r for r in table.rows if _ROW_A.search(r.label)), None)
        if col is None or row is None or col not in row.cells:
            continue
        cell = row.cells[col]
        ev = PageEvidence(
            doc_id=doc_id, page=page.number, bbox=cell_box(row, cell),
            sentence=f"[shareholding pattern, XIII(b)] {row.label}: {cell.text}",
        )  # fmt: skip
        text = _clean(cell.text)
        if is_placeholder(text):
            return SummaryValue(key="pledged_promoter_pct", evidence=ev, status="placeholder")
        if is_nil(text):
            zero = Percent(value=Decimal(0), raw=cell.text)
            return SummaryValue(
                key="pledged_promoter_pct", value=zero, period="latest", evidence=ev,
                status="stated_zero",
            )  # fmt: skip
        pct = _percent(cell)
        if pct is None:
            continue
        return SummaryValue(
            key="pledged_promoter_pct", value=Percent(value=pct, raw=cell.text), period="latest",
            evidence=ev, status="found" if pct > 0 else "stated_zero",
        )  # fmt: skip
    return _none_pledged(pages + _pages(doc, summary_pages(sections)), doc_id)


def _none_pledged(pages: list[Page], doc_id: str) -> SummaryValue | None:
    for page in pages:
        text = " ".join(page.text.split())
        if m := _NONE_PLEDGED.search(text):
            ev = PageEvidence(doc_id=doc_id, page=page.number, sentence=m.group(0))
            zero = Percent(value=Decimal(0), raw=m.group(0)[-40:])
            return SummaryValue(
                key="pledged_promoter_pct", value=zero, period="latest", evidence=ev,
                status="stated_zero",
            )  # fmt: skip
    return None


def identifiable(doc: ParsedDoc) -> bool:
    """``False`` when the document states the company has no identifiable promoter."""
    return not any(_NO_PROMOTER.search(" ".join(p.text.split())) for p in doc.pages)


_ACA_HEADING = re.compile(
    r"average\s+cost\s+of\s+acquisition\s+(?:per\s+equity\s+share\s+)?(?:of\s+)?(?:equity\s+)?"
    r"shares?\s+(?:for|by|of|held)",
    re.IGNORECASE,
)
_ACA_HEADER = r"cost\s+of\s+acquisition|average\s+cost|acquisition"
_LEFT_OUT = re.compile(r"negligible|n\.?\s?a\.?|not applicable|[●•]", re.IGNORECASE)


def _aca_tables(doc: ParsedDoc, sections: list[Section]) -> list[AnchoredTable]:
    """The average-cost-of-acquisition table under its Summary heading, and its run-on page."""
    pages = _pages(doc, summary_pages(sections))
    for k, page in enumerate(pages):
        if not _ACA_HEADING.search(" ".join(page.text.split())):
            continue
        heading = next(
            (ln.top for ln in lines_of(page.words) if _ACA_HEADING.search(ln.text)), None
        )
        table = read_anchored(page, _ACA_HEADER, require=(r"number|shares",), after=heading)
        if table is None or not table.columns:
            continue
        tables = [table]
        nxt = pages[k + 1] if k + 1 < len(pages) else None
        if nxt is not None and nxt.number == page.number + 1:
            more = read_continuation(nxt, table)
            if more is not None and more.rows:
                tables.append(more)
        return tables
    return []


def waca(doc: ParsedDoc, sections: list[Section], doc_id: str) -> list[SummaryValue]:
    """Promoters' and selling shareholders' average cost of acquisition (₹ per share).

    The first value is the share-weighted average over the holders whose cost is printed ("Nil"
    counts as zero; "Negligible" and "N.A." are left out and named), then one value per holder.
    """
    tables = _aca_tables(doc, sections)
    if not tables:
        return []
    # The cost is the rightmost column; its header words may sit outside the narrow column.
    cost_col = tables[0].column(_ACA_HEADER, rightmost=True)
    if cost_col is None:
        cost_col = len(tables[0].columns) - 1
    shares_col = next(
        (k for k, c in enumerate(tables[0].columns)
         if k != cost_col and re.search(r"number|shares", c.header, re.IGNORECASE)),
        None,
    )  # fmt: skip
    if cost_col is None or shares_col is None:
        return []
    holders: list[SummaryValue] = []
    weight, total = Decimal(0), Decimal(0)
    left_out: list[str] = []
    for t in tables:
        for row in t.rows:
            cost_cell, shares_cell = row.cells.get(cost_col), row.cells.get(shares_col)
            name = _clean(row.label) or row.group
            if cost_cell is None or shares_cell is None or not re.search(r"[A-Za-z]{3}", name):
                continue
            cost_text, shares_text = _clean(cost_cell.text), _clean(shares_cell.text)
            if _LEFT_OUT.search(cost_text):
                left_out.append(f"{name}: {cost_cell.text}")
                continue
            cost = Decimal(0) if is_nil(cost_text) else cell_number(cost_text)
            shares = cell_number(shares_text)
            if cost is None or shares is None or shares <= 0:
                continue
            weight += shares
            total += shares * cost
            ev = PageEvidence(
                doc_id=doc_id, page=t.page, bbox=cell_box(row, shares_cell, cost_cell),
                sentence=f"{name}: {shares_cell.text} shares, average cost ₹{cost_cell.text}",
            )  # fmt: skip
            money = Money(value_inr=cost, currency="INR", raw=cost_cell.text, precision=2)
            holders.append(
                SummaryValue(key="waca_holder", value=money, period=name, evidence=ev,
                             status="found" if cost > 0 else "stated_zero")
            )  # fmt: skip
    if not holders or weight == 0:
        return []
    avg = (total / weight).quantize(Decimal("0.01"))
    first = holders[0].evidence
    assert first is not None
    note = f"; left out: {'; '.join(left_out)}" if left_out else ""
    ev = first.model_copy(
        update={
            "bbox": None,
            "sentence": f"[computed: share-weighted average cost of acquisition of "
            f"{len(holders)} holders, ₹ per share]{note}"[:600],
        }
    )
    money = Money(value_inr=avg, currency="INR", raw=str(avg), precision=2)
    weighted = SummaryValue(
        key="waca_selling_shareholders", value=money, period="weighted", evidence=ev,
        status="found",
    )  # fmt: skip
    return [weighted, *holders]


def extract_holdings(doc: ParsedDoc, sections: list[Section], doc_id: str) -> Holdings:
    """Post-offer promoter share, pledged share, identifiable-promoter flag and WACA."""
    return Holdings(
        promoter_holding_post=promoter_post(doc, sections, doc_id),
        pledged_pct=pledged(doc, sections, doc_id),
        promoter_identifiable=identifiable(doc),
        waca=waca(doc, sections, doc_id),
    )
