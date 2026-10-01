"""Two question-aware nudges for retrieval, both measured on the dev questions only (ADR-047).

1. **Cover pages.** The registrar, lead managers, promoters, issue size, price and face value are
   printed on the first pages of the RHP and Prospectus, in a block that reads like a title page
   and ranks poorly against body text that repeats the question's words. When the question asks
   for one of those facts, the passages of pages 1-3 are added to the candidate pool before the
   reranker, so the reranker (not a fixed rule) decides whether they make the top.
2. **Prospectus first for the final price.** The RHP prints ``[●]`` for the offer price and the
   amounts that depend on it; the Prospectus has the numbers. For those questions Prospectus
   passages are placed ahead of RHP ones. Other questions are untouched.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from finsight.core.schemas import Passage

COVER_PAGES = 3  # the title block, contacts and "The Offer" summary start here
COVER_EXTRA = 4  # at most this many cover passages join the pool

_COVER_CUES = re.compile(
    r"registrar|lead managers?|\bbrlms?\b|book running|promoters?|"
    r"(?:total )?(?:issue|offer) size|total (?:issue|offer)|"
    r"size of (?:this |the )?(?:ipo|issue|offer)|total size|"
    r"(?:offer|issue|allotment|allotted) price|price band|price .{0,30}allot|"
    r"face value|fresh issue|offer for sale|\bofs\b|"
    r"रजिस्ट्रार|लीड मैनेजर|बुक रनिंग|प्रमोटर|कुल (?:इश्यू|निर्गम|ऑफर)|(?:इश्यू|ऑफर) साइज़?|"
    r"(?:ऑफर|इश्यू) प्राइस|प्राइस बैंड|मूल्य (?:दायरा|बैंड)|फेस वैल्यू|अंकित मूल्य|"
    r"फ्रेश इश्यू|ऑफर फॉर सेल|निर्गम मूल्य|निर्गम आकार|कुल साइज़?|शेयर किस भाव|किस भाव|"
    r"(?:ipo|आईपीओ) का (?:कुल )?साइज़?",
    re.IGNORECASE,
)
_PROSPECTUS_CUES = re.compile(
    r"(?:offer|issue|final|cut-?off) price|price per (?:equity )?share|"
    r"(?:total )?(?:issue|offer) size|"
    r"total (?:issue|offer)|total size|size of (?:this |the )?(?:ipo|issue|offer)|"
    r"price .{0,30}allot|allotted price|amount raised|aggregating|किस भाव|कुल साइज़?|"
    r"(?:ऑफर|इश्यू|निर्गम) (?:प्राइस|मूल्य)|कुल (?:इश्यू|निर्गम|ऑफर)|(?:इश्यू|ऑफर) साइज़?|"
    r"निर्गम आकार|कितना पैसा जुटा",
    re.IGNORECASE,
)


def wants_cover(question: str) -> bool:
    return _COVER_CUES.search(question) is not None


def prefers_prospectus(question: str) -> bool:
    return _PROSPECTUS_CUES.search(question) is not None


def cover_candidates(passages: Sequence[Passage], prefer_prospectus: bool = False) -> list[int]:
    """Indices of the first-pages passages, the preferred document's first, in page order."""
    cover = [
        (i, p) for i, p in enumerate(passages) if p.page_start <= COVER_PAGES and p.page_end <= 6
    ]
    first = "prospectus" if prefer_prospectus else "rhp"
    cover.sort(key=lambda t: (t[1].doc_type != first, t[1].page_start, t[0]))
    return [i for i, _ in cover][:COVER_EXTRA]


def inject(
    question: str,
    passages: Sequence[Passage],
    order: list[tuple[int, float]],
    pool: int,
) -> list[tuple[int, float]]:
    """``order`` (index, score) with cover passages appended when the question asks for a cover
    fact. The pool may grow by ``COVER_EXTRA``; scores of injected passages are the pool's lowest,
    so without a reranker they trail the real hits."""
    if not wants_cover(question):
        return order[:pool]
    have = {i for i, _ in order[:pool]}
    floor = min((s for _, s in order), default=0.0)
    extra = [
        (i, floor)
        for i in cover_candidates(passages, prefers_prospectus(question))
        if i not in have
    ]
    return order[:pool] + extra


def prospectus_first(
    question: str, passages: Sequence[Passage], order: list[tuple[int, float]]
) -> list[tuple[int, float]]:
    """Final-price questions: Prospectus passages ahead of RHP ones (stable within each group).
    The RHP prints the price as a placeholder, so its passage cannot answer these questions."""
    if not prefers_prospectus(question):
        return order
    return sorted(order, key=lambda t: passages[t[0]].doc_type != "prospectus")
