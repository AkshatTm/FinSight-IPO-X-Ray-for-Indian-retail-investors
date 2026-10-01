"""Three question-aware nudges for retrieval, both measured on the dev questions only (ADR-047).

1. **Cover pages.** The registrar, lead managers, promoters, issue size, price and face value are
   printed on the first pages of the RHP and Prospectus, in a block that reads like a title page
   and ranks poorly against body text that repeats the question's words. When the question asks
   for one of those facts, the passages of pages 1-3 are added to the candidate pool before the
   reranker, so the reranker (not a fixed rule) decides whether they make the top.
2. **Prospectus first for the final price.** The RHP prints ``[●]`` for the offer price and the
   amounts that depend on it; the Prospectus has the numbers. For those questions Prospectus
   passages are placed ahead of RHP ones. Other questions are untouched.
3. **Objects of the offer.** "How will the money be used?" is answered by the objects table, but
   its words ("capital expenditure", "repayment of borrowings") do not overlap the question, so
   it ranks below boilerplate that repeats "offer" and "proceeds" (P3.6: Ather's top 5 held no
   objects page). When the question asks about the use of money, the passages of the
   ``objects_of_the_offer`` section join the pool, as the cover pages do.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from finsight.core.schemas import Passage

COVER_PAGES = 3  # the title block, contacts and "The Offer" summary start here
COVER_EXTRA = 4  # at most this many cover passages join the pool
OBJECTS_SECTION = "objects_of_the_offer"
OBJECTS_EXTRA = 4  # at most this many objects-section passages join the pool

_NUKTA = "\u093c"  # "ऑफ़र" and "ऑफर" are the same word to a reader


def _norm(question: str) -> str:
    return unicodedata.normalize("NFC", question).replace(_NUKTA, "").casefold()


_COVER_CUES = re.compile(
    r"registrar|lead managers?|\bbrlms?\b|book running|promoters?|"
    r"(?:total )?(?:issue|offer) size|total (?:issue|offer)|"
    r"size of (?:this |the )?(?:ipo|issue|offer)|total size|"
    r"(?:offer|issue|allotment|allotted) price|price band|price .{0,30}allot|"
    r"face value|fresh issue|offer for sale|\bofs\b|"
    r"रजिस्ट्रार|रजिस्ट्रर|लीड\s*मैनेजर|बुक\s*रनिंग|प्रमोटर|कुल\s*(?:इश्यू|इश्यु|निर्गम|ऑफर)|"
    r"(?:इश्यू|ऑफर)\s*साइज़?|"
    r"(?:ऑफर|इश्यू)\s*प्राइस|प्राइस\s*बैंड|मूल्य\s*(?:दायरा|बैंड)|फेस\s*व[ेै]?ल्यू|अंकित\s*मूल्य|"
    r"फ्रेश\s*इश्यू|ऑफर\s*फॉर\s*सेल|निर्गम\s*मूल्य|निर्गम\s*आकार|कुल\s*साइज़?|"
    r"शेयर\s*किस\s*भाव|किस\s*भाव|(?:ipo|आईपीओ)\s*का\s*(?:कुल\s*)?साइज़?|"
    r"kul\s+(?:issue|offer)|(?:ipo|issue|offer)\s+ka\s+(?:kul\s+)?(?:size|price)|kis\s+bhav|"
    r"share\s+ka\s+(?:bhav|price)|registrar\s+kaun|promoter\s+kaun",
    re.IGNORECASE,
)
_PROSPECTUS_CUES = re.compile(
    r"(?:offer|issue|final|cut-?off) price|price per (?:equity )?share|"
    r"(?:total )?(?:issue|offer) size|"
    r"total (?:issue|offer)|total size|size of (?:this |the )?(?:ipo|issue|offer)|"
    r"price .{0,30}allot|allotted price|amount raised|aggregating|किस\s*भाव|कुल\s*साइज़?|"
    r"(?:ऑफर|इश्यू|निर्गम)\s*(?:प्राइस|मूल्य)|कुल\s*(?:इश्यू|इश्यु|निर्गम|ऑफर)|"
    r"(?:इश्यू|ऑफर)\s*साइज़?|निर्गम\s*आकार|कितना\s*पैसा\s*जुटा|"
    r"kul\s+(?:issue|offer)|(?:ipo|issue|offer)\s+ka\s+(?:kul\s+)?(?:size|price)|kis\s+bhav",
    re.IGNORECASE,
)


_OBJECTS_CUES = re.compile(
    r"use of (?:the )?(?:net )?(?:ipo )?(?:proceeds|funds|money)|objects? of (?:the |this )?(?:offer|issue)|"
    r"(?:money|funds?|proceeds|capital|amount).{0,40}(?:used|spent|utili[sz]ed|utili[sz]ation|go(?:es)? (?:to|towards))|"
    r"(?:used|spent|utili[sz]ed) for.{0,40}(?:money|funds?|proceeds)|where (?:will|does|is) .{0,30}(?:money|funds?|proceeds)|"
    r"पैसा?े?\s*(?:का\s*)?(?:कहाँ|कहां|किस\s*काम|कैसे\s*(?:खर्च|इस्तेमाल))|"
    r"(?:पैसे|धन|राशि|फंड)\s*का\s*(?:उपयोग|इस्तेमाल|इस्तमाल)|(?:उपयोग|इस्तेमाल).{0,15}(?:पैसे|धन|राशि)|"
    r"ऑफर\s*के\s*उद्देश्य|उद्देश्य.{0,20}(?:ऑफर|इश्यू)|"
    r"paisa\s+(?:kahan|kaha|kidhar|kis\s+kaam)|paise\s+(?:kahan|kaha|kis\s+kaam)|"
    r"(?:paisa|paise|raqam)\s+.{0,20}(?:use|istemal|upyog)|upyog\s+kaise",
    re.IGNORECASE,
)


def wants_objects(question: str) -> bool:
    return _OBJECTS_CUES.search(_norm(question)) is not None


def objects_candidates(passages: Sequence[Passage]) -> list[int]:
    """Indices of the objects-of-the-offer passages, RHP first, in page order."""
    rows = [(i, p) for i, p in enumerate(passages) if p.section_id == OBJECTS_SECTION]
    rows.sort(key=lambda t: (t[1].doc_type != "rhp", t[1].page_start, t[0]))
    return [i for i, _ in rows][:OBJECTS_EXTRA]


def wants_cover(question: str) -> bool:
    return _COVER_CUES.search(_norm(question)) is not None


def prefers_prospectus(question: str) -> bool:
    return _PROSPECTUS_CUES.search(_norm(question)) is not None


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
    cover, objects = wants_cover(question), wants_objects(question)
    if not (cover or objects):
        return order[:pool]
    have = {i for i, _ in order[:pool]}
    floor = min((s for _, s in order), default=0.0)
    wanted = cover_candidates(passages, prefers_prospectus(question)) if cover else []
    wanted += objects_candidates(passages) if objects else []
    extra: list[tuple[int, float]] = []
    for i in wanted:
        if i not in have:
            have.add(i)
            extra.append((i, floor))
    return order[:pool] + extra


def prospectus_first(
    question: str, passages: Sequence[Passage], order: list[tuple[int, float]]
) -> list[tuple[int, float]]:
    """Final-price questions: Prospectus passages ahead of RHP ones (stable within each group).
    The RHP prints the price as a placeholder, so its passage cannot answer these questions."""
    if not prefers_prospectus(question):
        return order
    return sorted(order, key=lambda t: passages[t[0]].doc_type != "prospectus")
