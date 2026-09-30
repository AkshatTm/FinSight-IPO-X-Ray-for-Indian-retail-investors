"""Table extractor bake-off (ADR-017): PyMuPDF vs pdfplumber vs Docling on 3 RHP pages.

    uv run --group tables python scripts/table_bakeoff.py

Writes eval_results/table_bakeoff.json. For each extractor and page: tables found, body rows,
cells holding an amount or [●] ("value cells", the ones extraction needs) and seconds per page
(Docling timed after a warm-up page, so model loading is not counted).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path

import pdfplumber
import pymupdf

from finsight.core.config import get_settings
from finsight.ingest.registry import get_demo_ipo

# (ipo, PDF page, what the page shows)
PAGES = [
    ("urban-company-2025", 163, "objects: header ruled, body unruled"),
    ("meesho-2025", 210, "objects: fully ruled"),
    ("tata-capital-2025", 145, "capital structure: long ruled table"),
]
_VALUE = re.compile(r"^\(?[\d,]+(\.\d+)?\)?$|\[[●•]\]")

Grid = list[list[str]]


def _clean(rows: list[list[str | None]]) -> Grid:
    return [[" ".join((c or "").split()) for c in r] for r in rows]


def by_pymupdf(pdf: Path, page: int) -> list[Grid]:
    with pymupdf.open(pdf) as doc:
        return [_clean(t.extract()) for t in doc[page - 1].find_tables().tables]


def by_pdfplumber(pdf: Path, page: int) -> list[Grid]:
    with pdfplumber.open(pdf) as doc:
        return [_clean(t) for t in doc.pages[page - 1].extract_tables()]


def _docling() -> Callable[[Path, int], list[Grid]]:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    pdf_opts = PdfFormatOption(pipeline_options=opts)
    conv = DocumentConverter(format_options={InputFormat.PDF: pdf_opts})

    def run(pdf: Path, page: int) -> list[Grid]:
        doc = conv.convert(str(pdf), page_range=(page, page)).document
        return [t.export_to_dataframe(doc=doc).astype(str).values.tolist() for t in doc.tables]

    return run


def score(grids: list[Grid]) -> dict[str, int]:
    cells = [c for g in grids for r in g for c in r]
    return {
        "tables": len(grids),
        "rows": sum(len(g) for g in grids),
        "value_cells": sum(1 for c in cells if _VALUE.search(c.replace(" ", ""))),
    }


def main() -> None:
    docling = _docling()
    extractors = {"pymupdf": by_pymupdf, "pdfplumber": by_pdfplumber, "docling": docling}
    first = get_demo_ipo(PAGES[0][0]).rhp.file
    docling(first, PAGES[0][1])  # warm-up: load the layout and table models once
    results = []
    for ipo_id, page, what in PAGES:
        pdf = get_demo_ipo(ipo_id).rhp.file
        row: dict[str, object] = {"ipo_id": ipo_id, "pdf_page": page, "what": what}
        for name, fn in extractors.items():
            t0 = time.perf_counter()
            grids = fn(pdf, page)
            row[name] = score(grids) | {"seconds": round(time.perf_counter() - t0, 2)}
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))
    out = get_settings().paths.eval_dir / "table_bakeoff.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(results, indent=1, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
