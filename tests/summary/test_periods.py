"""Column headers → periods, and which columns are the last three full fiscal years."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from finsight.summary import parse_period, rank_years


@pytest.mark.parametrize(
    ("header", "kind", "year"),
    [
        ("As at and for the Financial Year ended March 31, 2024", "year", 2024),
        ("As at and for nine months ended December 31, 2024", "stub", 2024),
        ("For the three months ended June 30, 2025*", "stub", 2025),
        ("For the year ended 31 March 2022", "year", 2022),
        ("Fiscal 2024", "year", 2024),
        ("FY24", "year", 2024),
        ("2023-24", "year", 2024),
        ("Six-month period ended September 30, 2024", "stub", 2024),
        ("December 31, 2023", "year", 2023),
        ("As at and for the Financial Year", "year", None),
    ],
)
def test_parse_period(header: str, kind: str, year: int | None) -> None:
    p = parse_period(header)
    assert (p.kind, p.year) == (kind, year)


def test_dates_only_columns_are_not_explicit() -> None:
    assert not parse_period("December 31, 2023").explicit
    assert parse_period("For the year ended December 31, 2022").explicit


def test_rank_skips_stubs_and_orders_latest_first() -> None:
    headers = [
        "nine months ended December 31, 2024",
        "nine months ended December 31, 2023",
        "Financial Year ended March 31, 2024",
        "Financial Year ended March 31, 2023",
        "Financial Year ended March 31, 2022",
    ]
    assert rank_years([parse_period(h) for h in headers]) == {
        2: "latest",
        3: "latest-1",
        4: "latest-2",
    }


def test_rank_orders_by_year_not_by_position() -> None:
    headers = ["Fiscal 2022", "Fiscal 2023", "Fiscal 2024"]
    assert rank_years([parse_period(h) for h in headers]) == {
        2: "latest",
        1: "latest-1",
        0: "latest-2",
    }


def test_centred_year_header_reaches_date_only_columns() -> None:
    # Hexaware (dev): one "For the year ended" over three December columns.
    headers = [
        "For the nine months ended September 30, 2024",
        "For the nine months ended September 30, 2023",
        "December 31, 2023",
        "For the year ended December 31, 2022",
        "December 31, 2021",
    ]
    assert rank_years([parse_period(h) for h in headers]) == {
        2: "latest",
        3: "latest-1",
        4: "latest-2",
    }


def test_stub_without_its_label_is_not_ranked() -> None:
    # The "nine months" words sit elsewhere; the September column ends in the wrong month.
    headers = ["September 30, 2024", "For the year ended March 31, 2024", "March 31, 2023"]
    assert rank_years([parse_period(h) for h in headers]) == {1: "latest", 2: "latest-1"}


def test_balance_sheet_dates_use_the_oldest_columns_month() -> None:
    headers = [
        "As at 31 December 2024",
        "As at 31 December 2023",
        "As at 31 March 2024",
        "As at 31 March 2023",
        "As at 31 March 2022",
    ]
    assert rank_years([parse_period(h) for h in headers]) == {
        2: "latest",
        3: "latest-1",
        4: "latest-2",
    }


def test_columns_without_a_year_are_never_ranked() -> None:
    assert rank_years([parse_period("For the year ended"), parse_period("Fiscal")]) == {}


def test_duplicate_years_keep_the_first_column() -> None:
    assert rank_years([parse_period("Fiscal 2024"), parse_period("Fiscal 2024 (pro forma)")]) == {
        0: "latest"
    }


@given(st.lists(st.text(max_size=60), max_size=8))
def test_rank_never_crashes_and_gives_at_most_three(headers: list[str]) -> None:
    ranks = rank_years([parse_period(h) for h in headers])
    assert len(ranks) <= 3
    assert sorted(ranks.values()) == sorted(["latest", "latest-1", "latest-2"][: len(ranks)])
