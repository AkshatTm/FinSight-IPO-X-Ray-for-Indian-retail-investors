"""Which metric is a number about? A keyword map for English, Hindi and Hinglish.

The verifier needs this to tell "the fresh issue is ₹ 26,260 million" from "the offer for sale
is ₹ 26,260 million": same number, different claim (02 section 10.3, step 2). Three cues, read
off real cover pages:

1. A defined term right after the amount names it: ``₹ 29,808 MILLION (THE "OFFER")``.
2. Otherwise the nearest keyword *before* the amount, in the same sentence: prospectus prose
   names the metric first ("a fresh issue of ... aggregating up to ₹ 26,260 million"). A
   per-share keyword (face value, price, premium) names only the first amount after it.
3. Only when nothing precedes it, a keyword right after the amount ("₹ 10 face value").

An amount can carry two metrics: in a pure offer for sale the total is also the OFS amount.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BEFORE = 320  # characters: one long legal sentence ("initial public offering of ... aggregating")
AFTER = 40
DEFINITION_GAP = 12  # "₹ 26,260 MILLION *^ (THE "FRESH ISSUE")": only footnote marks between

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
        r"(?:offer|issue)\s+price|(?:at\s+a\s+)?price\s+of|(?:ऑफर|इश्यू)\s+(?:प्राइस|मूल्य)|"
        r"(?:निर्गम|पेशकश)\s+मूल्य"
    ),
    "premium": r"(?:securities\s+|share\s+)?premium|प्रीमियम",
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
PER_SHARE = {"face_value", "offer_price", "price_band", "premium", "lot_size"}
_BREAK = re.compile(r"[.।;]\s")  # a keyword in an earlier sentence does not name this amount

# (THE "OFFER"), (the "Fresh Issue"): a defined term labels what stands before it
_DEFINITION = re.compile(r"\(\s*(?:the\s+)?[“\"']\s*([^”\"'()]{2,40}?)\s*[”\"']\s*\)", re.I)
_DEFINED = {
    "offer": "total_issue",
    "issue": "total_issue",
    "fresh issue": "fresh_issue",
    "offer for sale": "ofs",
    "offer price": "offer_price",
    "issue price": "offer_price",
}
_MARKS_ONLY = re.compile(r"[\s*^†‡#]*")


@dataclass(frozen=True)
class MetricHit:
    """A metric name (revenue, PAT, ...) found in a text span."""

    metric: str
    start: int
    end: int


class MetricIndex:
    """Keywords and defined terms of one text, found once and asked about many amounts."""

    def __init__(self, text: str, amounts: list[tuple[int, int]] | None = None) -> None:
        self.text = text
        self.amounts = amounts or []
        definitions = list(_DEFINITION.finditer(text))
        self.definitions = [
            MetricHit(_DEFINED[" ".join(m.group(1).casefold().split())], m.start(), m.end())
            for m in definitions
            if " ".join(m.group(1).casefold().split()) in _DEFINED
        ]
        inside = [(m.start(), m.end()) for m in definitions]
        self.hits = [
            h for h in find_metrics(text) if not any(a <= h.start and h.end <= b for a, b in inside)
        ]

    def at(self, start: int, end: int) -> tuple[str, ...]:
        """Metrics of the amount at ``text[start:end]``, strongest cue first; () when unnamed."""
        found: list[str] = []
        for d in self.definitions:
            gap = self.text[end : d.start]
            if 0 <= d.start - end <= DEFINITION_GAP and _MARKS_ONLY.fullmatch(gap):
                found.append(d.metric)
        before = [h for h in self.hits if h.end <= start and start - h.end <= BEFORE]
        for hit in reversed(before):
            if _BREAK.search(self.text, hit.end, start):
                break
            between = any(hit.end <= a and b <= start for a, b in self.amounts)
            if not (hit.metric in PER_SHARE and between):
                found.append(hit.metric)
                break
        if not found:
            after = [h for h in self.hits if h.start >= end and h.start - end <= AFTER]
            for hit in after:
                if not _BREAK.search(self.text, end, hit.start):
                    found.append(hit.metric)
                    break
        return tuple(dict.fromkeys(found))


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
    text: str, start: int, end: int, amounts: list[tuple[int, int]] | None = None
) -> str | None:
    """The first metric of the amount at ``text[start:end]``, or None when nothing names it."""
    found = MetricIndex(text, amounts).at(start, end)
    return found[0] if found else None
