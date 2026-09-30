from datetime import date

import pytest

from finsight.normalize import find_periods, parse_period

# (text, kind, fiscal year it ends, quarter, end date)
CASES = [
    ("FY24", "year", 2024, None, date(2024, 3, 31)),
    ("FY 2024", "year", 2024, None, date(2024, 3, 31)),
    ("FY'25", "year", 2025, None, date(2025, 3, 31)),
    ("FY2024-25", "year", 2025, None, date(2025, 3, 31)),
    ("FY 2023–24", "year", 2024, None, date(2024, 3, 31)),
    ("Fiscal 2024", "year", 2024, None, date(2024, 3, 31)),
    ("financial year 2023-24", "year", 2024, None, date(2024, 3, 31)),
    ("Q3FY25", "quarter", 2025, 3, date(2024, 12, 31)),
    ("Q1 FY2026", "quarter", 2026, 1, date(2025, 6, 30)),
    ("Q4FY24", "quarter", 2024, 4, date(2024, 3, 31)),
    ("quarter ended December 31, 2024", "quarter", 2025, 3, date(2024, 12, 31)),
    ("three months ended June 30, 2025", "quarter", 2026, 1, date(2025, 6, 30)),
    ("six months ended September 30, 2024", "half_year", 2025, None, date(2024, 9, 30)),
    ("nine months ended 31 December 2024", "nine_months", 2025, None, date(2024, 12, 31)),
    ("year ended March 31, 2024", "year", 2024, None, date(2024, 3, 31)),
    ("Fiscal Year ended 31st March, 2023", "year", 2023, None, date(2023, 3, 31)),
    ("as of March 31, 2025", "as_of", 2025, None, date(2025, 3, 31)),
    ("as at 30 June 2025", "as_of", 2026, 1, date(2025, 6, 30)),
]


@pytest.mark.parametrize(("text", "kind", "fy", "quarter", "end"), CASES)
def test_parse_period(text: str, kind: str, fy: int, quarter: int | None, end: date) -> None:
    period = parse_period(text)
    assert period is not None, text
    assert (period.kind, period.fy, period.quarter, period.end) == (kind, fy, quarter, end)
    assert period.raw == text


@pytest.mark.parametrize("text", ["2024", "₹ 800 crore", "FY", "Q5FY25", "FY2024-26", ""])
def test_not_a_period(text: str) -> None:
    assert parse_period(text) is None


def test_find_periods_in_a_sentence() -> None:
    text = "Revenue for FY24 was ₹ 1,250 crore and for the six months ended September 30, 2024 …"
    periods = find_periods(text)
    assert [(p.period.kind, p.period.fy) for p in periods] == [("year", 2024), ("half_year", 2025)]
    assert [text[p.start : p.end] for p in periods] == [
        "FY24", "six months ended September 30, 2024",
    ]  # fmt: skip
