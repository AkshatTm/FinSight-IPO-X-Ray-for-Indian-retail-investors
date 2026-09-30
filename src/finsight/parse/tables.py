"""Tables in the key sections, with the unit header ("₹ in million") that scales their cells.

Two backends (ADR-017):
- **Docling** (primary, `uv sync --group tables`): a layout model plus a table-structure model.
  It recovers tables whose body rows have no ruling lines, which is how many RHPs print the
  Objects-of-the-Offer table.
- **PyMuPDF** ``find_tables`` (fallback, always installed): finds tables from their ruling
  lines. Fast and exact on fully ruled tables, but sees only the header of unruled ones.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable, Iterable
from functools import cache
from pathlib import Path
from typing import Any

import pymupdf

from finsight.core.schemas import ParsedDoc, Section, Table, TableCell

# Sections whose tables the X-Ray needs; very long sections are capped (pages from the start).
TABLE_SECTIONS = ("the_offer", "capital_structure", "objects_of_the_offer")
MAX_SECTION_PAGES = 40
ABOVE_PT = 72  # look this far above a table (one inch) for its "(₹ in million)" line

_CUR = re.compile(r"(₹|\bRs\b\.?|\bINR\b|\bRupees\b|US\$|\bUSD\b)", re.IGNORECASE)
_SCALE = re.compile(
    r"(\blakhs?\b|\blacs?\b|\bcrores?\b|\bcr\b|\bmillions?\b|\bmn\b|\bbillions?\b|\bbn\b"
    r"|\bthousands?\b|['’‘]000\b)",
    re.IGNORECASE,
)
_SCALE_NAMES = {
    "lakh": "lakh", "lac": "lakh", "crore": "crore", "cr": "crore",
    "million": "million", "mn": "million", "billion": "billion", "bn": "billion",
    "thousand": "thousand", "000": "thousand",
}  # fmt: skip
_PAREN = re.compile(r"\(([^()]*)\)")
_BARE = re.compile(r"^\s*(in\s+)?(₹|Rs\.?|INR)\s+(in\s+)?\w+\s*$", re.IGNORECASE)


def _scale_name(token: str) -> str:
    word = token.lower().lstrip("'’‘").rstrip("s")
    return _SCALE_NAMES[word]


def _unit(text: str, *, need_in: bool) -> str | None:
    """Canonical unit ("₹ in crore") for a phrase like "Amount in ₹ crores", else None."""
    if re.search(r"\d", text.replace("000", "")):
        return None  # "(₹ 800 crore)" is an amount, not a unit header
    cur, scale = _CUR.search(text), _SCALE.search(text)
    has_in = re.search(r"\bin\b", text, re.IGNORECASE) is not None
    if not cur and not (scale and has_in):
        return None
    if need_in and not (cur and scale):
        return None
    sym = None if not cur else ("$" if "$" in cur[0] or "usd" in cur[0].lower() else "₹")
    if scale is None:
        return sym
    return f"{sym} in {_scale_name(scale[0])}" if sym else f"in {_scale_name(scale[0])}"


def detect_header_scale(text: str) -> str | None:
    """First unit header in ``text`` (table header cells or the lines just above a table)."""
    for line in text.splitlines():
        for group in _PAREN.findall(line):
            if unit := _unit(group, need_in=False):
                return unit
        if _BARE.match(line) and (unit := _unit(line, need_in=True)):
            return unit
    return None


# ------------------------------------------------------------------------- backends
Backend = Callable[[Path, list[int]], list[tuple[int, list[TableCell]]]]
"""(pdf, 1-based pages) -> [(page, cells)] with cell boxes in PDF points, top-left origin."""


def _text(value: str | None) -> str:
    return " ".join((value or "").split())


def pymupdf_backend(pdf: Path, pages: list[int]) -> list[tuple[int, list[TableCell]]]:
    found = []
    with pymupdf.open(pdf) as doc:
        for n in pages:
            for table in doc[n - 1].find_tables().tables:
                cells = [
                    TableCell(row=r, col=c, text=_text(text), bbox=tuple(box), page=n)
                    for r, (row, texts) in enumerate(zip(table.rows, table.extract(), strict=False))
                    for c, (box, text) in enumerate(zip(row.cells, texts, strict=False))
                    if box is not None and text is not None
                ]
                if cells:
                    found.append((n, cells))
    return found


@cache
def _docling_converter() -> Any:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


def _runs(pages: list[int], limit: int = 20) -> Iterable[tuple[int, int]]:
    """Contiguous page runs of at most ``limit`` pages, so Docling works in small batches."""
    start = prev = pages[0]
    for n in pages[1:]:
        if n != prev + 1 or n - start >= limit:
            yield start, prev
            start = n
        prev = n
    yield start, prev


def docling_backend(pdf: Path, pages: list[int]) -> list[tuple[int, list[TableCell]]]:
    found = []
    for first, last in _runs(sorted(pages)) if pages else []:
        doc = _docling_converter().convert(str(pdf), page_range=(first, last)).document
        for table in doc.tables:
            if not table.prov:
                continue
            n = table.prov[0].page_no
            height = doc.pages[n].size.height
            cells = []
            for cell in table.data.table_cells:
                if cell.bbox is None or not _text(cell.text):
                    continue
                b = cell.bbox.to_top_left_origin(page_height=height)
                cells.append(
                    TableCell(row=cell.start_row_offset_idx, col=cell.start_col_offset_idx,
                              text=_text(cell.text), bbox=(b.l, b.t, b.r, b.b), page=n)
                )  # fmt: skip
            if cells:
                found.append((n, cells))
    return found


def default_backend() -> tuple[str, Backend]:
    if importlib.util.find_spec("docling") is not None:
        return "docling", docling_backend
    return "pymupdf", pymupdf_backend


# ------------------------------------------------------------------------- tables
def _words_above(doc: ParsedDoc, page: int, top: float) -> str:
    words = doc.pages[page - 1].words
    return " ".join(w.text for w in words if top - ABOVE_PT <= w.bbox[3] <= top + 1)


def _header_text(cells: list[TableCell]) -> str:
    return "\n".join(c.text for c in sorted(cells, key=lambda c: (c.row, c.col)) if c.row <= 1)


def extract_tables(
    pdf: Path,
    doc: ParsedDoc,
    sections: list[Section],
    *,
    backend: Backend | None = None,
    section_ids: tuple[str, ...] = TABLE_SECTIONS,
) -> list[Table]:
    """Tables on the pages of the chosen sections, each with its unit header if one is stated."""
    run = backend or default_backend()[1]
    tables: list[Table] = []
    for section in sections:
        if section.id not in section_ids:
            continue
        last = min(section.end_page, section.start_page + MAX_SECTION_PAGES - 1)
        per_page: dict[int, int] = {}
        for page, cells in run(pdf, list(range(section.start_page, last + 1))):
            k = per_page.get(page, 0)
            per_page[page] = k + 1
            top = min(c.bbox[1] for c in cells)
            scale = detect_header_scale(_header_text(cells)) or detect_header_scale(
                _words_above(doc, page, top)
            )
            tables.append(
                Table(id=f"{doc.doc_type}:{section.id}:p{page}:t{k}", section_id=section.id,
                      pages=[page], header_scale=scale, cells=cells)
            )  # fmt: skip
    return tables


def table_rows(table: Table) -> list[list[str]]:
    """The table as a grid of strings (merged or missing cells are empty)."""
    if not table.cells:
        return []
    n_rows = max(c.row for c in table.cells) + 1
    n_cols = max(c.col for c in table.cells) + 1
    grid = [[""] * n_cols for _ in range(n_rows)]
    for c in table.cells:
        grid[c.row][c.col] = c.text
    return [[cell for cell in row if cell] for row in grid if any(row)]


_PROCEEDS = re.compile(r"\b(net|gross) proceeds\b", re.IGNORECASE)
_PURE_OFS = re.compile(
    r"will not receive any (of the )?proceeds (from|of) the Offer(?!\s+for\s+Sale)", re.IGNORECASE
)


def objects_table(tables: list[Table]) -> Table | None:
    """The Objects-of-the-Offer table that lists gross/net proceeds, if any."""
    for table in tables:
        if table.section_id == "objects_of_the_offer" and any(
            _PROCEEDS.search(c.text) for c in table.cells
        ):
            return table
    return None


def is_pure_ofs(objects_text: str) -> bool:
    """The company gets no money: the whole offer is an Offer for Sale (no Fresh Issue)."""
    return _PURE_OFS.search(" ".join(objects_text.split())) is not None
