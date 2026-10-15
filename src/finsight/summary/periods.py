"""Column headers → reporting periods: a full fiscal year or a stub (part-year) period.

Red-flag inputs use the last three **full** fiscal years, latest first (gold v3 ``latest``,
``latest-1``, ``latest-2``). Stub periods ("nine months ended December 31, 2024") are read but
never ranked, so a nine-month loss is not compared with a full year. A column whose year cannot
be read is never ranked either (nothing is guessed from column order).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

PERIOD_KEYS = ("latest", "latest-1", "latest-2")

_STUB = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|[1-9]|1[01])[\s-]*months?\b"
    r"|\bperiod ended\b|\bquarter\b|\bhalf[\s-]*year\b|\bq[1-4]\b|\bh1\b",
    re.IGNORECASE,
)
_FULL = re.compile(
    r"\byears?\b|\bfiscal\b|\bfy\s*['’]?\s*(?:\d{2}|\d{4})?\b|\bfinancial year\b|\btwelve months\b"
    r"|\b12 months\b",
    re.IGNORECASE,
)
_MONTH = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?![a-z])", re.IGNORECASE
)
_YEAR = re.compile(r"\b((?:19|20)\d\d)\b")
_FY_SHORT = re.compile(
    r"\b(?:fy|fiscal|financial year)\s*['’]?\s*(\d{2})\b(?![\d,])", re.IGNORECASE
)
_FY_SPAN = re.compile(r"\b((?:19|20)\d\d)\s*[-–/]\s*(\d{2})\b")


@dataclass(frozen=True)
class Period:
    """One column's period: kind, fiscal year (the calendar year it ends in) and the header.

    ``explicit`` is False when the header names neither a year nor a part-year period (only a
    date, e.g. "December 31, 2023" under a centred "For the year ended"); ``month`` is the
    month the period ends in, when printed.
    """

    kind: Literal["year", "stub"]
    year: int | None
    label: str
    explicit: bool = True
    month: str | None = None


def parse_period(header: str) -> Period:
    """Classify a column header such as "As at and for the Financial Year ended March 31, 2024"."""
    text = " ".join(header.split())
    stub, full = _STUB.search(text) is not None, _FULL.search(text) is not None
    kind: Literal["year", "stub"] = "stub" if stub else "year"
    months = _MONTH.findall(text)
    year: int | None = None
    if m := _FY_SPAN.search(text):
        year = int(m[1][:2] + m[2])  # "2023-24" ends in 2024
    elif years := _YEAR.findall(text):
        year = int(years[-1])
    elif m := _FY_SHORT.search(text):
        year = 2000 + int(m[1])
    return Period(
        kind=kind, year=year, label=text, explicit=stub or full,
        month=months[-1].lower()[:3] if months else None,
    )  # fmt: skip


def rank_years(periods: list[Period]) -> dict[int, str]:
    """Column index → "latest" / "latest-1" / "latest-2" for full-year columns with a year.

    The first column wins when two columns show the same year (e.g. a pro forma column). A column
    with only a date counts as a full year when it ends in the same month as a column that says
    "year", so a stub whose "nine months" label sits elsewhere is not ranked as a year. When no
    column says "year" with a month (balance-sheet "As at" dates), the oldest dated column sets
    the fiscal month: the oldest period shown is always a full year.
    """
    year_months: set[str | None] = {
        p.month for p in periods if p.kind == "year" and p.explicit and p.month
    }
    if not year_months:
        dated = [p for p in periods if p.kind == "year" and p.year is not None and p.month]
        if dated:
            year_months = {min(dated, key=lambda p: p.year or 0).month}
    seen: dict[int, int] = {}
    for i, p in enumerate(periods):
        if not p.explicit and year_months and p.month not in year_months:
            continue
        if p.kind == "year" and p.year is not None and p.year not in seen:
            seen[p.year] = i
    ordered = sorted(seen, reverse=True)[: len(PERIOD_KEYS)]
    return {seen[y]: PERIOD_KEYS[k] for k, y in enumerate(ordered)}
