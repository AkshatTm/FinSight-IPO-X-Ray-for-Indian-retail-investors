"""Revenue, profit after tax, net worth, total borrowings and operating cash flow (B02 §6a).

Where each value is read, in order:

- Revenue, profit, net worth, borrowings: the restated financial summary table that SEBI ICDR
  requires in the **Summary of the Offer Document** (the table with the most of these rows wins),
  then the Summary Financial Information statements for anything still missing.
- Operating cash flow: the restated cash-flow summary in Summary Financial Information, then the
  restated cash-flow statement pages (``find_subsection_pages(...)["cash_flows"]``).

Yearly values are the last three full fiscal years, latest first. Balance-sheet values (net worth,
borrowings) are primary at the latest full fiscal year end (``latest``); when the same table also
prints a newer part-year column, that value is kept as a secondary ``*_stub`` value whose
``period`` is the printed date. Every value is ``found`` (with its page, box and row),
``stated_zero``, ``placeholder`` (``[●]``) or ``not_found``. A dash or "Nil" is ``stated_zero``
only when its row or column otherwise prints figures. Without a unit line no amount is read.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from finsight.core.schemas import Money, Page, PageEvidence, ParsedDoc, Section, SummaryValue, Word
from finsight.normalize import parse_amount
from finsight.summary.layout import (
    GridTable,
    Row,
    is_nil,
    is_placeholder,
    read_tables,
    union_bbox,
    unit_of,
)
from finsight.summary.periods import PERIOD_KEYS, parse_period, rank_years

YEARLY = ("revenue", "profit_after_tax", "operating_cash_flow")
POINT = ("total_borrowings", "net_worth")

_ENUM = re.compile(r"^(?:[ivxlc]+\.?\)?|\(?[a-z]\)|[a-z]\.|\d{1,2}[.)]|[-–•])\s+", re.IGNORECASE)
_NOTE = re.compile(r"\s*\((?:\d{1,2}|[a-z]|[ivx]+)\)|[*^#@†‡]+")


def clean_label(text: str) -> str:
    """Lower-case label without enumerators ("IX", "(a)", "1.") or note marks ("(3)", "*")."""
    t = " ".join(text.split()).lower()
    for _ in range(2):
        t = _ENUM.sub("", t)
    return " ".join(_NOTE.sub(" ", t).split())


@dataclass(frozen=True)
class RowRule:
    """A row label pattern; ``reject`` drops look-alike rows (growth %, per-share, before tax)."""

    pattern: re.Pattern[str]
    reject: re.Pattern[str] | None = None

    def match(self, label: str) -> bool:
        return bool(self.pattern.search(label)) and not (self.reject and self.reject.search(label))


def _rule(pattern: str, reject: str | None = None) -> RowRule:
    return RowRule(re.compile(pattern), re.compile(reject) if reject else None)


_RATIO = r"%|\bgrowth\b|\bmargin\b|\bcagr\b|\bratio\b|\bper (equity )?share\b|\breturn on\b"
RULES: dict[str, list[RowRule]] = {
    "revenue": [_rule(r"^(total )?revenue from operations?\b", _RATIO)],
    "profit_after_tax": [
        _rule(
            r"^(restated )?(consolidated )?(net )?(profit|loss|\(loss\)|\(profit\))\b",
            _RATIO + r"|\bbefore\b|attributable|\bearning|comprehensive|exceptional|operating"
            r"|\bgross\b|ebitda|discontinued|continuing|from operations|\b(profit|loss|gain) on\b"
            r"|\bshare of\b",
        ),
        _rule(r"^(restated )?(net )?profit after tax\b|^pat\b", _RATIO + r"|continuing"),
    ],
    "net_worth": [
        _rule(r"^(total )?net ?worth\b", _RATIO + r"|adjusted|tangible"),
        # Some summaries print Ind AS "Total equity" in place of "Net worth" (dev: Bluestone).
        _rule(r"^total equity\b", _RATIO + r"|liabilities|non[\s-]*controlling"),
    ],
    "total_borrowings": [_rule(r"^total borrowings?\b", _RATIO + r"|net debt|/")],
    "operating_cash_flow": [
        _rule(r"^net cash(?:\s*flows?)?\b.*\boperating activit", r"\bbefore\b"),
        _rule(r"^cash (flows? )?(generated|used|from).*operating activit", r"\bbefore\b"),
    ],
}
# Used only inside the chosen summary table: a single "Borrowings" row, or current + non-current.
_BORROWINGS = _rule(r"^borrowings?\b", _RATIO)
_CURRENT = _rule(r"^current borrowings?\b", _RATIO)
_NON_CURRENT = _rule(r"^non[\s-]*current borrowings?\b", _RATIO)


def find_row(table: GridTable, rules: list[RowRule]) -> Row | None:
    """The first row whose label (own, own + continuation, or above + own) matches."""
    for rule in rules:
        for row in table.rows:
            if any(rule.match(clean_label(lab)) for lab in row.labels()):
                return row
    return None


# ------------------------------------------------------------------------- values
def row_unit(row: Row, table_unit: str | None) -> str | None:
    """A unit printed in the row label ("Revenue from Operations (₹ in million)") wins over the
    table's when it has a scale or the table's has none."""
    own = unit_of(" ".join(p for p in (row.label, row.label_below) if p))
    if own and (" in " in own or table_unit is None or " in " not in table_unit):
        return own
    return table_unit


def _money(word: Word, unit: str) -> Money | None:
    raw = word.text.strip().rstrip("*^#@†‡")
    if is_nil(raw):
        scale = unit.split(" in ")[-1] if " in " in unit else None
        return Money(value_inr=Decimal(0), currency="INR", raw=raw, scale_word=scale, precision=0)
    amount = parse_amount(raw, unit)
    return amount if isinstance(amount, Money) else None


PRIMARY = "primary: latest full fiscal year"
SECONDARY = "secondary: stub period"


def _evidence(
    doc_id: str, page: int, row: Row, cell: Word, header: str, unit: str, role: str = ""
) -> PageEvidence:
    label = " ".join(p for p in (row.label, row.label_below) if p) or row.label_above
    sentence = f"{label} — {header}: {cell.text} ({unit})" if header else f"{label}: {cell.text}"
    if role:
        sentence = f"[{role}] {sentence}"
    return PageEvidence(
        doc_id=doc_id, page=page, bbox=union_bbox([*row.label_words, cell]), sentence=sentence
    )


def _is_number(word: Word | None) -> bool:
    return word is not None and not is_nil(word.text) and not is_placeholder(word.text)


def otherwise_numeric(table: GridTable, row: Row, col: int) -> bool:
    """Another cell of the row, or of the column, prints a real figure: a dash there is a zero
    the document states, not an empty cell."""
    if any(_is_number(w) for k, w in row.cells.items() if k != col):
        return True
    return any(_is_number(r.cells.get(col)) for r in table.rows if r is not row)


def _value(
    key: str, period: str, table: GridTable, row: Row, col: int, doc_id: str, role: str = ""
) -> SummaryValue | None:
    cell = row.cells.get(col)
    unit = row_unit(row, table.unit)
    if cell is None or unit is None:
        return None
    header = table.columns[col].header
    ev = _evidence(doc_id, table.page, row, cell, header, unit, role)
    if is_placeholder(cell.text):
        return SummaryValue(key=key, period=period, evidence=ev, status="placeholder")
    if is_nil(cell.text) and not otherwise_numeric(table, row, col):
        return None
    money = _money(cell, unit)
    if money is None:
        return None
    status = "stated_zero" if is_nil(cell.text) else "found"
    return SummaryValue(key=key, value=money, period=period, evidence=ev, status=status)


def _missing(key: str, period: str | None) -> SummaryValue:
    return SummaryValue(key=key, period=period, status="not_found")


@dataclass
class _Ranked:
    table: GridTable
    years: dict[str, int]  # "latest" -> column index
    continues: _Ranked | None = None  # the same table on the previous page
    stub: int | None = None  # the newest part-year column, when the years were ranked

    def column(self, period: str) -> int | None:
        return self.stub if period == "stub" else self.years.get(period)

    def period_label(self, period: str) -> str:
        """``period`` for a value: the key, or the printed header for the stub column."""
        if period == "stub" and self.stub is not None:
            return self.table.columns[self.stub].header or "stub"
        return period


def _ranked(table: GridTable) -> _Ranked:
    periods = [parse_period(c.header) for c in table.columns]
    ranks = rank_years(periods)
    years = {period: col for col, period in ranks.items()}
    stub = None
    if "latest" in years:
        latest = periods[years["latest"]].year or 0
        stubs = [
            (p.year, -i) for i, p in enumerate(periods)
            if p.kind == "stub" and p.year is not None and p.year >= latest
        ]  # fmt: skip
        stub = -max(stubs)[1] if stubs else None
    return _Ranked(table, years, stub=stub)


def _role(period: str) -> str:
    return SECONDARY if period == "stub" else PRIMARY


def _sum_borrowings(t: _Ranked, doc_id: str, period: str = "latest") -> SummaryValue | None:
    """Total borrowings from one "Borrowings" row, or current + non-current rows of one table."""
    col = t.column(period)
    if col is None:
        return None
    label, role = t.period_label(period), _role(period)
    single = find_row(t.table, [_BORROWINGS])
    if single is not None:
        return _value("total_borrowings", label, t.table, single, col, doc_id, role)
    cur, non = find_row(t.table, [_CURRENT]), find_row(t.table, [_NON_CURRENT])
    if cur is None or non is None:
        return None
    a = _value("total_borrowings", label, t.table, cur, col, doc_id, role)
    b = _value("total_borrowings", label, t.table, non, col, doc_id, role)
    if a is None or b is None or a.evidence is None or b.evidence is None:
        return None
    ma, mb = a.value, b.value
    if not (isinstance(ma, Money) and isinstance(mb, Money)):
        return None  # a placeholder in either row
    if ma.value_inr is None or mb.value_inr is None:
        return None
    total = Money(
        value_inr=ma.value_inr + mb.value_inr, currency="INR", raw=f"{ma.raw} + {mb.raw}",
        scale_word=ma.scale_word, precision=max(ma.precision, mb.precision),
    )  # fmt: skip
    ev = a.evidence.model_copy(
        update={"sentence": f"{a.evidence.sentence}; {b.evidence.sentence}", "bbox": None}
    )
    return SummaryValue(
        key="total_borrowings", value=total, period=label, evidence=ev, status="found"
    )


# ------------------------------------------------------------------------- pages
def _pages(doc: ParsedDoc, numbers: Iterable[int]) -> list[Page]:
    by_number = {p.number: p for p in doc.pages}
    return [by_number[n] for n in numbers if n in by_number]


def _section_pages(sections: list[Section], section_id: str, limit: int = 40) -> list[int]:
    for s in sections:
        if s.id == section_id:
            return list(range(s.start_page, min(s.end_page, s.start_page + limit - 1) + 1))
    return []


SUMMARY_WINDOW = 40  # pages scanned before Risk Factors when no Summary section was detected


def summary_pages(sections: list[Section]) -> list[int]:
    """Pages of the Summary of the Offer Document.

    When the section was not detected, the pages just before Risk Factors (where ICDR puts the
    summary) are scanned instead; the best-scoring table there must still show two of the
    summary rows to be used.
    """
    if pages := _section_pages(sections, "summary"):
        return pages
    rf = next((s.start_page for s in sections if s.id == "risk_factors"), None)
    if rf is None:
        return list(range(1, SUMMARY_WINDOW + 1))
    return list(range(max(1, rf - SUMMARY_WINDOW), rf))


def _same_columns(a: GridTable, b: GridTable) -> bool:
    return len(a.columns) == len(b.columns) and all(
        abs(x.right - y.right) <= 6 for x, y in zip(a.columns, b.columns, strict=True)
    )


def _tables(doc: ParsedDoc, numbers: Iterable[int]) -> list[_Ranked]:
    """Tables with a unit. A table that continues the previous one (same columns, on the next
    page or further down the same page) takes its unit when it states none, and its headers
    when it repeats none."""
    out: list[_Ranked] = []
    previous: _Ranked | None = None
    for page in _pages(doc, numbers):
        for table in read_tables(page):
            continues = None
            same = previous is not None and _same_columns(previous.table, table)
            headless = not any(c.header for c in table.columns)
            if previous is not None and same and (table.unit is None or headless):
                continues = previous
                table.unit = table.unit or previous.table.unit
                if headless:
                    for c, p in zip(table.columns, previous.table.columns, strict=True):
                        c.header = p.header
            if table.unit:
                ranked = _ranked(table)
                ranked.continues = continues
                out.append(ranked)
                previous = ranked
    return out


def _with_continuations(best: _Ranked, tables: list[_Ranked]) -> list[_Ranked]:
    """``best`` and the pages it runs on to."""
    chain = [best]
    for t in tables:
        if t.continues is chain[-1]:
            chain.append(t)
    return chain


def _score(chain: list[_Ranked]) -> int:
    """How many of the four summary rows a table (with its continuation pages) shows."""
    keys = ("revenue", "profit_after_tax", "net_worth", "total_borrowings")
    return sum(
        any(t.years and find_row(t.table, RULES[k]) is not None for t in chain) for k in keys
    )


def _summary_table(tables: list[_Ranked]) -> list[_Ranked]:
    """The restated financial summary: the table showing the most summary rows (at least 2),
    with the pages it continues on; the earliest wins a tie."""
    chains = [_with_continuations(t, tables) for t in tables if t.continues is None]
    best = max(chains, key=_score, default=[])
    return best if best and _score(best) >= 2 else []


@dataclass
class FinancialValues:
    """What C3.1a reads: yearly lists (latest first, always 3 entries) and two point values."""

    currency_unit: str
    revenue: list[SummaryValue]
    profit_after_tax: list[SummaryValue]
    operating_cash_flow: list[SummaryValue]
    total_borrowings: SummaryValue
    net_worth: SummaryValue
    total_borrowings_stub: SummaryValue | None = None
    net_worth_stub: SummaryValue | None = None


def _fill(
    key: str,
    tables: list[_Ranked],
    doc_id: str,
    out: dict[str, SummaryValue],
    rules: list[RowRule] | None = None,
) -> None:
    """Fill the still-missing periods of ``key`` from the first table that has its row.

    Balance-sheet values (``POINT``) take ``latest`` as the primary value and, from the same
    table only, the newest stub column as ``out["stub"]`` (secondary).
    """
    point = key in POINT
    periods = ("latest",) if point else PERIOD_KEYS
    for t in tables:
        row = find_row(t.table, rules or RULES[key])
        if row is None:
            continue
        for period in periods:
            if period in out or period not in t.years:
                continue
            role = PRIMARY if point else ""
            col = t.years[period]
            if (v := _value(key, period, t.table, row, col, doc_id, role)) is not None:
                out[period] = v
                if point and t.stub is not None:
                    label = t.period_label("stub")
                    stub = _value(key, label, t.table, row, t.stub, doc_id, SECONDARY)
                    if stub is not None:
                        out["stub"] = stub
        if all(p in out for p in periods):
            return


def extract_financials(
    doc: ParsedDoc,
    sections: list[Section],
    doc_id: str,
    cash_flow_pages: list[int] | None = None,
) -> FinancialValues:
    """Read the C3.1a values from a parsed document (full or fixture pages)."""
    summary = _summary_table(_tables(doc, summary_pages(sections)))
    sfi = _tables(doc, _section_pages(sections, "summary_financial_information"))
    cash = _tables(doc, cash_flow_pages or [])
    found: dict[str, dict[str, SummaryValue]] = {k: {} for k in (*YEARLY, *POINT)}
    for key in ("revenue", "profit_after_tax", "net_worth", "total_borrowings"):
        _fill(key, summary + sfi, doc_id, found[key])
    borrowings = found["total_borrowings"]
    for t in summary:
        if "latest" not in borrowings and (v := _sum_borrowings(t, doc_id)):
            borrowings["latest"] = v
            if s := _sum_borrowings(t, doc_id, "stub"):
                borrowings["stub"] = s
    _fill("operating_cash_flow", summary + sfi + cash, doc_id, found["operating_cash_flow"])
    unit = summary[0].table.unit if summary else next((t.table.unit for t in sfi), None)

    def yearly(key: str) -> list[SummaryValue]:
        return [found[key].get(p) or _missing(key, p) for p in PERIOD_KEYS]

    def point(key: str) -> SummaryValue:
        return found[key].get("latest") or _missing(key, "latest")

    return FinancialValues(
        currency_unit=unit or "",
        revenue=yearly("revenue"),
        profit_after_tax=yearly("profit_after_tax"),
        operating_cash_flow=yearly("operating_cash_flow"),
        total_borrowings=point("total_borrowings"),
        net_worth=point("net_worth"),
        total_borrowings_stub=found["total_borrowings"].get("stub"),
        net_worth_stub=found["net_worth"].get("stub"),
    )


def values_by_source(
    doc: ParsedDoc,
    sections: list[Section],
    doc_id: str,
    cash_flow_pages: list[int] | None = None,
) -> dict[str, dict[str, Decimal]]:
    """Each field read from each source on its own ("summary", "sfi", "cash"), in rupees.

    For the coverage script's cross-check: two sources that both print a value should agree;
    a disagreement points at a wrong row or column. Net worth is compared only where a row says
    "Net worth" (Ind AS "Total equity" legitimately differs from it).
    """
    sources = {
        "summary": _summary_table(_tables(doc, summary_pages(sections))),
        "sfi": _tables(doc, _section_pages(sections, "summary_financial_information")),
        "cash": _tables(doc, cash_flow_pages or []),
    }
    out: dict[str, dict[str, Decimal]] = {}
    for name, tables in sources.items():
        for key in ("operating_cash_flow",) if name == "cash" else (*YEARLY, *POINT):
            found: dict[str, SummaryValue] = {}
            rules = RULES[key][:1] if key == "net_worth" else RULES[key]
            _fill(key, tables, doc_id, found, rules)
            for period, v in found.items():
                if isinstance(v.value, Money) and v.value.value_inr is not None:
                    field = key if key in POINT else f"{key}:{period}"
                    out.setdefault(field, {})[name] = v.value.value_inr
    return out
