"""Indian financial periods: FY24, FY2024-25, Fiscal 2024, Q3FY25, "quarter ended ...".

The Indian fiscal year runs 1 April to 31 March and is named by the year it ends in:
FY2024-25 = FY25 = Fiscal 2025 = 1 Apr 2024 - 31 Mar 2025. Q1 ends 30 June, Q2 30 Sept,
Q3 31 Dec and Q4 31 March.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

PeriodKind = Literal["year", "quarter", "half_year", "nine_months", "as_of"]

_MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTHS |= {name.lower(): i for i, name in enumerate(calendar.month_abbr) if name}
_MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?"  # noqa: E501
_DATE = (
    rf"(?:(?P<m1>{_MONTH})\s+(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<y1>\d{{4}})"
    rf"|(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m2>{_MONTH}),?\s+(?P<y2>\d{{4}}))"
)
_YEAR = r"(?:\d{4}|\d{2})"

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("quarter_code", re.compile(rf"\bQ(?P<q>[1-4])\s*(?:of\s+)?FY\s*'?(?P<y>{_YEAR})\b", re.I)),
    (
        "ended",
        re.compile(
            r"\b(?P<what>quarter|three\s+months|six\s+months|half[\s-]year|nine\s+months"
            r"|(?:fiscal|financial)\s+year|year)\s+ended\s+(?:on\s+)?" + _DATE,
            re.I,
        ),
    ),
    ("as_of", re.compile(r"\bas\s+(?:of|at|on)\s+" + _DATE, re.I)),
    (
        "fy_span",
        re.compile(
            rf"(?:\bFY\s*'?|\b(?:fiscal|financial)\s+year\s+)(?P<a>\d{{4}})\s*[-–/]\s*(?P<b>{_YEAR})\b",
            re.I,
        ),
    ),
    ("fy", re.compile(rf"\bFY\s*'?(?P<y>{_YEAR})\b", re.I)),
    ("fiscal", re.compile(r"\b(?:fiscal|financial)(?:\s+year)?\s+(?P<y>\d{4})\b", re.I)),
]
_ENDED_KIND: dict[str, PeriodKind] = {
    "quarter": "quarter", "three months": "quarter", "six months": "half_year",
    "half year": "half_year", "half-year": "half_year", "nine months": "nine_months",
    "fiscal year": "year", "financial year": "year", "year": "year",
}  # fmt: skip


@dataclass(frozen=True)
class Period:
    """A reporting period (year, quarter, half year, nine months or a date)."""

    kind: PeriodKind
    fy: int  # the fiscal year by the calendar year it ends in (FY2024-25 -> 2025)
    quarter: int | None
    end: date
    raw: str


def _year(text: str) -> int:
    return 2000 + int(text) if len(text) == 2 else int(text)


def fiscal_year(day: date) -> int:
    """The fiscal year a date falls in, named by its end year (April to March)."""
    return day.year + 1 if day.month >= 4 else day.year


def fiscal_quarter(day: date) -> int:
    """The fiscal quarter (1-4) of a date, April-June being 1."""
    return {4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3}.get(day.month, 4)


def _quarter_end(fy: int, quarter: int) -> date:
    return {1: date(fy - 1, 6, 30), 2: date(fy - 1, 9, 30), 3: date(fy - 1, 12, 31)}.get(
        quarter, date(fy, 3, 31)
    )


def _date(m: re.Match[str]) -> date | None:
    month = m["m1"] or m["m2"]
    day, year = m["d1"] or m["d2"], m["y1"] or m["y2"]
    try:
        return date(int(year), _MONTHS[month.lower().rstrip(".")[:3]], int(day))
    except (KeyError, ValueError):
        return None


def _period(name: str, m: re.Match[str]) -> Period | None:
    raw = m.group(0)
    if name == "quarter_code":
        fy, q = _year(m["y"]), int(m["q"])
        return Period("quarter", fy, q, _quarter_end(fy, q), raw)
    if name in ("fy", "fiscal"):
        fy = _year(m["y"])
        return Period("year", fy, None, date(fy, 3, 31), raw)
    if name == "fy_span":
        first, last = int(m["a"]), _year(m["b"])
        if last != first + 1:
            return None
        return Period("year", last, None, date(last, 3, 31), raw)
    day = _date(m)
    if day is None:
        return None
    if name == "as_of":
        # a 31 March balance is the year-end one; other dates are quarter-end stubs
        quarter = fiscal_quarter(day) if day.month != 3 else None
        return Period("as_of", fiscal_year(day), quarter, day, raw)
    kind = _ENDED_KIND[" ".join(m["what"].lower().split())]
    quarter = fiscal_quarter(day) if kind == "quarter" else None
    return Period(kind, fiscal_year(day), quarter, day, raw)


@dataclass(frozen=True)
class PeriodSpan:
    """A period and where it sits in the text."""

    period: Period
    start: int
    end: int


def find_periods(text: str) -> list[PeriodSpan]:
    """Every period in ``text``, in order; earlier patterns win where two overlap."""
    spans: list[PeriodSpan] = []
    for name, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            if any(s.start < m.end() and m.start() < s.end for s in spans):
                continue
            if (period := _period(name, m)) is not None:
                spans.append(PeriodSpan(period, m.start(), m.end()))
    return sorted(spans, key=lambda s: s.start)


def parse_period(text: str) -> Period | None:
    """The period that ``text`` is (the whole string, stripped), else None."""
    text = text.strip()
    spans = find_periods(text)
    if len(spans) == 1 and (spans[0].start, spans[0].end) == (0, len(text)):
        return spans[0].period
    return None
