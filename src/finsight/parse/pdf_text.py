"""PDF -> pages of words with boxes, fonts and clean text (02_ARCHITECTURE.md section 3).

Words are built from PyMuPDF's per-character data so every word keeps an exact box
(for highlighting) plus its font size and bold flag (for section detection).
``Page.text`` drops repeated headers/footers and the printed page number; the words
themselves are all kept, so any region can still be highlighted.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from finsight.core.schemas import BBox, DocType, Page, ParsedDoc, Word
from finsight.parse.clean import (
    EDGE_BAND,
    boilerplate_keys,
    is_scanned_page,
    line_key,
    read_printed_page,
)

_BOLD_FLAG = 16  # PyMuPDF span flag bit for bold


@dataclass
class _Line:
    text: str
    y0: float
    y1: float
    words: list[Word] = field(default_factory=list)


@dataclass
class _RawPage:
    number: int
    width: float
    height: float
    lines: list[_Line]
    n_images: int

    def edge_lines(self) -> list[str]:
        top, bottom = self.height * EDGE_BAND, self.height * (1 - EDGE_BAND)
        return [ln.text for ln in self.lines if ln.y1 <= top or ln.y0 >= bottom]

    def footer_lines(self) -> list[str]:
        bottom = self.height * (1 - EDGE_BAND)
        return [ln.text for ln in reversed(self.lines) if ln.y0 >= bottom]


def _union(boxes: list[BBox]) -> BBox:
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _is_bold(span: dict[str, object]) -> bool:
    flags = span.get("flags", 0)
    font = str(span.get("font", ""))
    return bool(isinstance(flags, int) and flags & _BOLD_FLAG) or "bold" in font.lower()


def _read_page(page: pymupdf.Page) -> _RawPage:
    raw = page.get_text("rawdict", sort=True)
    lines: list[_Line] = []
    for block in raw["blocks"]:
        for line in block.get("lines", []):
            current = _Line(text="", y0=line["bbox"][1], y1=line["bbox"][3])
            texts: list[str] = []
            for span in line["spans"]:
                size, bold = float(span["size"]), _is_bold(span)
                chars: list[tuple[str, BBox]] = [(c["c"], tuple(c["bbox"])) for c in span["chars"]]
                texts.append("".join(c for c, _ in chars))
                word_chars: list[tuple[str, BBox]] = []
                for char, box in [*chars, (" ", (0.0, 0.0, 0.0, 0.0))]:
                    if char.isspace():
                        if word_chars:
                            current.words.append(
                                Word(
                                    text="".join(c for c, _ in word_chars),
                                    bbox=_union([b for _, b in word_chars]),
                                    font_size=round(size, 2),
                                    bold=bold,
                                )
                            )
                            word_chars = []
                    else:
                        word_chars.append((char, box))
            current.text = " ".join("".join(texts).split())
            if current.text:
                lines.append(current)
    return _RawPage(
        number=page.number + 1,
        width=page.rect.width,
        height=page.rect.height,
        lines=lines,
        n_images=len(page.get_images(full=False)),
    )


def parse_pdf(path: Path, ipo_id: str, doc_type: DocType) -> ParsedDoc:
    """Parse one PDF into a :class:`ParsedDoc` (pages are PDF pages, 1-indexed)."""
    data = path.read_bytes()
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        raw_pages = [_read_page(page) for page in pdf]

    readable = [p for p in raw_pages if p.lines]
    repeated = boilerplate_keys(p.edge_lines() for p in readable) if readable else set()

    pages: list[Page] = []
    for raw in raw_pages:
        n_chars = sum(len(ln.text) for ln in raw.lines)
        scanned = is_scanned_page(n_chars, raw.n_images)
        printed = read_printed_page(raw.footer_lines())
        bottom = raw.height * (1 - 0.12)
        kept = [
            ln.text
            for ln in raw.lines
            if line_key(ln.text) not in repeated
            and not (printed and ln.y0 >= bottom and read_printed_page([ln.text]) == printed)
        ]
        pages.append(
            Page(
                number=raw.number,
                printed_page=printed,
                width=raw.width,
                height=raw.height,
                words=[] if scanned else [w for ln in raw.lines for w in ln.words],
                text="" if scanned else "\n".join(kept),
                is_scanned=scanned,
            )
        )
    return ParsedDoc(
        ipo_id=ipo_id,
        doc_type=doc_type,
        source_path=path.as_posix(),
        n_pages=len(pages),
        pages=pages,
        sha256=hashlib.sha256(data).hexdigest(),
    )
