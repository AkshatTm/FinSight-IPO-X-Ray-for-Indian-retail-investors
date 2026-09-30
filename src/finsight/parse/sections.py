"""Find the SEBI-standard sections of an RHP or Prospectus (02_ARCHITECTURE.md section 10.1).

Three signals vote:
1. **TOC** - the table of contents gives each title and its *printed* page; the footer
   numbers read in P1.1 turn that into a PDF page (median offset as fallback).
2. **Regex** - the title appears as a whole line near the top of that page.
3. **Font** - that heading is bold or clearly larger than the page's body text.
When the TOC page and the heading disagree, the heading wins if it is close by. When
there is no TOC entry, key sections are found by the heading scan alone.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import Literal

from finsight.core.schemas import Page, ParsedDoc, Section

Method = Literal["toc", "regex", "font"]

# The four sections the X-Ray depends on (G1 gate).
KEY_SECTIONS = ("cover", "the_offer", "capital_structure", "objects_of_the_offer")

# Canonical ids for SEBI ICDR titles; everything else gets a slug of its title.
_CANONICAL: list[tuple[str, re.Pattern[str]]] = [
    (sid, re.compile(rf"^{pat}$"))
    for sid, pat in [
        ("definitions", r"DEFINITIONS AND ABBREVIATIONS"),
        (
            "summary",
            r"(?:SUMMARY OF (THE OFFER DOCUMENT|THIS (RED HERRING )?PROSPECTUS)"
            r"|OFFER DOCUMENT SUMMARY)",
        ),
        ("risk_factors", r"RISK FACTORS"),
        ("the_offer", r"THE (OFFER|ISSUE)"),
        ("general_information", r"GENERAL INFORMATION"),
        ("capital_structure", r"CAPITAL STRUCTURE"),
        ("objects_of_the_offer", r"OBJECTS? OF THE (OFFER|ISSUE)"),
        ("basis_for_offer_price", r"BASIS FOR (THE )?(OFFER|ISSUE) PRICE"),
        ("our_promoters", r"OUR PROMOTERS? AND PROMOTER GROUP"),
        ("our_management", r"OUR MANAGEMENT"),
        ("terms_of_the_offer", r"TERMS OF THE (OFFER|ISSUE)"),
        ("offer_structure", r"(OFFER|ISSUE) STRUCTURE"),
        ("offer_procedure", r"(OFFER|ISSUE) PROCEDURE"),
        ("management_s_discussion_and_analysis", r"MANAGEMENT S DISCUSSION AND ANALYSIS.*"),
    ]
]

_TOC_HEAD = re.compile(r"^(TABLE OF CONTENTS|CONTENTS)$", re.MULTILINE | re.IGNORECASE)
_TOC_LINE = re.compile(r"^(?P<title>.*?)\s*\.{4,}\s*(?P<page>\d{1,4})\s*$")
_PART = re.compile(r"^SECTION\s+[IVXLC]+\s*[:\-–]?\s*", re.IGNORECASE)
# Part headers that are also a section in their own right ("SECTION II: RISK FACTORS").
_PART_SECTIONS = {"risk_factors"}
HEADING_LINES = 8  # a heading must be within the first lines of the page text
NEAR = 3  # pages either side of the TOC page to look for the heading


def normalize_title(text: str) -> str:
    text = text.upper().replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def canonical_id(title: str) -> str:
    norm = normalize_title(title)
    for sid, pattern in _CANONICAL:
        if pattern.match(norm):
            return sid
    return re.sub(r"[^a-z0-9]+", "_", norm.lower()).strip("_")


# ------------------------------------------------------------------------- TOC
@dataclass
class TocEntry:
    title: str
    printed_page: int


def find_toc_pages(doc: ParsedDoc, within: int = 20) -> list[int]:
    return [p.number for p in doc.pages[:within] if _TOC_HEAD.search(p.text)]


def parse_toc_lines(lines: list[str]) -> list[TocEntry]:
    """Title + printed page per TOC line; wrapped titles are joined, part headers skipped."""
    entries: list[TocEntry] = []
    pending: list[str] = []
    for raw in lines:
        line = " ".join(raw.split())
        if not line or _TOC_HEAD.match(line):
            continue
        match = _TOC_LINE.match(line)
        if not match:
            if "...." not in line:
                pending.append(line)
            continue
        title = " ".join([*pending, match["title"]]).strip(" .")
        pending = []
        part = _PART.match(title)
        if part:
            title = title[part.end() :].strip()
            if canonical_id(title) not in _PART_SECTIONS:
                continue
        if title:
            entries.append(TocEntry(title=title, printed_page=int(match["page"])))
    return entries


def printed_to_pdf(doc: ParsedDoc, printed: int) -> int:
    """PDF page carrying printed number ``printed``; else apply the median offset."""
    offsets = []
    for page in doc.pages:
        if page.printed_page and page.printed_page.isdigit():
            if int(page.printed_page) == printed:
                return page.number
            offsets.append(page.number - int(page.printed_page))
    shift = int(statistics.median(offsets)) if offsets else 0
    return min(max(printed + shift, 1), doc.n_pages)


# ------------------------------------------------------------------------- headings
def _top_lines(page: Page) -> list[str]:
    """First lines of the page, normalised, with any "SECTION II -" part prefix removed."""
    lines = []
    for raw in page.text.splitlines()[:HEADING_LINES]:
        part = _PART.match(raw.strip())
        text = raw.strip()[part.end() :] if part else raw
        if text.strip():
            lines.append(normalize_title(text))
    return lines


def _heading_matches(page: Page, title: str) -> bool:
    want = normalize_title(title)
    for line in _top_lines(page):
        if line == want:
            return True
        if len(line) >= 15 and len(want) >= 15 and (want.startswith(line) or line.startswith(want)):
            return True
    return False


def _bold_heading(page: Page, title: str) -> bool:
    """Font cue: the title's words are bold or clearly larger than the page's body text."""
    first = normalize_title(title).split()[:3]
    if not page.words or not first:
        return False
    body = statistics.median(w.font_size for w in page.words)
    hits = [
        w
        for w in page.words
        if normalize_title(w.text) in first and (w.bold or w.font_size >= 1.2 * body)
    ]
    return len(hits) >= min(2, len(first))


def _scan_for(doc: ParsedDoc, title: str, pages: range) -> int | None:
    for n in pages:
        if 1 <= n <= doc.n_pages and _heading_matches(doc.pages[n - 1], title):
            return n
    return None


# ------------------------------------------------------------------------- vote
@dataclass
class _Found:
    id: str
    title: str
    start: int
    method: Method
    confidence: float


def _locate(doc: ParsedDoc, title: str, toc_page: int | None, after: int) -> _Found | None:
    sid = canonical_id(title)
    if toc_page is not None:
        page = doc.pages[toc_page - 1]
        if _heading_matches(page, title):
            bold = _bold_heading(page, title)
            return _Found(sid, title, toc_page, "toc", 1.0 if bold else 0.9)
        near = _scan_for(doc, title, range(max(after + 1, toc_page - NEAR), toc_page + NEAR + 1))
        if near is not None:
            bold = _bold_heading(doc.pages[near - 1], title)
            return _Found(sid, title, near, "font" if bold else "regex", 0.6 if bold else 0.5)
        return _Found(sid, title, toc_page, "toc", 0.7)
    found = _scan_for(doc, title, range(after + 1, doc.n_pages + 1))
    if found is None:
        return None
    bold = _bold_heading(doc.pages[found - 1], title)
    return _Found(sid, title, found, "font" if bold else "regex", 0.6 if bold else 0.5)


_FALLBACK_TITLES = {
    "the_offer": "THE OFFER",
    "capital_structure": "CAPITAL STRUCTURE",
    "objects_of_the_offer": "OBJECTS OF THE OFFER",
    "general_information": "GENERAL INFORMATION",
    "our_promoters": "OUR PROMOTERS AND PROMOTER GROUP",
}


def find_sections(doc: ParsedDoc) -> list[Section]:
    """All sections found, sorted by start page, each ending where the next begins."""
    toc_pages = find_toc_pages(doc)
    after = max(toc_pages) if toc_pages else 2
    lines = [ln for n in toc_pages for ln in doc.pages[n - 1].text.splitlines()]
    found: dict[str, _Found] = {}
    for entry in parse_toc_lines(lines):
        hit = _locate(doc, entry.title, printed_to_pdf(doc, entry.printed_page), after)
        if hit and hit.id not in found:
            found[hit.id] = hit
    for sid, title in _FALLBACK_TITLES.items():
        if sid not in found and (hit := _locate(doc, title, None, after)):
            found[sid] = hit

    cover_end = min(toc_pages) - 1 if toc_pages else 2
    ordered = sorted(found.values(), key=lambda f: f.start)
    sections = [
        Section(id="cover", title="Cover", start_page=1, end_page=max(1, cover_end),
                method="regex", confidence=1.0)
    ]  # fmt: skip
    for i, f in enumerate(ordered):
        later = [g.start for g in ordered[i + 1 :] if g.start > f.start]
        end = (min(later) - 1) if later else doc.n_pages
        sections.append(
            Section(id=f.id, title=f.title, start_page=f.start, end_page=end,
                    method=f.method, confidence=f.confidence)
        )  # fmt: skip
    return sections
