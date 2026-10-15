"""Column headers → reporting periods: a full fiscal year or a stub (part-year) period.

Red-flag inputs use the last three **full** fiscal years, latest first (gold v3 ``latest``,
``latest-1``, ``latest-2``). Stub periods ("nine months ended December 31, 2024") are read but
never ranked, so a nine-month loss is not compared with a full year. A column whose year cannot
be read is never ranked either (nothing is guessed from column order).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Literal

PERIOD_KEYS = ("latest", "latest-1", "latest-2")

_STUB = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|[1-9]|1[01])[\s-]*months?\b"
    r"|\bquarter\b|\bhalf[\s-]*year\b|\bq[1-4]\b|\bh1\b",
    re.IGNORECASE,
)
_VAGUE_STUB = re.compile(r"\bperiod ended\b", re.IGNORECASE)  # a short first year, or a stub
_YEAR_OR_PERIOD = re.compile(
    r"\b(?:year|fiscal)\s*/\s*period\b|\bperiod\s*/\s*(?:year|fiscal)\b", re.IGNORECASE
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
    month the period ends in, when printed. ``clear_stub`` marks a stub that names its length
    ("nine months"), unlike a bare "period ended".
    """

    kind: Literal["year", "stub"]
    year: int | None
    label: str
    explicit: bool = True
    month: str | None = None
    clear_stub: bool = False


def parse_period(header: str) -> Period:
    """Classify a column header such as "As at and for the Financial Year ended March 31, 2024"."""
    text = " ".join(header.split())
    clear = _STUB.search(text) is not None
    # "For the Fiscal/ period ended June 30, 2024" is used for full years and stubs alike: such
    # a column counts as a date only, so the fiscal month (rank_years) decides.
    either = _YEAR_OR_PERIOD.search(text) is not None and not clear
    stub = clear or (_VAGUE_STUB.search(text) is not None and not either)
    full = _FULL.search(text) is not None
    kind: Literal["year", "stub"] = "stub" if stub else "year"
    months = _MONTH.findall(text)
    year: int | None = None
    if m := _FY_SPAN.search(text):
        year = int(m[1][:2] + m[2])  # "2023-24" ends in 2024
    elif years := _YEAR.findall(text):
        # Two different years in one header: the column could not be told apart from a neighbour.
        year = int(years[0]) if len(set(years)) == 1 else None
    elif m := _FY_SHORT.search(text):
        year = 2000 + int(m[1])
    return Period(
        kind=kind, year=year, label=text, explicit=(stub or full) and not either,
        month=months[-1].lower()[:3] if months else None, clear_stub=clear,
    )  # fmt: skip


_FY_WORDS = re.compile(r"\bfiscal\b|\bfinancial year\b|\bfy\b", re.IGNORECASE)
_TWELVE = re.compile(r"\b(?:twelve|12)[\s-]*months\b", re.IGNORECASE)


def trailing_as_stub(periods: list[Period]) -> list[Period]:
    """ "Twelve months ended September 30" beside "Financial Year 2023" columns is a trailing
    period, not a fiscal year: it becomes a clear stub unless it ends in the fiscal month."""
    fiscal = [p for p in periods if p.kind == "year" and _FY_WORDS.search(p.label)]
    if not fiscal:
        return periods
    months = {p.month for p in fiscal if p.month}
    return [
        replace(p, kind="stub", clear_stub=True)
        if _TWELVE.search(p.label)
        and not _FY_WORDS.search(p.label)
        and (not months or p.month not in months)
        else p
        for p in periods
    ]


def rank_years(periods: list[Period]) -> dict[int, str]:
    """Column index → "latest" / "latest-1" / "latest-2" for full-year columns with a year.

    The first column wins when two columns show the same year (e.g. a pro forma column). A column
    with only a date counts as a full year when it ends in the same month as a column that says
    "year", so a stub whose "nine months" label sits elsewhere is not ranked as a year. When no
    column says "year" with a month (balance-sheet "As at" dates), the oldest dated column sets
    the fiscal month: the oldest period shown is always a full year. A column showing only a
    year ("2025" under a header centred over the other columns) is a full year when no column
    of the table is a part-year period. Nothing is ranked when a full-year column has no
    readable year, or when a column left out shows a later year than "latest" without naming
    itself a part-year period ("nine months"): either would shift "latest" onto an older column.
    Ranked years are consecutive; ranking stops at the first gap.
    """
    periods = trailing_as_stub(periods)
    year_months: set[str | None] = {
        p.month for p in periods if p.kind == "year" and p.explicit and p.month
    }
    if not year_months:
        dated = [p for p in periods if p.kind == "year" and p.year is not None and p.month]
        if dated:
            year_months = {min(dated, key=lambda p: p.year or 0).month}
    if any(p.kind == "year" and p.year is None for p in periods):
        return {}  # a year column whose year was not read: any ranking could be shifted
    any_stub = any(p.kind == "stub" for p in periods)
    seen: dict[int, int] = {}
    for i, p in enumerate(periods):
        if not p.explicit and p.month is None and any_stub:
            continue  # a bare "2025" next to part-year columns could be either
        if not p.explicit and p.month is not None and year_months and p.month not in year_months:
            continue
        if p.kind == "year" and p.year is not None and p.year not in seen:
            seen[p.year] = i
    ordered = sorted(seen, reverse=True)[: len(PERIOD_KEYS)]
    # Consecutive years only: a gap means a column in between was not read.
    for k in range(1, len(ordered)):
        if ordered[k] != ordered[k - 1] - 1:
            ordered = ordered[:k]
            break
    ranked = set(seen.values())
    if ordered and any(
        i not in ranked and p.year is not None and p.year > ordered[0] and not p.clear_stub
        for i, p in enumerate(periods)
    ):
        return {}
    return {seen[y]: PERIOD_KEYS[k] for k, y in enumerate(ordered)}
