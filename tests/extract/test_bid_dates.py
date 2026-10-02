from datetime import date

import pytest

from finsight.core.schemas import Page, ParsedDoc
from finsight.extract import find_bid_closed, parse_closed


def doc(pages: list[str]) -> ParsedDoc:
    return ParsedDoc(
        ipo_id="x", doc_type="prospectus", source_path="x.pdf", n_pages=len(pages), sha256="0",
        pages=[
            Page(number=i, width=595, height=842, words=[], text=t, is_scanned=False)
            for i, t in enumerate(pages, 1)
        ],
    )  # type: ignore[arg-type]  # fmt: skip


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("BID/OFFER OPENED ON: THURSDAY, NOVEMBER 6, 2025 "
         "BID/OFFER CLOSED ON: MONDAY, NOVEMBER 10, 2025",
         date(2025, 11, 10)),
        ("BID/ISSUE CLOSED ON(1): Friday, 7 November 2025", date(2025, 11, 7)),
        ("Bid / Offer Closed On Tuesday, Feb 11, 2025", date(2025, 2, 11)),
        ("OFFER CLOSED ON:\nMonday,\nJune 25th, 2025", date(2025, 6, 25)),
        # variants printed in the ten demo prospectuses
        ("BID/ OFFER OPENED ON Monday, April 28, 2025 CLOSED ON Wednesday April 30, 2025",
         date(2025, 4, 30)),
        ("BID/OFFER OPENED ON Wednesday, June 25, 2025 BID/OFFER CLOSED ON Friday, June, 27, 2025",
         date(2025, 6, 27)),
        ("BID/ OFFER OPENED Wednesday, September 10, 2025 "
         "BID/ OFFER CLOSED Friday, September 12, 2025#",
         date(2025, 9, 12)),
        ("BID/ OFFER OPENED ON Tuesday, November 4, BID/ OFFER CLOSEED ON Friday, November 7, 2025",
         date(2025, 11, 7)),
    ],
)  # fmt: skip
def test_closing_date_formats(text: str, expected: date) -> None:
    found = parse_closed(text)
    assert found is not None
    assert found[0] == expected


def test_no_date_and_impossible_dates_are_not_guessed() -> None:
    assert parse_closed("The Bid/Offer Opening Date is [●]") is None
    assert parse_closed("BID/OFFER CLOSED ON: Monday, February 30, 2025") is None
    assert parse_closed("BID/OFFER CLOSED ON: [●]") is None


def test_first_pages_of_the_prospectus_are_searched_and_the_page_is_kept() -> None:
    d = doc(["cover", "BID/OFFER CLOSED ON: Monday, November 10, 2025 more text", "later"])
    found = find_bid_closed(d)
    assert found is not None
    assert (found.closed_on, found.page) == (date(2025, 11, 10), 2)
    assert "CLOSED ON" in found.text
    assert find_bid_closed(doc(["nothing"] * 3)) is None
    assert find_bid_closed(doc(["x"] * 20 + ["BID/OFFER CLOSED ON: Monday, March 3, 2025"])) is None
