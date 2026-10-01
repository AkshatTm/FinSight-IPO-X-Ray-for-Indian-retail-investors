"""Propagation: find the seed value again in other passages of the same document.

A passage becomes a training example when it holds the *same value* as the seed (by
``normalize.equal``: ₹ 3,000 million == Rs. 300 crore) and, nearby, a word that names the metric
("fresh issue", "offer for sale", ...). Names are matched fuzzily (case, punctuation, Ltd ==
Limited); a list trains on one span that covers all of its names. Only passages in the field's
expected sections are searched (05 section 3).

v2 (after the 50-row audit, ADR-041): a face value counts only when its sentence is about equity
shares (not preference shares, CCPS, OCRPS, debentures); a name keeps its closing bracket
("(HUF)"); a list span grows over neighbouring company names the seed did not know.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsight.core.schemas import (
    Amount,
    FieldSpec,
    ListValue,
    ParsedDoc,
    Section,
    TableValue,
    TextValue,
    Value,
)
from finsight.extract import build_passages
from finsight.normalize import equal, parse_amounts
from finsight.weaklabel.seeds import Seed

MAX_POSITIVES = 8  # per field and document: templated repeats should not dominate the set
MAX_LIST_SPAN = 700  # characters; a longer "list" is several sentences, not one answer
BEFORE, AFTER = 250, 120  # the metric word must sit this close to the value
KEYWORDS = {
    "fresh_issue_size": r"fresh\s+issue",
    "ofs_shares": r"offer\s+for\s+sale|selling\s+shareholder",
    "ofs_amount": r"offer\s+for\s+sale|selling\s+shareholder",
    "total_issue_size": r"\boffer\b|\bissue\b",
    "face_value": r"face\s+value",
    "book_running_lead_managers": r"lead\s+manager|\bBRLMs?\b",
    "registrar": r"registrar",
    "promoters": r"promoter",
}


@dataclass(frozen=True)
class Example:
    id: str
    ipo_id: str
    field_id: str
    passage_id: str
    page: int
    context: str
    answer_text: str  # "" for a negative
    answer_start: int  # -1 for a negative
    is_impossible: bool


def _keyword_near(field_id: str, text: str, start: int, end: int) -> bool:
    window = text[max(0, start - BEFORE) : end + AFTER]
    return re.search(KEYWORDS[field_id], window, re.IGNORECASE) is not None


def _name_pattern(name: str) -> re.Pattern[str]:
    """Words in order, any punctuation or spacing between them, Ltd == Limited."""
    words = re.findall(r"[a-z0-9&]+", name.casefold())
    parts = [r"(?:limited|ltd\.?)" if w in ("limited", "ltd") else re.escape(w) for w in words]
    pattern = r"\b" + r"[\s.,()'/-]{0,4}".join(parts)
    if parts and parts[-1].startswith("(?:limited"):
        return re.compile(pattern, re.IGNORECASE)  # "Ltd." keeps its full stop in the span
    return re.compile(pattern + r"\b", re.IGNORECASE)


_EQUITY = re.compile(r"equity\s+shares?", re.IGNORECASE)
_OTHER_CLASS = re.compile(
    r"preference|\b(?:CCPS|CCCPS|OCRPS|OCCPS|OCPS|RPS|NCDs?)\b|debentures?|\bbonds?\b|warrants?",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"[.;]\s")
_PER = re.compile(r"[\s/-]*(?:per\s+)?", re.IGNORECASE)


def _about_equity(text: str, start: int, end: int) -> bool:
    """The share class named closest to the amount, within its sentence, must be equity shares."""
    lo = max(0, start - BEFORE)
    ends = [m.end() for m in _SENTENCE_END.finditer(text, lo, start)]
    lo = ends[-1] if ends else lo
    stop = _SENTENCE_END.search(text, end, end + AFTER)
    hi = stop.start() if stop else min(len(text), end + AFTER)

    def gap(pattern: re.Pattern[str]) -> int | None:
        """Distance to the nearest mention before the amount, or right after it ("₹10 per X")."""
        gaps = []
        for m in pattern.finditer(text, lo, hi):
            if m.end() <= start:
                gaps.append(start - m.end())
            elif m.start() >= end and _PER.fullmatch(text, end, m.start()):
                gaps.append(0)
        return min(gaps) if gaps else None

    equity, other = gap(_EQUITY), gap(_OTHER_CLASS)
    return equity is not None and (other is None or equity < other)


def _amount_span(field_id: str, value: Amount, text: str) -> tuple[int, int] | None:
    for span in parse_amounts(text):
        same = span.amount.kind == value.kind and equal(span.amount, value)
        if not (same and _keyword_near(field_id, text, span.start, span.end)):
            continue
        if field_id == "face_value" and not _about_equity(text, span.start, span.end):
            continue
        return span.start, span.end
    return None


def _name_span(name: str, text: str) -> tuple[int, int] | None:
    m = _name_pattern(name).search(text)
    if m is None:
        return None
    end = m.end()
    if m.group().count("(") > m.group().count(")") and text[end : end + 1] == ")":
        end += 1  # "DEEPAK AGARWAL (HUF)" keeps its bracket
    return m.start(), end


_COMPANY = (
    r"[A-Z][\w&.'-]*(?:\s+(?:[A-Z(][\w&.'()-]*|and|of|&)){0,9}?\s+(?:Limited|LIMITED|Ltd\.?|LTD\.?)"
)
_JOIN = r"\s*(?:,\s*and\b|,|\band\b|&)\s*"
_ITEM_BEFORE = re.compile(rf"{_COMPANY}{_JOIN}$")
_ITEM_AFTER = re.compile(rf"{_JOIN}{_COMPANY}")
_OTHER_ROLE = re.compile(r"registrar|syndicate|counsel|auditor|banker|monitoring", re.IGNORECASE)


def _whole_list(text: str, start: int, end: int) -> tuple[int, int]:
    """Grow a list span over neighbouring company names: the seed only knows some firms."""
    while (m := _ITEM_BEFORE.search(text, max(0, start - 160), start)) is not None:
        start = m.start()
    while (m := _ITEM_AFTER.match(text, end)) is not None:
        if _OTHER_ROLE.search(text, m.end(), m.end() + 60):
            break  # "... and KFin Technologies Limited is the Registrar"
        end = m.end()
    return start, end


def find_answer(field: FieldSpec, value: Value, text: str) -> tuple[int, int] | None:
    """Character span of the seed value in ``text``, or None."""
    if isinstance(value, TableValue):
        return None
    if isinstance(value, TextValue):
        span = _name_span(value.text, text)
        if span and _keyword_near(field.id, text, *span):
            return span
        return None
    if isinstance(value, ListValue):
        spans = []
        for item in value.items:
            span = _name_span(item, text)
            if span is None:
                return None
            spans.append(span)
        start, end = min(s for s, _ in spans), max(e for _, e in spans)
        if end - start > MAX_LIST_SPAN or not _keyword_near(field.id, text, start, end):
            return None
        grown = _whole_list(text, start, end)
        return grown if grown[1] - grown[0] <= MAX_LIST_SPAN else (start, end)
    return _amount_span(field.id, value, text)


def propagate(
    doc: ParsedDoc,
    sections: list[Section],
    field: FieldSpec,
    seed: Seed,
    max_positives: int = MAX_POSITIVES,
) -> list[Example]:
    """Positive examples: passages of the field's sections that contain the seed value."""
    out: list[Example] = []
    for passage in build_passages(doc, sections, field):
        span = find_answer(field, seed.value, passage.text)
        if span is None:
            continue
        start, end = span
        out.append(
            Example(
                id=f"{passage.id}:{field.id}",
                ipo_id=doc.ipo_id,
                field_id=field.id,
                passage_id=passage.id,
                page=passage.page,
                context=passage.text,
                answer_text=passage.text[start:end],
                answer_start=start,
                is_impossible=False,
            )
        )
        if len(out) >= max_positives:
            break
    return out
