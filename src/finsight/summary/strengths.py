"""Our Strengths (CC-06): the issuer's own list of strengths from "Our Business".

The section is a heading ("Our Strengths", "Our Competitive Strengths", "Key Strengths") followed
by one bold heading per strength and a paragraph under it, and ends at the strategies heading
("Our Strategies", "Our Growth Strategies"). Each item keeps the heading as printed, the first
sentence of its paragraph and its page. These are the company's claims, shown as such: nothing is
rewritten or scored here.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from finsight.core.schemas import Page, ParsedDoc, Section
from finsight.summary.layout import Line, lines_of
from finsight.summary.locate import section_pages

_HEADING = re.compile(
    r"^(?:\d{1,2}[.)]\s*)?(?:our\s+)?(?:key\s+|competitive\s+|principal\s+|core\s+)?"
    r"(?:business\s+)?strengths?\s*:?$",
    re.IGNORECASE,
)
_END = re.compile(
    r"^(?:\d{1,2}[.)]\s*)?(?:our\s+)?(?:key\s+|growth\s+|business\s+|future\s+)*strateg(?:y|ies)\b",
    re.IGNORECASE,
)
_ENUM = re.compile(r"^(?:\d{1,2}[.)]|[a-z][.)]|\([a-z0-9ivx]{1,4}\)|[•▪●■\-–])\s*", re.IGNORECASE)
_SENTENCE = re.compile(r"^(.{15,400}?[.!?])(?=\s+[A-Z“\"(]|\s*$)", re.DOTALL)
MAX_ITEMS = 15
MAX_PAGES = 14
MAX_HEADING_WORDS = 30
LINE_GAP = 16.0  # a bold heading wrapped onto the next line sits this close


class Strength(BaseModel):
    """One printed strength: its heading, the first sentence under it and the page."""

    heading: str
    sentence: str
    page: int


def _bold_prefix(line: Line) -> list[str]:
    out: list[str] = []
    for w in line.words:
        if not w.bold:
            break
        out.append(w.text)
    return out


def _clean(text: str) -> str:
    return _ENUM.sub("", " ".join(text.split())).strip(" :.–-")


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    m = _SENTENCE.match(text)
    return (m.group(1) if m else text[:300]).strip()


def extract_strengths(doc: ParsedDoc, sections: list[Section]) -> list[Strength]:
    """The strengths listed under "Our Strengths" in Our Business; ``[]`` when not found."""
    by_number = {p.number: p for p in doc.pages}
    pages: list[Page] = [
        by_number[n] for n in section_pages(sections, "our_business", 60) if n in by_number
    ]
    items: list[Strength] = []
    started = False
    pages_seen = 0
    heading: list[str] = []
    heading_page = 0
    body: list[str] = []
    last_top = -1e9

    def close() -> None:
        if heading:
            text = _clean(" ".join(heading))
            if text and len(text.split()) <= MAX_HEADING_WORDS:
                items.append(
                    Strength(heading=text, sentence=_first_sentence(" ".join(body)),
                             page=heading_page)
                )  # fmt: skip

    for page in pages:
        if started:
            pages_seen += 1
            if pages_seen > MAX_PAGES:
                break
        for line in lines_of(page.words):
            text = " ".join(line.text.split())
            bold = _bold_prefix(line)
            all_bold = len(bold) == len(line.words)
            if not started:
                if all_bold and _HEADING.match(text):
                    started = True
                continue
            if all_bold and _END.match(text):
                close()
                return items[:MAX_ITEMS]
            if all_bold and text:
                wrapped = heading and not body and line.top - last_top <= LINE_GAP
                if wrapped:
                    heading.append(text)
                else:
                    close()
                    heading, heading_page, body = [text], page.number, []
                last_top = line.top
                continue
            if len(bold) >= 3 and re.search(r"[.:]$", bold[-1]):  # inline "Bold lead-in. Text"
                close()
                heading, heading_page = [" ".join(bold)], page.number
                body = [" ".join(w.text for w in line.words[len(bold) :])]
                last_top = line.top
                continue
            if heading:
                body.append(text)
            if len(items) >= MAX_ITEMS:
                return items
    close() if started and heading else None
    return items[:MAX_ITEMS] if started else []
