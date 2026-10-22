"""Financials tab (CC-06): extra restated rows per period and ratios computed from them.

``extract_rows`` reads, from the same restated summary table the red-flag readers use (the
Summary of the Offer Document first, then Summary Financial Information), the rows the
Financials tab shows beside revenue, profit and net worth: equity share capital, total income,
EPS basic / diluted and net asset value per share, for the three fiscal years and the newest
stub period. Per-share rows are plain rupees: the table's scale ("₹ in million") is not applied.

``ratios`` computes, in code only, revenue growth year on year, PAT margin, debt to equity and
cash from operations. Each ratio carries its formula and the pages of its inputs; a ratio whose
inputs are missing, placeholders or a non-positive base is ``not_available`` with the reason.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field

from finsight.core.schemas import (
    DecimalStr,
    FinancialSummary,
    Money,
    ParsedDoc,
    Section,
    SummaryValue,
)
from finsight.summary.financials import (
    _RATIO,
    PRIMARY,
    SECONDARY,
    RowRule,
    _evidence,
    _Ranked,
    _rule,
    _section_pages,
    _summary_table,
    _tables,
    _value,
    find_row,
    summary_pages,
)
from finsight.summary.layout import Row, is_nil, is_placeholder
from finsight.summary.periods import PERIOD_KEYS

PERIODS = (*PERIOD_KEYS, "stub")
_EPS = r"(?=.*\b(?:earnings? per (?:equity )?share|eps)\b)"
_NOT_EPS = r"%|\bgrowth\b|\bcagr\b|\bratio\b|\breturn on\b|\bweighted\b|\bnumber of\b"
ROWS: dict[str, list[RowRule]] = {
    "equity_share_capital": [_rule(r"^equity share capital\b", _RATIO)],
    "total_income": [_rule(r"^total income\b", _RATIO)],
    # Jio p.76 prints "Earnings per equity share … Basic (in Rupees)" then a bare "Diluted" row.
    "eps_basic": [_rule(_EPS + r"(?=.*\bbasic\b)", _NOT_EPS), _rule(r"^basic\b", _NOT_EPS)],
    "eps_diluted": [_rule(_EPS + r"(?=.*\bdiluted\b)", _NOT_EPS), _rule(r"^diluted\b", _NOT_EPS)],
    "nav_per_share": [_rule(r"^net asset value per (?:equity )?share\b", _NOT_EPS)],
}
PER_SHARE = ("eps_basic", "eps_diluted", "nav_per_share")
_NUMBER = re.compile(r"^\(?-?\s?[\d,]+(?:\.\d+)?\)?$")


def _per_share(
    key: str, period: str, t: _Ranked, row: Row, col: int, doc_id: str, role: str
) -> SummaryValue | None:
    """A per-share cell in plain rupees ("6.05", "(1.23)" = -1.23), never scaled."""
    table = t.table
    cell = row.cells.get(col)
    if cell is None:
        return None
    ev = _evidence(doc_id, table.page, row, cell, table.columns[col].header, "₹", role)
    text = cell.text.strip().rstrip("*^#@†‡")
    if is_placeholder(text):
        return SummaryValue(key=key, period=period, evidence=ev, status="placeholder")
    if is_nil(text) or not _NUMBER.match(text):
        return None
    negative = text.startswith("(") or text.startswith("-")
    try:
        number = Decimal(re.sub(r"[(),\s-]", "", text))
    except InvalidOperation:
        return None
    value = Money(value_inr=-number if negative else number, currency="INR", raw=cell.text,
                  scale_word=None, precision=2)  # fmt: skip
    return SummaryValue(key=key, value=value, period=period, evidence=ev, status="found")


def extract_rows(
    doc: ParsedDoc, sections: list[Section], doc_id: str
) -> dict[str, list[SummaryValue]]:
    """``{row key: [latest, latest-1, latest-2, stub]}``; a missing period is ``not_found``.

    The stub entry's ``period`` is the printed column header when the table has one.
    """
    summary = _summary_table(_tables(doc, summary_pages(sections, "financials")))
    sfi = _tables(doc, _section_pages(sections, "summary_financial_information"))
    out: dict[str, list[SummaryValue]] = {}
    for key, rules in ROWS.items():
        got: dict[str, SummaryValue] = {}
        for t in summary + sfi:
            row = find_row(t.table, rules)
            if row is None:
                continue
            for period in PERIODS:
                col = t.column(period)
                if period in got or col is None:
                    continue
                label, role = t.period_label(period), SECONDARY if period == "stub" else PRIMARY
                if key in PER_SHARE:
                    v = _per_share(key, label, t, row, col, doc_id, role)
                else:
                    v = _value(key, label, t.table, row, col, doc_id, role)
                if v is not None:
                    got[period] = v
            if all(p in got for p in PERIOD_KEYS):
                break
        out[key] = [got.get(p) or SummaryValue(key=key, period=p) for p in PERIODS]
    return out


# ------------------------------------------------------------------------- ratios
class Ratio(BaseModel):
    """One computed figure: its value, the formula it came from and where the inputs are."""

    key: str
    period: str
    value: DecimalStr | None = None
    unit: Literal["%", "x", "₹"]
    formula: str
    inputs: list[str] = Field(default_factory=list)
    pages: list[int] = Field(default_factory=list)
    status: Literal["computed", "as_printed", "not_available"] = "not_available"
    reason: str | None = None


def _inr(v: SummaryValue | None) -> Decimal | None:
    if v is None or v.status not in ("found", "stated_zero") or not isinstance(v.value, Money):
        return None
    return v.value.value_inr


def _input(name: str, v: SummaryValue | None) -> str:
    raw = v.value.raw if v is not None and isinstance(v.value, Money) else "missing"
    page = f", p.{v.evidence.page}" if v is not None and v.evidence else ""
    return f"{name} ({v.period if v else '?'}): {raw}{page}"


def _pages_of(vs: list[SummaryValue | None]) -> list[int]:
    return sorted({v.evidence.page for v in vs if v is not None and v.evidence is not None})


RatioKey = Literal["revenue_growth_yoy", "pat_margin", "debt_to_equity", "operating_cash_flow"]
Unit = Literal["%", "x", "₹"]
Parts = list[tuple[str, SummaryValue | None]]
FORMULAS: dict[str, str] = {
    "revenue_growth_yoy": "(revenue this year − revenue last year) ÷ revenue last year × 100",
    "pat_margin": "profit after tax ÷ revenue from operations × 100",
    "debt_to_equity": "total borrowings ÷ net worth",
    "operating_cash_flow": "net cash from operating activities, as printed",
}


def _ratio(
    key: RatioKey, period: str, unit: Unit, parts: Parts, value: Decimal | None, reason: str
) -> Ratio:
    return Ratio(
        key=key,
        period=period,
        value=value.quantize(Decimal("0.01")) if value is not None else None,
        unit=unit,
        formula=FORMULAS[key],
        inputs=[_input(n, v) for n, v in parts],
        pages=_pages_of([v for _, v in parts]),
        status="computed" if value is not None else "not_available",
        reason=None if value is not None else reason,
    )


def _at(values: list[SummaryValue], i: int) -> SummaryValue | None:
    return values[i] if i < len(values) else None


def _divide(
    top: Decimal | None, base: Decimal | None, missing: tuple[str, str], not_positive: str
) -> tuple[Decimal | None, str]:
    """``top / base`` when both are known and the base is positive, else the reason why not."""
    if top is None:
        return None, missing[0]
    if base is None:
        return None, missing[1]
    if base <= 0:
        return None, not_positive
    return top / base, ""


def ratios(summary: FinancialSummary) -> list[Ratio]:
    """Revenue growth (two years), PAT margin (three years), debt / equity and cash from
    operations (latest full fiscal year), from ``summary.json`` values."""
    out: list[Ratio] = []
    rev, pat = summary.revenue, summary.profit_after_tax
    for i in (0, 1):
        now, before = _at(rev, i), _at(rev, i + 1)
        a, b = _inr(now), _inr(before)
        change = a - b if a is not None and b is not None else a
        q, why = _divide(
            change, b,
            ("this year's revenue is missing", "previous year's revenue is missing"),
            "previous year's revenue is not positive",
        )  # fmt: skip
        parts: Parts = [("revenue", now), ("revenue last year", before)]
        out.append(_ratio("revenue_growth_yoy", PERIOD_KEYS[i], "%", parts,
                          q * 100 if q is not None else None, why))  # fmt: skip
    for i in range(3):
        p, r = _at(pat, i), _at(rev, i)
        q, why = _divide(_inr(p), _inr(r), ("profit after tax is missing", "revenue is missing"),
                         "revenue is not positive")  # fmt: skip
        out.append(_ratio("pat_margin", PERIOD_KEYS[i], "%",
                          [("profit after tax", p), ("revenue", r)],
                          q * 100 if q is not None else None, why))  # fmt: skip
    debt, worth = summary.total_borrowings, summary.net_worth
    q, why = _divide(_inr(debt), _inr(worth),
                     ("total borrowings are missing", "net worth is missing"),
                     "net worth is not positive")  # fmt: skip
    out.append(_ratio("debt_to_equity", "latest", "x",
                      [("total borrowings", debt), ("net worth", worth)], q, why))  # fmt: skip
    cash = _at(summary.operating_cash_flow, 0)
    printed = _ratio("operating_cash_flow", "latest", "₹", [("cash from operations", cash)],
                     _inr(cash), "cash from operations is missing")  # fmt: skip
    if printed.status == "computed":
        printed.status = "as_printed"
    out.append(printed)
    return out
