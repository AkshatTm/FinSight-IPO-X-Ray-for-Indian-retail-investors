"""B1.2: report.json is assembled from whichever stage outputs exist."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from finsight.core.schemas import DocRecord
from finsight.reports import assemble, etag, write_report
from finsight.storage import LocalStorage, doc_key, get_json, put_json

DOC = DocRecord(
    doc_id="doc_a",
    sha256="a" * 64,
    doc_type="rhp",
    pages=10,
    created_at=datetime(2026, 10, 3, tzinfo=UTC),
    status="partial",
)


def test_missing_parts_are_null(tmp_path: Path) -> None:
    report = assemble(LocalStorage(tmp_path), DOC)
    assert report.facts_summary is None
    assert report.risk_level is None
    assert report.top_risks is None
    assert report.redflags_summary is None


def test_parts_are_read_and_top_five_risks_ranked(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    risks = [{"rid": f"r{i}", "importance": i / 10} for i in range(8)]
    put_json(storage, doc_key("doc_a", "risks.json"), {"risks": risks})
    put_json(
        storage,
        doc_key("doc_a", "redflags.json"),
        {"flags": [{"id": "RF01", "status": "ok", "sentence": "x"}]},
    )
    put_json(storage, doc_key("doc_a", "risklevel.json"), {"level": "medium"})
    put_json(
        storage, doc_key("doc_a", "summary.json"), {"offer_line_params": {"price_band": "1-2"}}
    )
    report = write_report(storage, DOC, companion_doc_id="doc_b")
    assert [r["rid"] for r in report.top_risks or []] == ["r7", "r6", "r5", "r4", "r3"]
    assert report.redflags_summary == [{"id": "RF01", "status": "ok"}]
    assert report.risk_level == {"level": "medium"}
    assert report.offer_line_params == {"price_band": "1-2"}
    assert get_json(storage, "docs/doc_a/report.json")["companion_doc_id"] == "doc_b"
    assert etag(report) == etag(assemble(storage, DOC, "doc_b"))
