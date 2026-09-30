from pathlib import Path

from pydantic import TypeAdapter

from finsight.core.schemas import Section
from finsight.parse import pymupdf_backend
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.parse_stage import run_parse
from finsight.pipeline.tables_stage import (
    load_tables,
    run_tables,
    tables_summary,
    update_summary,
)

BACKEND = ("pymupdf", pymupdf_backend)


def _prepare(pdf: Path, processed: Path) -> None:
    """Parse the one-page fixture and give it an Objects section on page 1."""
    run_parse(pdf, processed, "acme-2025", "rhp", images=False)
    objects = Section(id="objects_of_the_offer", title="OBJECTS OF THE OFFER", start_page=1,
                      end_page=1, method="toc", confidence=1.0)  # fmt: skip
    out = doc_outputs(processed, "acme-2025", "rhp").sections
    out.write_bytes(TypeAdapter(list[Section]).dump_json([objects]))


def test_run_tables_writes_tables_and_reports_objects(table_pdf: Path, tmp_path: Path) -> None:
    _prepare(table_pdf, tmp_path)
    report = run_tables(tmp_path, table_pdf, "acme-2025", "rhp", backend=BACKEND)
    assert (report.objects, report.pure_ofs, report.backend) == ("ok", False, "pymupdf")
    assert report.objects_scale == "₹ in million"
    assert report.objects_rows[-1] == "Net Proceeds"
    assert doc_outputs(tmp_path, "acme-2025", "rhp").tables.name == "tables.json"
    assert len(load_tables(tmp_path, "acme-2025", "rhp")) == report.n_tables == 1


def test_summary_counts_fresh_issue_documents_only(table_pdf: Path, tmp_path: Path) -> None:
    _prepare(table_pdf, tmp_path)
    ok = run_tables(tmp_path, table_pdf, "acme-2025", "rhp", backend=BACKEND)
    ofs = ok.__class__(**{**ok.__dict__, "ipo_id": "ofs-2025", "pure_ofs": True,
                          "objects": "not_in_document"})  # fmt: skip
    summary = tables_summary([ok, ofs])["summary"]
    assert isinstance(summary, dict)
    assert summary["rhp"] == {
        "fresh_issue_with_objects_rows": "1/1",
        "pure_ofs_not_in_document": ["ofs-2025"],
        "missing": [],
    }


def test_update_summary_merges_one_ipo_at_a_time(table_pdf: Path, tmp_path: Path) -> None:
    _prepare(table_pdf, tmp_path)
    ok = run_tables(tmp_path, table_pdf, "acme-2025", "rhp", backend=BACKEND)
    ofs = ok.__class__(**{**ok.__dict__, "ipo_id": "ofs-2025", "pure_ofs": True,
                          "objects": "not_in_document"})  # fmt: skip
    out = tmp_path / "eval" / "tables.json"
    update_summary(out, [ok])
    summary = update_summary(out, [ofs])
    assert set(summary["documents"]) == {"acme-2025:rhp", "ofs-2025:rhp"}  # type: ignore[arg-type]
