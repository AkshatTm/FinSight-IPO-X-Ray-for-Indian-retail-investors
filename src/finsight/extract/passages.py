"""Section-restricted passages for the QA extractors.

A question-answering model reads a few hundred words at a time, so each page in the field's
sections (``configs/fields.yaml``) is cut into passages of at most ``max_chars`` at sentence ends.
Ids follow ADR-033, so a passage can be traced to its page. These are lightweight search units;
the retrieval index (P3.1) builds full ``Passage`` objects with word boxes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsight.core.ids import passage_id
from finsight.core.schemas import DocType, FieldSpec, ParsedDoc, Section
from finsight.extract.rules import pages_to_search

MAX_CHARS = 1500  # about 300 words, well inside the model's 384-token window with its stride
MAX_PASSAGES = 150  # per field and document; earlier pages come first
_SENTENCE_END = re.compile(r"(?<=[.;:])\s+")


@dataclass(frozen=True)
class QAPassage:
    id: str
    doc_type: DocType
    page: int  # PDF page, 1-indexed
    printed_page: str | None
    text: str


def _chunks(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(text):
        while len(sentence) > max_chars:  # one endless sentence: cut it at a word boundary
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            head, sentence = sentence[:cut], sentence[cut:].lstrip()
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def build_passages(
    doc: ParsedDoc,
    sections: list[Section],
    field: FieldSpec,
    max_chars: int = MAX_CHARS,
    max_passages: int = MAX_PASSAGES,
) -> list[QAPassage]:
    out: list[QAPassage] = []
    for number in pages_to_search(doc, sections, field):
        page = doc.pages[number - 1]
        text = " ".join(page.text.split())
        for k, chunk in enumerate(_chunks(text, max_chars)):
            out.append(
                QAPassage(
                    id=passage_id(doc.ipo_id, doc.doc_type, number, k),
                    doc_type=doc.doc_type,
                    page=number,
                    printed_page=page.printed_page,
                    text=chunk,
                )
            )
            if len(out) >= max_passages:
                return out
    return out
