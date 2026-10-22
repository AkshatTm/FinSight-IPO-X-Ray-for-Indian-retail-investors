"""CC-04: an existing laptop database gets the cache v2 columns, and the purge script picks the
right documents."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa

from finsight.core.config import load_settings
from finsight.core.schemas import DocRecord
from finsight.db import Database
from finsight.storage import LocalStorage

OLD_DOCS = """CREATE TABLE docs (
    doc_id VARCHAR(40) PRIMARY KEY, sha256 VARCHAR(64) NOT NULL UNIQUE, doc_type VARCHAR(16),
    company VARCHAR(300), pages INTEGER, uploaded_by VARCHAR(64), is_showcase BOOLEAN NOT NULL,
    companion_of VARCHAR(40), created_at DATETIME NOT NULL, status VARCHAR(16) NOT NULL,
    rejection VARCHAR(32))"""


def test_create_all_adds_the_new_columns_to_an_old_database(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'old.db').as_posix()}"
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(sa.text(OLD_DOCS))
        conn.execute(
            sa.text(
                "INSERT INTO docs (doc_id, sha256, is_showcase, created_at, status) "
                "VALUES ('doc_old', :sha, 0, '2026-10-01 00:00:00', 'ready')"
            ),
            {"sha": "a" * 64},
        )
    db = Database(url)
    db.create_all()
    doc = db.get_doc("doc_old")
    assert doc is not None
    assert doc.pipeline_version is None
    assert doc.fingerprint is None
    assert doc.degraded_reasons == []
    db.update_doc("doc_old", analysis_status="degraded", degraded_reasons=["skipped_model:ollama"])
    again = db.get_doc("doc_old")
    assert again is not None
    assert again.degraded_reasons == ["skipped_model:ollama"]


def _purge_module() -> object:
    path = Path(__file__).resolve().parents[2] / "scripts" / "purge_degraded.py"
    spec = importlib.util.spec_from_file_location("purge_degraded", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["purge_degraded"] = module
    spec.loader.exec_module(module)
    return module


def test_purge_lists_degraded_failed_and_unknown_and_spares_the_rest(tmp_path: Path) -> None:
    purge = _purge_module()
    settings = load_settings("dev_light")
    settings.paths.processed_dir = tmp_path / "processed"
    db = Database(f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    db.create_all()
    storage = LocalStorage(tmp_path / "s")
    now = datetime(2026, 10, 3, tzinfo=UTC)

    def add(doc_id: str, **kw: object) -> None:
        values: dict[str, object] = {
            "sha256": doc_id[-1] * 64,
            "created_at": now,
            "status": "ready",
        }
        db.insert_doc(DocRecord(doc_id=doc_id, **(values | kw)))  # type: ignore[arg-type]
        storage.put_bytes(f"docs/{doc_id}/summary.json", b"{}", "application/json")

    add("doc_a", fingerprint="f", analysis_status="complete", pipeline_version="4.0")
    add(
        "doc_b",
        fingerprint="f",
        analysis_status="degraded",
        degraded_reasons=["stage_failed:facts"],
    )
    add("doc_c", analysis_status="failed")
    add("doc_d")  # legacy: no fingerprint
    add("doc_e", is_showcase=True)
    add("doc_f", status="processing")
    dry = purge.purge(db, storage, settings, apply=False)  # type: ignore[attr-defined]
    assert [d for d, _ in dry] == ["doc_b", "doc_c", "doc_d"]
    assert db.get_doc("doc_b") is not None  # a dry run deletes nothing
    purge.purge(db, storage, settings, apply=True)  # type: ignore[attr-defined]
    assert [d.doc_id for d in db.all_docs()] == ["doc_a", "doc_e", "doc_f"]
    assert storage.list("docs/doc_b/") == []
    assert storage.list("docs/doc_a/") != []
