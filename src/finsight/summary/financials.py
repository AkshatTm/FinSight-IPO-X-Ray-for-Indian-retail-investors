"""Revenue, profit after tax, net worth, total borrowings and operating cash flow (B02 §6a).

Where each value is read, in order:

- Revenue, profit, net worth, borrowings: the restated financial summary table that SEBI ICDR
  requires in the **Summary of the Offer Document** (the table with the most of these rows wins),
  then the Summary Financial Information statements for anything still missing.
- Operating cash flow: the restated cash-flow summary in Summary Financial Information, then the
  restated cash-flow statement pages (``find_subsection_pages(...)["cash_flows"]``).

Yearly values are the last three full fiscal years, latest first; balance-sheet values (net worth,
borrowings) are taken at the latest full fiscal year end, matching ``latest``. Every value is
``found`` (with its page, box and row), ``placeholder`` (``[●]``) or ``not_found``. A printed
dash or "Nil" is a stated zero. Without a unit line ("₹ in million") no amount is read.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from finsight.core.schemas import Money, Page, PageEvidence, ParsedDoc, Section, SummaryValue, Word
from finsight.normalize import parse_amount
from finsight.summary.layout import GridTable, Row, is_nil, is_placeholder, read_tables, union_bbox
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
            r"|\bgross\b|ebitda|discontinued|from operations|\bon (sale|disposal)\b|\bshare of\b",
        ),
        _rule(r"^(restated )?(net )?profit after tax\b|^pat\b", _RATIO),
    ],
    "net_worth": [_rule(r"^(total )?net ?worth\b", _RATIO + r"|adjusted|tangible")],
    "total_borrowings": [_rule(r"^total borrowings?\b", _RATIO + r"|net debt|/")],
    "operating_cash_flow": [
        _rule(r"^net cash\b.*\boperating activit", r"\bbefore\b"),
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
def _money(word: Word, unit: str) -> Money | None:
    raw = word.text.strip().rstrip("*^#@†‡")
    if is_nil(raw):
        scale = unit.split(" in ")[-1] if " in " in unit else None
        return Money(value_inr=Decimal(0), currency="INR", raw=raw, scale_word=scale, precision=0)
    amount = parse_amount(raw, unit)
    return amount if isinstance(amount, Money) else None


def _evidence(doc_id: str, page: int, row: Row, cell: Word, header: str, unit: str) -> PageEvidence:
    label = " ".join(p for p in (row.label, row.label_below) if p) or row.label_above
    sentence = f"{label} — {header}: {cell.text} ({unit})" if header else f"{label}: {cell.text}"
    return PageEvidence(
        doc_id=doc_id, page=page, bbox=union_bbox([*row.label_words, cell]), sentence=sentence
    )


def _value(
    key: str, period: str, table: GridTable, row: Row, col: int, doc_id: str
) -> SummaryValue | None:
    cell = row.cells.get(col)
    if cell is None or table.unit is None:
        return None
    header = table.columns[col].header
    ev = _evidence(doc_id, table.page, row, cell, header, table.unit)
    if is_placeholder(cell.text):
        return SummaryValue(key=key, period=period, evidence=ev, status="placeholder")
    money = _money(cell, table.unit)
    if money is None:
        return None
    return SummaryValue(key=key, value=money, period=period, evidence=ev, status="found")


def _missing(key: str, period: str | None) -> SummaryValue:
    return SummaryValue(key=key, period=period, status="not_found")


@dataclass
class _Ranked:
    table: GridTable
    years: dict[str, int]  # "latest" -> column index


def _ranked(table: GridTable) -> _Ranked:
    ranks = rank_years([parse_period(c.header) for c in table.columns])
    return _Ranked(table, {period: col for col, period in ranks.items()})


def _sum_borrowings(t: _Ranked, doc_id: str) -> SummaryValue | None:
    """Total borrowings from one "Borrowings" row, or current + non-current rows of one table."""
    col = t.years.get("latest")
    if col is None:
        return None
    single = find_row(t.table, [_BORROWINGS])
    if single is not None:
        return _value("total_borrowings", "latest", t.table, single, col, doc_id)
    cur, non = find_row(t.table, [_CURRENT]), find_row(t.table, [_NON_CURRENT])
    if cur is None or non is None:
        return None
    a = _value("total_borrowings", "latest", t.table, cur, col, doc_id)
    b = _value("total_borrowings", "latest", t.table, non, col, doc_id)
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
        key="total_borrowings", value=total, period="latest", evidence=ev, status="found"
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


def _tables(doc: ParsedDoc, numbers: Iterable[int]) -> list[_Ranked]:
    return [_ranked(t) for page in _pages(doc, numbers) for t in read_tables(page) if t.unit]


def _score(t: _Ranked) -> int:
    keys = ("revenue", "profit_after_tax", "net_worth", "total_borrowings")
    return sum(find_row(t.table, RULES[k]) is not None for k in keys) if t.years else 0


@dataclass
class FinancialValues:
    """What C3.1a reads: yearly lists (latest first, always 3 entries) and two point values."""

    currency_unit: str
    revenue: list[SummaryValue]
    profit_after_tax: list[SummaryValue]
    operating_cash_flow: list[SummaryValue]
    total_borrowings: SummaryValue
    net_worth: SummaryValue


def _fill(key: str, tables: list[_Ranked], doc_id: str, out: dict[str, SummaryValue]) -> None:
    """Fill the still-missing periods of ``key`` from the first table that has its row."""
    periods = PERIOD_KEYS if key in YEARLY else ("latest",)
    for t in tables:
        row = find_row(t.table, RULES[key])
        if row is None:
            continue
        for period in periods:
            if period in out or period not in t.years:
                continue
            if (v := _value(key, period, t.table, row, t.years[period], doc_id)) is not None:
                out[period] = v
        if all(p in out for p in periods):
            return


def extract_financials(
    doc: ParsedDoc,
    sections: list[Section],
    doc_id: str,
    cash_flow_pages: list[int] | None = None,
) -> FinancialValues:
    """Read the C3.1a values from a parsed document (full or fixture pages)."""
    summary = sorted(_tables(doc, _section_pages(sections, "summary")), key=_score, reverse=True)
    summary = [t for t in summary if _score(t) >= 2][:1]
    sfi = _tables(doc, _section_pages(sections, "summary_financial_information"))
    cash = _tables(doc, cash_flow_pages or [])
    found: dict[str, dict[str, SummaryValue]] = {k: {} for k in (*YEARLY, *POINT)}
    for key in ("revenue", "profit_after_tax", "net_worth", "total_borrowings"):
        _fill(key, summary + sfi, doc_id, found[key])
    borrowings = found["total_borrowings"]
    if "latest" not in borrowings and summary and (v := _sum_borrowings(summary[0], doc_id)):
        borrowings["latest"] = v
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
    )
