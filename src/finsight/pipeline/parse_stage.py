"""The parse stage: PDF -> parsed JSON + page images, with timing."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

from finsight.core.schemas import DocType, ParsedDoc
from finsight.parse import parse_pdf, render_pages
from finsight.pipeline.layout import doc_outputs


@dataclass
class ParseReport:
    ipo_id: str
    doc: DocType
    pages: int
    scanned_pages: int
    pages_with_printed_number: int
    parse_s: float
    images_s: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_parse(
    pdf: Path,
    processed_dir: Path,
    ipo_id: str,
    doc: DocType,
    images: bool = True,
    dpi: int = 110,
) -> ParseReport:
    out = doc_outputs(processed_dir, ipo_id, doc)
    out.parsed.parent.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    parsed = parse_pdf(pdf, ipo_id=ipo_id, doc_type=doc)
    out.parsed.write_text(parsed.model_dump_json(), encoding="utf-8")
    parse_s = time.perf_counter() - start

    start = time.perf_counter()
    if images:
        render_pages(pdf, out.pages_dir, dpi=dpi)
    images_s = time.perf_counter() - start

    return ParseReport(
        ipo_id=ipo_id,
        doc=doc,
        pages=parsed.n_pages,
        scanned_pages=sum(p.is_scanned for p in parsed.pages),
        pages_with_printed_number=sum(p.printed_page is not None for p in parsed.pages),
        parse_s=round(parse_s, 2),
        images_s=round(images_s, 2),
    )


def load_parsed(processed_dir: Path, ipo_id: str, doc: DocType) -> ParsedDoc:
    path = doc_outputs(processed_dir, ipo_id, doc).parsed
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run `pipeline build --ipo {ipo_id}` first")
    return ParsedDoc.model_validate_json(path.read_text(encoding="utf-8"))
