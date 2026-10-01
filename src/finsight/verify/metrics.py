"""Which metric is a number about? A keyword map for English, Hindi and Hinglish.

The verifier needs this to tell "the fresh issue is ₹ 26,260 million" from "the offer for sale
is ₹ 26,260 million": same number, different claim (02 section 10.3, step 2). Prospectus prose
names the metric first and the amount after it ("a fresh issue of up to ... aggregating up to
₹ 26,260 million"), so an amount belongs to the nearest keyword *before* it; only when nothing
precedes it does a keyword right after it count ("₹ 10 face value").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BEFORE = 160  # characters, about 20-25 tokens (02 section 10.3)
AFTER = 40

_PATTERNS: dict[str, str] = {
    "fresh_issue": r"fresh\s+issue|फ्रेश\s+इश्यू|नया\s+इश्यू|नए\s+इश्यू|ताज़ा\s+निर्गम",
    "ofs": (
        r"offer\s+for\s+sale|\bOFS\b|ऑफर\s+फॉर\s+सेल|ओएफएस|"
        r"बिक्री\s+(?:के\s+लिए\s+)?(?:प्रस्ताव|पेशकश)"
    ),
    "total_issue": (
        r"total\s+(?:issue|offer)(?:\s+size)?|(?:issue|offer)\s+size|"
        r"initial\s+public\s+offer(?:ing)?|कुल\s+(?:इश्यू|ऑफर|निर्गम)|"
        r"(?:इश्यू|ऑफर|आईपीओ|IPO)\s+(?:का\s+)?(?:कुल\s+)?(?:साइज़|साइज|आकार)"
    ),
    "price_band": r"price\s+band|प्राइस\s+बैंड|मूल्य\s+(?:दायरा|बैंड)",
    "offer_price": (
        r"(?:offer|issue)\s+price|(?:ऑफर|इश्यू)\s+(?:प्राइस|मूल्य)|"
        r"(?:निर्गम|पेशकश)\s+मूल्य"
    ),
    "face_value": r"face\s+value|फेस\s+वैल्यू|अंकित\s+मूल्य",
    "revenue": r"revenue(?:\s+from\s+operations)?|total\s+income|राजस्व|रेवेन्यू",
    "ebitda": r"\bEBITDA\b|एबिटडा",
    "profit": (
        r"profit\s+(?:after|before)\s+tax|\bPAT\b|(?:net\s+)?(?:profit|loss)(?:es)?|"
        r"मुनाफ[ाे]|लाभ|घाटा|घाटे|हानि"
    ),
    "net_worth": r"net\s+worth|नेट\s+वर्थ|निवल\s+मूल्य",
    "borrowings": r"borrowings?|\bdebt\b|कर्ज़?|ऋण",
    "lot_size": r"(?:bid\s+)?lot(?:\s+size)?|लॉट",
    "holding": r"shareholding|\bholding\b|\bstake\b|हिस्सेदारी",
}
_COMPILED = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _PATTERNS.items()]
PER_SHARE = {"face_value", "offer_price", "price_band", "lot_size"}
_BREAK = re.compile(r"[.।;]\s")  # a keyword in an earlier sentence does not name this amount


@dataclass(frozen=True)
class MetricHit:
    metric: str
    start: int
    end: int


def find_metrics(text: str) -> list[MetricHit]:
    """Metric keywords in ``text``, in order; of two overlapping hits the earlier one stays."""
    hits = sorted(
        (MetricHit(name, m.start(), m.end()) for name, rx in _COMPILED for m in rx.finditer(text)),
        key=lambda h: (h.start, -(h.end - h.start)),
    )
    kept: list[MetricHit] = []
    for hit in hits:
        if not kept or hit.start >= kept[-1].end:
            kept.append(hit)  # "fresh issue size" is the fresh issue, not "issue size"
    return kept


def metric_at(
    text: str,
    start: int,
    end: int,
    hits: list[MetricHit] | None = None,
    amounts: list[tuple[int, int]] | None = None,
) -> str | None:
    """The metric the amount at ``text[start:end]`` belongs to, or None when nothing names it.

    ``amounts``: spans of every amount in ``text``. A per-share keyword (face value, price)
    names only the first amount after it: in "a fresh issue of 10 shares of face value of ₹ 1
    each aggregating up to ₹ 300 crore", ₹ 300 crore is the fresh issue, not the face value.
    """
    hits = find_metrics(text) if hits is None else hits
    before = [h for h in hits if h.end <= start and start - h.end <= BEFORE]
    for hit in reversed(before):
        if _BREAK.search(text, hit.end, start):
            break
        between = any(hit.end <= a and b <= start for a, b in amounts or [])
        if not (hit.metric in PER_SHARE and between):
            return hit.metric
    after = [h for h in hits if h.start >= end and h.start - end <= AFTER]
    for hit in after:
        if not _BREAK.search(text, end, hit.start):
            return hit.metric
    return None
