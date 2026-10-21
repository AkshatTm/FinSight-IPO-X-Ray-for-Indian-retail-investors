"""CC-04: preflight refuses a job when a model is missing, "analyse without" degrades it."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from finsight import jobs as jobs_module
from finsight.core.config import Settings, load_settings
from finsight.core.schemas import DocRecord
from finsight.db import Database
from finsight.jobs import preflight as pf
from finsight.jobs import process_document
from finsight.jobs.cache import Fingerprint
from finsight.jobs.runner import Stage
from finsight.storage import LocalStorage, put_json

T0 = datetime(2026, 10, 3, 6, 0, tzinfo=UTC)


def _ok(_: Settings) -> tuple[bool, str]:
    return True, "fine"


def _down(_: Settings) -> tuple[bool, str]:
    return False, "Ollama is not running at http://localhost:11434"


@pytest.fixture
def settings() -> Settings:
    cfg = load_settings("dev_light")
    cfg.jobs.model_stages = True  # preflight only checks the models of stages that are on
    return cfg


@pytest.fixture
def probes(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in pf.MODELS:
        monkeypatch.setitem(pf.DEFAULT_PROBES, name, _ok)


def test_no_model_stages_means_nothing_to_check() -> None:
    cfg = load_settings("dev_light")
    cfg.jobs.model_stages = False
    assert pf.run_preflight(cfg, probes={"ollama": _down}).ok


def test_a_missing_model_blocks_and_the_message_names_it(settings: Settings) -> None:
    result = pf.run_preflight(settings, probes={n: _ok for n in pf.MODELS} | {"ollama": _down})
    assert not result.ok
    assert result.missing == ["ollama"]
    assert "Ollama is not running" in result.message()


def test_ticking_a_model_off_unblocks_but_still_reports_it(settings: Settings) -> None:
    probes = {n: _ok for n in pf.MODELS} | {"ollama": _down}
    result = pf.run_preflight(settings, skip=["ollama"], probes=probes)
    assert result.ok
    assert result.missing == ["ollama"]


def test_classifier_check_reports_a_missing_folder(tmp_path: Path, settings: Settings) -> None:
    settings.paths.models_dir = tmp_path
    ok, detail = pf._check_classifier(settings)
    assert not ok
    assert "model.onnx" in detail


def _doc(db: Database, skipped: list[str] | None = None) -> str:
    db.insert_doc(
        DocRecord(doc_id="doc_a", sha256="a" * 64, created_at=T0, skipped_models=skipped or [])
    )
    return "doc_a"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    database.create_all()
    return database


def _stage(name: str) -> Stage:
    def fn(ctx: object) -> dict[str, object]:
        put_json(ctx.storage, ctx.key(f"{name}.json"), {"ran": name})  # type: ignore[attr-defined]
        return {"ready": True}

    return Stage(name, fn, output=f"{name}.json")


def test_models_down_refuses_the_job_before_any_stage_runs(
    db: Database,
    tmp_path: Path,
    settings: Settings,
    probes: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(pf.DEFAULT_PROBES, "ollama", _down)
    ran: list[str] = []
    monkeypatch.setattr(jobs_module, "upload_stages", lambda models=True: ran.append("x") or [])
    storage = LocalStorage(tmp_path / "s")
    doc_id = _doc(db)
    job = db.create_job(doc_id)
    result = process_document(db, storage, settings, doc_id, job.job_id)
    assert (result.status, result.failed_stages) == ("failed", ["preflight"])
    assert ran == []  # no stage was even built
    doc = db.get_doc(doc_id)
    assert doc is not None
    assert (doc.status, doc.analysis_status) == ("failed", "failed")
    assert doc.degraded_reasons == ["model_missing:ollama"]
    events = db.events_after(job.job_id)
    assert [e.event for e in events] == ["stage", "done"]
    assert "Ollama is not running" in str(events[0].data["detail"]["message"])  # type: ignore[index]


def test_analyse_without_runs_degraded_and_never_complete(
    db: Database,
    tmp_path: Path,
    settings: Settings,
    probes: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(pf.DEFAULT_PROBES, "ollama", _down)
    monkeypatch.setattr(
        jobs_module, "upload_stages", lambda models=True: [_stage("facts"), _stage("simplify")]
    )
    monkeypatch.setattr(
        jobs_module, "models_fingerprint", lambda s, skip=(): Fingerprint("fp-skipped", {})
    )
    storage = LocalStorage(tmp_path / "s")
    doc_id = _doc(db, skipped=["ollama"])
    job = db.create_job(doc_id)
    result = process_document(db, storage, settings, doc_id, job.job_id)
    assert result.status == "partial"
    doc = db.get_doc(doc_id)
    assert doc is not None
    assert doc.analysis_status == "degraded"
    assert doc.degraded_reasons == ["skipped_model:ollama"]
    assert (doc.pipeline_version, doc.fingerprint) == (settings.pipeline_version, "fp-skipped")
    assert storage.exists("docs/doc_a/facts.json")
    assert not storage.exists("docs/doc_a/simplify.json")  # the skipped stage did not run


def test_a_ticked_model_that_came_back_runs_normally(
    db: Database,
    tmp_path: Path,
    settings: Settings,
    probes: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(jobs_module, "upload_stages", lambda models=True: [_stage("simplify")])
    monkeypatch.setattr(jobs_module, "models_fingerprint", lambda s, skip=(): Fingerprint("fp", {}))
    storage = LocalStorage(tmp_path / "s")
    doc_id = _doc(db, skipped=["ollama"])
    job = db.create_job(doc_id)
    assert process_document(db, storage, settings, doc_id, job.job_id).status == "ready"
    doc = db.get_doc(doc_id)
    assert doc is not None
    assert doc.analysis_status == "complete"
