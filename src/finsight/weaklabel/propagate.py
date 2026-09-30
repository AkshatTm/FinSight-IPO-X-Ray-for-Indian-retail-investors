"""Propagation: find the seed value again in other passages of the same document.

A passage becomes a training example when it holds the *same value* as the seed (by
``normalize.equal``: ₹ 3,000 million == Rs. 300 crore) and, nearby, a word that names the metric
("fresh issue", "offer for sale", ...). Names are matched fuzzily (case, punctuation, Ltd ==
Limited); a list trains on one span that covers all of its names. Only passages in the field's
expected sections are searched (05 section 3).
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


def _amount_span(field_id: str, value: Amount, text: str) -> tuple[int, int] | None:
    for span in parse_amounts(text):
        same = span.amount.kind == value.kind and equal(span.amount, value)
        if same and _keyword_near(field_id, text, span.start, span.end):
            return span.start, span.end
    return None


def find_answer(field: FieldSpec, value: Value, text: str) -> tuple[int, int] | None:
    """Character span of the seed value in ``text``, or None."""
    if isinstance(value, TableValue):
        return None
    if isinstance(value, TextValue):
        m = _name_pattern(value.text).search(text)
        if m and _keyword_near(field.id, text, m.start(), m.end()):
            return m.start(), m.end()
        return None
    if isinstance(value, ListValue):
        spans = []
        for item in value.items:
            m = _name_pattern(item).search(text)
            if m is None:
                return None
            spans.append((m.start(), m.end()))
        start, end = min(s for s, _ in spans), max(e for _, e in spans)
        if end - start > MAX_LIST_SPAN or not _keyword_near(field.id, text, start, end):
            return None
        return start, end
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
