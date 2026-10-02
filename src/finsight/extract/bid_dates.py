"""The date the bid or offer closed, read from the Prospectus cover (run 2).

The Prospectus prints "BID/OFFER CLOSED ON: Monday, November 10, 2025" in the timetable block on
its first pages. The workspace header shows it as "Bid closed 10 Nov 2025 (Prospectus p. 3)", so
the date is grounded in the document, not typed from memory (``configs/ipo_meta.yaml`` holds only
the listing date, which no filing contains). First match wins; a date that does not parse is
dropped rather than guessed.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from finsight.core.schemas import BidClosed, ParsedDoc

SEARCH_PAGES = 12  # the timetable block is on the cover pages
_NAMES = "January February March April May June July August September October November December"
_MONTHS = _NAMES.lower().split()
_MONTH = "|".join(_NAMES.split() + [m[:3].capitalize() for m in _MONTHS])
# "BID/OFFER CLOSED ON Monday, ..." as printed, and the variants the ten prospectuses use: no
# "ON" ("CLOSED Friday, ..."), the typo "CLOSEED", no "BID/OFFER" in front ("... OPENED ON ...
# CLOSED ON Wednesday ..."), no comma after the weekday, a comma after the month ("June, 27, 2025").
_CLOSED = re.compile(
    r"(?:(?:BID\s*/\s*)?(?:OFFER|ISSUE)\s+)?CLOSE+D?(?:\s+ON)?\s*(?:\(\d\)|\*|#|\^)*\s*:?\s*"
    r"(?:(?:Mon|Tues?|Wednes|Thurs?|Fri|Satur|Sun)[a-z]*\s*,?\s*)?"
    rf"(?:(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m1>{_MONTH})\.?,?\s+(?P<y1>\d{{4}})"
    rf"|(?P<m2>{_MONTH})\.?,?\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<y2>\d{{4}}))",
    re.IGNORECASE,
)


def _month(word: str) -> int | None:
    key = word.lower()[:3]
    return next((i for i, m in enumerate(_MONTHS, 1) if m[:3] == key), None)


def parse_closed(text: str) -> tuple[date, str] | None:
    """``(date, matched text)`` of the first "closed on" date in ``text``, or ``None``."""
    squashed = " ".join(text.split())
    for m in _CLOSED.finditer(squashed):
        day = m.group("d1") or m.group("d2")
        month = _month(m.group("m1") or m.group("m2"))
        year = m.group("y1") or m.group("y2")
        try:
            when = datetime(int(year), month or 0, int(day)).date()
        except ValueError:
            continue
        return when, m.group(0)
    return None


def find_bid_closed(doc: ParsedDoc) -> BidClosed | None:
    """The closing date and its page, searched on the first pages of a Prospectus."""
    for page in doc.pages[:SEARCH_PAGES]:
        found = parse_closed(page.text)
        if found is not None:
            return BidClosed(closed_on=found[0], page=page.number, text=found[1])
    return None
