"""Cut a parsed document into search passages; a table is always one passage.

Prose is cut at sentence ends into passages of about ``TARGET_CHARS`` (roughly 350 tokens), never
across a page. Words that sit inside a table's cells are left out of the prose and the table is
emitted whole, one row per line, so a number never loses its row or column header. Every passage
carries ``char_to_bbox`` (character span -> page and box) because "Show in document" needs it.
"""

from __future__ import annotations

import re

from finsight.core.ids import passage_id
from finsight.core.schemas import BBox, Page, ParsedDoc, Passage, Section, Table, Word
from finsight.retrieve.redact import address_column_words, redact_prose, redact_table

TARGET_CHARS = 1500  # about 350 tokens
HARD_MAX_CHARS = 2100  # an endless sentence is cut at a word boundary past this
MIN_CHARS = 15  # page numbers and stray headings are not worth a passage
UNSECTIONED = "unsectioned"
_SENTENCE_END = re.compile(r"[.;:!?]$")

Spans = list[tuple[int, int, int, BBox]]


def section_for_page(page: int, sections: list[Section]) -> str:
    """The most specific (latest-starting) section covering ``page``."""
    covering = [s for s in sections if s.start_page <= page <= s.end_page]
    if not covering:
        return UNSECTIONED
    return max(covering, key=lambda s: (s.start_page, -s.end_page)).id


def _inside(word: Word, boxes: list[BBox]) -> bool:
    cx = (word.bbox[0] + word.bbox[2]) / 2
    cy = (word.bbox[1] + word.bbox[3]) / 2
    return any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes)


def _word_groups(words: list[Word]) -> list[list[Word]]:
    groups: list[list[Word]] = []
    current: list[Word] = []
    size = 0
    for word in words:
        current.append(word)
        size += len(word.text) + 1
        if (size >= TARGET_CHARS and _SENTENCE_END.search(word.text)) or size >= HARD_MAX_CHARS:
            groups.append(current)
            current, size = [], 0
    if current:
        groups.append(current)
    return groups


def _group_text(group: list[Word], page: int) -> tuple[str, Spans]:
    parts: list[str] = []
    spans: Spans = []
    pos = 0
    for word in group:
        spans.append((pos, pos + len(word.text), page, word.bbox))
        parts.append(word.text)
        pos += len(word.text) + 1
    return " ".join(parts), spans


def _text_groups(text: str) -> list[str]:
    """Fallback for pages without word boxes (scanned pages): sentence-end cuts, no spans."""
    out: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.;:!?])\s+", " ".join(text.split())):
        if current and len(current) + 1 + len(sentence) > TARGET_CHARS:
            out.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        out.append(current)
    return out


def _prose(page: Page, boxes: list[BBox]) -> list[tuple[str, Spans]]:
    if not page.words:
        return [redact_prose(t, []) for t in _text_groups(page.text)]
    private = address_column_words(page.words)
    words = [
        w
        for i, w in enumerate(page.words)
        if w.text.strip() and i not in private and not _inside(w, boxes)
    ]
    return [redact_prose(*_group_text(g, page.number)) for g in _word_groups(words)]


def table_text(table: Table) -> tuple[str, Spans]:
    """The whole table as text, one row per line, cells joined by `` | ``, with its spans."""
    cells = sorted(table.cells, key=lambda c: (c.page, c.row, c.col))
    text = f"[Table, {table.header_scale}]\n" if table.header_scale else ""
    spans: Spans = []
    previous: tuple[int, int] | None = None
    for cell in cells:
        key = (cell.page, cell.row)
        if previous is not None:
            text += " | " if key == previous else "\n"
        previous = key
        flat = " ".join(cell.text.split())
        if flat:
            spans.append((len(text), len(text) + len(flat), cell.page, cell.bbox))
        text += flat
    return text, spans


def build_chunks(doc: ParsedDoc, sections: list[Section], tables: list[Table]) -> list[Passage]:
    """Passages for one document, in page order; ids follow ADR-033."""
    boxes_by_page: dict[int, list[BBox]] = {}
    for table in tables:
        for cell in table.cells:
            boxes_by_page.setdefault(cell.page, []).append(cell.bbox)
    tables_by_start: dict[int, list[Table]] = {}
    for table in tables:
        if table.cells:
            tables_by_start.setdefault(
                min(table.pages or [c.page for c in table.cells]), []
            ).append(table)

    out: list[Passage] = []
    for page in doc.pages:
        k = 0
        section = section_for_page(page.number, sections)
        for text, spans in _prose(page, boxes_by_page.get(page.number, [])):
            if len(text) < MIN_CHARS:
                continue
            out.append(
                Passage(
                    id=passage_id(doc.ipo_id, doc.doc_type, page.number, k),
                    ipo_id=doc.ipo_id,
                    doc_type=doc.doc_type,
                    section_id=section,
                    page_start=page.number,
                    page_end=page.number,
                    text=text,
                    char_to_bbox=spans,
                )
            )
            k += 1
        for table in tables_by_start.get(page.number, []):
            text, spans = table_text(redact_table(table))
            pages = [c.page for c in table.cells]
            out.append(
                Passage(
                    id=passage_id(doc.ipo_id, doc.doc_type, page.number, k),
                    ipo_id=doc.ipo_id,
                    doc_type=doc.doc_type,
                    section_id=table.section_id or section,
                    page_start=min(pages),
                    page_end=max(pages),
                    text=text,
                    char_to_bbox=spans,
                )
            )
            k += 1
    return out
