"""CC-04: delete, re-analyse, stale-on-open and the preflight refusal over the HTTP API."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from make_fixture_pdf import build_offer_pdf

from finsight.api.app import create_app
from finsight.api.errors import ApiError
from finsight.api.routes_docs import _owned
from finsight.api.uploads_state import UploadState, get_upload_state
from finsight.auth import User
from finsight.core.config import load_settings
from finsight.core.schemas import DocRecord
from finsight.db import Database
from finsight.jobs import InlineLauncher, process_document
from finsight.jobs import preflight as pf
from finsight.storage import LocalStorage


@pytest.fixture
def state(tmp_path: Path) -> UploadState:
    settings = load_settings("dev_light")
    settings.jobs.poll_interval_s = 0.01
    settings.paths.processed_dir = tmp_path / "processed"
    db = Database(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    db.create_all()
    storage = LocalStorage(tmp_path / "store")
    launcher = InlineLauncher(lambda d, j: process_document(db, storage, settings, d, j), sync=True)
    return UploadState(settings, db, storage, launcher)


@pytest.fixture
def client(state: UploadState) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_upload_state] = lambda: state
    with TestClient(app) as test_client:
        yield test_client


def _upload(client: TestClient, tmp_path: Path, body: dict | None = None) -> tuple[str, int]:  # type: ignore[type-arg]
    pdf = tmp_path / "rhp.pdf"
    data = pdf.read_bytes() if pdf.exists() else build_offer_pdf(pdf, "rhp").read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    started = client.post(
        "/api/uploads/init", json={"filename": "x.pdf", "size_bytes": len(data), "sha256": sha}
    ).json()
    client.post(started["upload_url"], content=data, headers={"Content-Type": "application/pdf"})
    done = client.post(f"/api/uploads/{started['doc_id']}/complete", json=body)
    return str(started["doc_id"]), done.status_code


def _models_down(monkeypatch: pytest.MonkeyPatch, state: UploadState) -> None:
    state.settings.jobs.model_stages = True
    for name in pf.MODELS:
        monkeypatch.setitem(pf.DEFAULT_PROBES, name, lambda s: (True, "ok"))
    monkeypatch.setitem(pf.DEFAULT_PROBES, "ollama", lambda s: (False, "Ollama is not running"))


def test_finished_analysis_is_stamped_complete(client: TestClient, tmp_path: Path) -> None:
    doc_id, code = _upload(client, tmp_path)
    assert code == 200
    detail = client.get(f"/api/docs/{doc_id}").json()
    assert detail["doc"]["analysis_status"] == "complete"
    assert detail["doc"]["pipeline_version"] == load_settings("dev_light").pipeline_version
    assert detail["cache"]["state"] == "fresh"
    assert detail["cache"]["reanalysing"] is False


def test_models_down_refuses_the_upload_and_keeps_the_file(
    client: TestClient, state: UploadState, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _models_down(monkeypatch, state)
    doc_id, code = _upload(client, tmp_path)
    assert code == 503
    assert state.storage.exists(f"docs/{doc_id}/source.pdf")
    assert state.db.get_doc(doc_id).status == "uploading"  # type: ignore[union-attr]
    retry = client.post(f"/api/uploads/{doc_id}/complete")
    assert retry.json()["error"]["code"] == "models_unavailable"
    assert "Ollama is not running" in retry.json()["error"]["message"]


def test_analyse_without_the_model_gives_a_degraded_report(
    client: TestClient, state: UploadState, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _models_down(monkeypatch, state)
    doc_id, code = _upload(client, tmp_path, {"analyse_without": ["ollama"]})
    assert code == 200
    doc = client.get(f"/api/docs/{doc_id}").json()["doc"]
    assert doc["analysis_status"] == "degraded"
    assert "skipped_model:ollama" in doc["degraded_reasons"]
    report = client.get(f"/api/docs/{doc_id}/report")
    assert "Cache-Control" not in report.headers  # a degraded report is never cached as complete


def test_pipeline_version_bump_reanalyses_on_open(
    client: TestClient, state: UploadState, tmp_path: Path
) -> None:
    doc_id, _ = _upload(client, tmp_path)
    first_job = client.get(f"/api/docs/{doc_id}").json()["job_id"]
    state.settings.pipeline_version = "next-version"
    opened = client.get(f"/api/docs/{doc_id}").json()
    assert opened["cache"]["reanalysing"] is True
    assert opened["cache"]["state"] == "stale_version"
    after = client.get(f"/api/docs/{doc_id}").json()  # the synchronous test launcher has finished
    assert after["job_id"] != first_job
    assert after["doc"]["pipeline_version"] == "next-version"
    assert after["cache"]["state"] == "fresh"


def test_stale_analysis_is_kept_when_the_models_are_down(
    client: TestClient, state: UploadState, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc_id, _ = _upload(client, tmp_path)
    _models_down(monkeypatch, state)
    state.settings.pipeline_version = "next-version"
    opened = client.get(f"/api/docs/{doc_id}").json()
    assert opened["cache"]["reanalysing"] is False
    assert "Ollama is not running" in opened["cache"]["blocked"]
    assert opened["doc"]["status"] == "ready"  # still readable
    assert state.storage.exists(f"docs/{doc_id}/summary.json")


def test_reanalyse_endpoint_starts_a_fresh_job(
    client: TestClient, state: UploadState, tmp_path: Path
) -> None:
    doc_id, _ = _upload(client, tmp_path)
    before = client.get(f"/api/docs/{doc_id}").json()["job_id"]
    resp = client.post(f"/api/docs/{doc_id}/reanalyse")
    assert resp.status_code == 200
    assert resp.json()["job_id"] != before
    assert client.get(f"/api/docs/{doc_id}").json()["doc"]["analysis_status"] == "complete"


def test_reanalyse_refuses_when_a_model_is_down_and_leaves_the_old_report(
    client: TestClient, state: UploadState, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc_id, _ = _upload(client, tmp_path)
    _models_down(monkeypatch, state)
    resp = client.post(f"/api/docs/{doc_id}/reanalyse")
    assert (resp.status_code, resp.json()["error"]["code"]) == (503, "models_unavailable")
    assert state.storage.exists(f"docs/{doc_id}/summary.json")  # nothing was deleted


def test_delete_removes_files_rows_and_the_published_workspace(
    client: TestClient, state: UploadState, tmp_path: Path
) -> None:
    doc_id, _ = _upload(client, tmp_path)
    published = state.settings.paths.processed_dir / doc_id
    published.mkdir(parents=True)
    (published / "upload.json").write_text("{}")
    assert state.storage.list(f"docs/{doc_id}/")
    resp = client.delete(f"/api/docs/{doc_id}")
    assert resp.status_code == 200
    assert state.storage.list(f"docs/{doc_id}/") == []
    assert not published.exists()
    assert state.db.get_doc(doc_id) is None
    assert client.get(f"/api/docs/{doc_id}").status_code == 404
    again, code = _upload(client, tmp_path)  # same PDF: analysed from scratch
    assert (again, code) == (doc_id, 200)


def test_showcase_and_other_users_documents_are_protected() -> None:
    showcase = DocRecord(
        doc_id="x",
        sha256="a" * 64,
        created_at=__import__("datetime").datetime.now(),
        is_showcase=True,
    )
    with pytest.raises(ApiError) as err:
        _owned(showcase, User("someone", None, is_admin=True))
    assert err.value.status_code == 403
    theirs = showcase.model_copy(update={"is_showcase": False, "uploaded_by": "u1"})
    with pytest.raises(ApiError):
        _owned(theirs, User("u2", None))
    _owned(theirs, User("u1", None))
    _owned(theirs, User("admin", None, is_admin=True))


def test_cannot_delete_while_processing(
    client: TestClient, state: UploadState, tmp_path: Path
) -> None:
    doc_id, _ = _upload(client, tmp_path)
    state.db.update_doc(doc_id, status="processing")
    resp = client.delete(f"/api/docs/{doc_id}")
    assert (resp.status_code, resp.json()["error"]["code"]) == (409, "doc_busy")
