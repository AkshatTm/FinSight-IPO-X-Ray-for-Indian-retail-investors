"""CC-04: the cache key, staleness, status and delete."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from finsight.core.config import Settings, load_settings
from finsight.core.schemas import DocRecord
from finsight.db import Database
from finsight.jobs import cache_key, delete_document
from finsight.jobs.cache import (
    Fingerprint,
    analysis_status,
    cache_state,
    models_fingerprint,
    reset_for_reanalysis,
)
from finsight.storage import LocalStorage

T0 = datetime(2026, 10, 3, 6, 0, tzinfo=UTC)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    cfg = load_settings("dev_light")
    cfg.paths.processed_dir = tmp_path / "processed"
    cfg.paths.data_dir = tmp_path / "data"
    return cfg


def _doc(settings: Settings, **kw: object) -> DocRecord:
    base: dict[str, object] = {
        "doc_id": "doc_a",
        "sha256": "a" * 64,
        "created_at": T0,
        "status": "ready",
        "pipeline_version": settings.pipeline_version,
        "fingerprint": "fp1",
    }
    return DocRecord(**(base | kw))  # type: ignore[arg-type]


def test_cache_key_changes_with_each_part() -> None:
    base = cache_key("a" * 64, "4.0", "fp")
    assert base == cache_key("a" * 64, "4.0", "fp")
    assert len({base, cache_key("b" * 64, "4.0", "fp"), cache_key("a" * 64, "4.1", "fp"),
                cache_key("a" * 64, "4.0", "fp2")}) == 4  # fmt: skip


def test_matching_version_and_models_is_fresh(settings: Settings) -> None:
    assert cache_state(_doc(settings), settings, Fingerprint("fp1", {})) == "fresh"


def test_pipeline_version_bump_makes_it_stale(settings: Settings) -> None:
    doc = _doc(settings)
    settings.pipeline_version = "next"
    assert cache_state(doc, settings, Fingerprint("fp1", {})) == "stale_version"


def test_other_model_weights_make_it_stale(settings: Settings) -> None:
    assert cache_state(_doc(settings), settings, Fingerprint("fp2", {})) == "stale_models"


def test_models_that_cannot_be_identified_do_not_force_a_rerun(settings: Settings) -> None:
    assert cache_state(_doc(settings), settings, Fingerprint(None, {})) == "fresh"


def test_unknown_fingerprint_counts_as_stale(settings: Settings) -> None:
    legacy = _doc(settings, fingerprint=None, pipeline_version=None)
    assert cache_state(legacy, settings, Fingerprint("fp1", {})) == "legacy"


def test_status_complete_degraded_failed() -> None:
    assert analysis_status("ready", [], []) == ("complete", [])
    assert analysis_status("partial", ["facts"], []) == ("degraded", ["stage_failed:facts"])
    assert analysis_status("ready", [], ["ollama"]) == ("degraded", ["skipped_model:ollama"])
    assert analysis_status("failed", ["parsed"], []) == ("failed", ["failed:parsed"])


def test_fingerprint_is_empty_but_stable_when_model_stages_are_off(settings: Settings) -> None:
    settings.jobs.model_stages = False
    one, two = models_fingerprint(settings), models_fingerprint(settings)
    assert one.value is not None
    assert one.value == two.value


def test_skipping_a_model_changes_the_fingerprint(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finsight.jobs import preflight as pf

    settings.jobs.model_stages = True
    monkeypatch.setattr(pf, "required_models", lambda s: ("ollama",))
    monkeypatch.setattr(pf, "ollama_digest", lambda s: "abc")
    full = models_fingerprint(settings)
    skipped = models_fingerprint(settings, skip=["ollama"])
    assert full.value
    assert skipped.value
    assert full.value != skipped.value


def _setup(tmp_path: Path, settings: Settings) -> tuple[Database, LocalStorage]:
    db = Database(f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    db.create_all()
    storage = LocalStorage(tmp_path / "s")
    db.insert_doc(_doc(settings))
    storage.put_bytes("docs/doc_a/source.pdf", b"%PDF", "application/pdf")
    storage.put_bytes("docs/doc_a/risks.json", b"[]", "application/json")
    published = settings.paths.processed_dir / "doc_a" / "pages"
    published.mkdir(parents=True)
    (published / "1.webp").write_bytes(b"img")
    (settings.paths.processed_dir / "doc_a" / "chunks.jsonl").write_text("{}")
    db.enqueue("doc_a", ["r1", "r2"])
    return db, storage


def test_delete_removes_every_artifact(tmp_path: Path, settings: Settings) -> None:
    db, storage = _setup(tmp_path, settings)
    db.record_upload("local-dev", "doc_a")
    delete_document(db, storage, settings, "doc_a")
    assert storage.list("docs/doc_a/") == []
    assert not (settings.paths.processed_dir / "doc_a").exists()
    assert db.get_doc("doc_a") is None
    assert db.queue("doc_a") == []
    assert db.latest_job("doc_a") is None
    assert db.count_uploads(T0.replace(year=2000)) == 1  # the quota count survives


def test_reanalysis_keeps_only_the_pdf_and_starts_a_clean_job(
    tmp_path: Path, settings: Settings
) -> None:
    db, storage = _setup(tmp_path, settings)
    old = db.create_job("doc_a")
    job_id = reset_for_reanalysis(db, storage, settings, "doc_a", ["ollama"])
    assert job_id != old.job_id
    assert storage.list("docs/doc_a/") == ["docs/doc_a/source.pdf"]
    assert not (settings.paths.processed_dir / "doc_a").exists()
    doc = db.get_doc("doc_a")
    assert doc is not None
    assert (doc.status, doc.pipeline_version, doc.fingerprint, doc.analysis_status) == (
        "processing", None, None, None
    )  # fmt: skip
    assert doc.skipped_models == ["ollama"]
    assert db.queue("doc_a") == []
