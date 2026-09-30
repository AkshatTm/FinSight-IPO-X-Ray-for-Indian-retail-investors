"""The tables stage: parsed + sections -> tables JSON, plus the Objects-of-the-Offer report."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter

from finsight.core.schemas import DocType, Table
from finsight.parse import (
    Backend,
    default_backend,
    extract_tables,
    is_pure_ofs,
    objects_table,
    table_rows,
)
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.parse_stage import load_parsed
from finsight.pipeline.sections_stage import load_sections

_TABLES = TypeAdapter(list[Table])
OBJECTS_TEXT_PAGES = 3  # the pure-OFS sentence sits on the first pages of the section

ObjectsStatus = Literal["ok", "not_in_document", "missing"]


@dataclass
class TablesReport:
    ipo_id: str
    doc: DocType
    backend: str
    n_tables: int
    seconds: float
    pure_ofs: bool
    objects: ObjectsStatus
    objects_scale: str | None = None
    objects_rows: list[str] = field(default_factory=list)  # first-column labels, capped


def run_tables(
    processed_dir: Path,
    pdf: Path,
    ipo_id: str,
    doc: DocType,
    backend: tuple[str, Backend] | None = None,
) -> TablesReport:
    parsed = load_parsed(processed_dir, ipo_id, doc)
    sections = load_sections(processed_dir, ipo_id, doc)
    name, run = backend or default_backend()
    t0 = time.perf_counter()
    tables = extract_tables(pdf, parsed, sections, backend=run)
    seconds = round(time.perf_counter() - t0, 1)
    doc_outputs(processed_dir, ipo_id, doc).tables.write_bytes(_TABLES.dump_json(tables, indent=1))

    objects = next((s for s in sections if s.id == "objects_of_the_offer"), None)
    text = ""
    if objects is not None:
        last = min(objects.end_page, objects.start_page + OBJECTS_TEXT_PAGES - 1)
        text = "\n".join(parsed.pages[n - 1].text for n in range(objects.start_page, last + 1))
    pure = is_pure_ofs(text)
    table = objects_table(tables)
    status: ObjectsStatus = "not_in_document" if pure else ("ok" if table else "missing")
    labels = [row[0][:60] for row in table_rows(table)[:12]] if table and not pure else []
    return TablesReport(
        ipo_id=ipo_id, doc=doc, backend=name, n_tables=len(tables), seconds=seconds,
        pure_ofs=pure, objects=status, objects_scale=table.header_scale if table else None,
        objects_rows=labels,
    )  # fmt: skip


def load_tables(processed_dir: Path, ipo_id: str, doc: DocType) -> list[Table]:
    path = doc_outputs(processed_dir, ipo_id, doc).tables
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run `pipeline build --stage tables` first")
    return _TABLES.validate_json(path.read_bytes())


def tables_summary(reports: list[TablesReport]) -> dict[str, object]:
    """Objects-of-the-Offer rows per document type: found where a fresh issue exists."""
    summary: dict[str, object] = {}
    for doc in ("rhp", "prospectus"):
        mine = [r for r in reports if r.doc == doc]
        fresh = [r for r in mine if not r.pure_ofs]
        found = sum(r.objects == "ok" for r in fresh)
        summary[doc] = {
            "fresh_issue_with_objects_rows": f"{found}/{len(fresh)}",
            "pure_ofs_not_in_document": sorted(r.ipo_id for r in mine if r.pure_ofs),
            "missing": sorted(r.ipo_id for r in mine if r.objects == "missing"),
        }
    return {
        "summary": summary,
        "documents": {f"{r.ipo_id}:{r.doc}": asdict(r) for r in sorted(reports, key=_key)},
    }


def _key(r: TablesReport) -> tuple[str, str]:
    return r.ipo_id, r.doc


def write_summary(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def update_summary(path: Path, reports: list[TablesReport]) -> dict[str, object]:
    """Merge ``reports`` into the summary at ``path`` (one IPO at a time survives a crash)."""
    known: dict[str, TablesReport] = {}
    if path.exists():
        documents = json.loads(path.read_text(encoding="utf-8"))["documents"]
        known = {k: TablesReport(**v) for k, v in documents.items()}
    known |= {f"{r.ipo_id}:{r.doc}": r for r in reports}
    summary = tables_summary(list(known.values()))
    write_summary(path, summary)
    return summary
