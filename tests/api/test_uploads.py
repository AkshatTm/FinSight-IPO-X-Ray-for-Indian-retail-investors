"""B1.2: contract tests for the B06 §2-3 upload and document endpoints on the local profile."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from make_fixture_pdf import build_offer_pdf

from finsight.api.app import create_app
from finsight.api.uploads_state import UploadState, get_upload_state
from finsight.core.config import AuthConfig, load_settings
from finsight.db import Database
from finsight.jobs import InlineLauncher, process_document
from finsight.storage import LocalStorage


@pytest.fixture
def state(tmp_path: Path) -> UploadState:
    settings = load_settings("dev_light")
    settings.jobs.poll_interval_s = 0.01
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


def _pdf(tmp_path: Path, kind: str = "rhp") -> bytes:
    return build_offer_pdf(tmp_path / f"{kind}.pdf", kind).read_bytes()


def _init(client: TestClient, data: bytes, sha: str | None = None) -> dict:  # type: ignore[type-arg]
    body = {
        "filename": "x.pdf",
        "size_bytes": len(data),
        "sha256": sha or hashlib.sha256(data).hexdigest(),
    }
    return client.post("/api/uploads/init", json=body).json()


def _upload(client: TestClient, data: bytes) -> str:
    started = _init(client, data)
    assert started["status"] == "upload"
    assert started["upload_method"] == "POST"
    put = client.post(
        started["upload_url"], content=data, headers={"Content-Type": "application/pdf"}
    )
    assert put.status_code == 200
    done = client.post(f"/api/uploads/{started['doc_id']}/complete")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "queued"
    return str(started["doc_id"])


def _events(client: TestClient, doc_id: str, last: int | None = None) -> list[tuple[int, str]]:
    headers = {"Last-Event-ID": str(last)} if last is not None else {}
    text = client.get(f"/api/docs/{doc_id}/events", headers=headers).text
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((int(lines["id"]), lines["event"]))
    return out


def test_full_upload_flow(client: TestClient, tmp_path: Path) -> None:
    doc_id = _upload(client, _pdf(tmp_path, "drhp"))
    events = _events(client, doc_id)
    assert [e for _, e in events] == ["stage", "stage", "stage", "stage", "stage", "done"]
    assert [s for s, _ in events] == [1, 2, 3, 4, 5, 6]
    assert _events(client, doc_id, last=4) == events[4:]  # replay after any seq
    detail = client.get(f"/api/docs/{doc_id}").json()
    assert detail["doc"]["doc_type"] == "drhp"
    assert detail["doc"]["status"] == "ready"
    assert [(s["stage"], s["status"]) for s in detail["stages"]] == [
        ("received", "done"),
        ("validated", "done"),
        ("detected", "done"),
    ]
    report = client.get(f"/api/docs/{doc_id}/report")
    assert report.status_code == 200
    assert report.headers["Cache-Control"] == "public, max-age=3600"
    assert report.json()["doc"]["doc_id"] == doc_id
    cached = client.get(
        f"/api/docs/{doc_id}/report", headers={"If-None-Match": report.headers["ETag"]}
    )
    assert cached.status_code == 304
    mine = client.get("/api/me/uploads").json()
    assert [(m["doc_id"], m["status"]) for m in mine] == [(doc_id, "ready")]


def test_same_file_again_returns_exists_without_using_quota(
    client: TestClient, state: UploadState, tmp_path: Path
) -> None:
    data = _pdf(tmp_path)
    doc_id = _upload(client, data)
    assert _init(client, data) == {
        "status": "exists",
        "doc_id": doc_id,
        "upload_url": None,
        "upload_method": None,
        "expires_at": None,
    }
    assert state.db.count_uploads(state.db.get_doc(doc_id).created_at.replace(hour=0)) == 1  # type: ignore[union-attr]


def test_hash_mismatch_is_rejected_and_file_removed(
    client: TestClient, state: UploadState, tmp_path: Path
) -> None:
    data = _pdf(tmp_path)
    started = _init(client, data, sha="f" * 64)
    client.post(started["upload_url"], content=data)
    resp = client.post(f"/api/uploads/{started['doc_id']}/complete")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "hash_mismatch"
    assert state.storage.list(f"docs/{started['doc_id']}/") == []


def test_validation_rejection_arrives_on_the_doc(client: TestClient, tmp_path: Path) -> None:
    doc_id = _upload(client, _pdf(tmp_path, "scanned"))
    doc = client.get(f"/api/docs/{doc_id}").json()["doc"]
    assert (doc["status"], doc["rejection"]) == ("failed", "scanned")


def test_per_user_quota(client: TestClient, tmp_path: Path) -> None:
    for i in range(3):
        assert _init(client, f"file {i}".encode())["status"] == "upload"
    resp = client.post(
        "/api/uploads/init", json={"filename": "x", "size_bytes": 5, "sha256": "e" * 64}
    )
    assert resp.status_code == 429
    error = resp.json()["error"]
    assert (error["code"], error["limit"]) == ("quota_exceeded", 3)
    assert error["resets_at"].endswith("+05:30")


def test_global_quota(client: TestClient, state: UploadState) -> None:
    state.settings.uploads.per_user_per_day = 99
    state.settings.uploads.global_per_day = 2
    for i in range(2):
        _init(client, f"g{i}".encode())
    resp = client.post(
        "/api/uploads/init", json={"filename": "x", "size_bytes": 5, "sha256": "d" * 64}
    )
    assert (resp.status_code, resp.json()["error"]["code"]) == (429, "global_quota_exceeded")


def test_kill_switch(client: TestClient, state: UploadState) -> None:
    state.settings.uploads.enabled = False
    resp = client.post(
        "/api/uploads/init", json={"filename": "x", "size_bytes": 5, "sha256": "c" * 64}
    )
    assert (resp.status_code, resp.json()["error"]["code"]) == (503, "uploads_disabled")


def test_too_large_at_init(client: TestClient) -> None:
    resp = client.post(
        "/api/uploads/init",
        json={"filename": "x", "size_bytes": 50 * 1024 * 1024 + 1, "sha256": "b" * 64},
    )
    assert (resp.status_code, resp.json()["error"]["code"]) == (422, "too_large")


def test_complete_without_init_and_unknown_doc(client: TestClient) -> None:
    resp = client.post("/api/uploads/doc_0123456789abcdef/complete")
    assert (resp.status_code, resp.json()["error"]["code"]) == (409, "upload_not_started")
    assert client.get("/api/docs/doc_0123456789abcdef").status_code == 404


def test_supabase_mode_needs_a_token(client: TestClient, state: UploadState) -> None:
    state.settings.auth = AuthConfig(
        mode="supabase", supabase_url="https://x.supabase.co", jwt_secret="s" * 40
    )
    resp = client.post(
        "/api/uploads/init", json={"filename": "x", "size_bytes": 5, "sha256": "a" * 64}
    )
    assert (resp.status_code, resp.json()["error"]["code"]) == (401, "unauthorized")
    assert client.get("/api/me/uploads").status_code == 401


def test_job_events_are_in_the_openapi_document(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    stream = schema["paths"]["/api/docs/{doc_id}/events"]["get"]["responses"]["200"]
    assert set(stream["content"]["text/event-stream"]["x-sse-events"]) == {
        "stage",
        "progress",
        "ready",
        "risk_simplified",
        "done",
    }


def test_limits_follow_the_config(client: TestClient, state: UploadState) -> None:
    assert client.get("/api/uploads/limits").json() == {
        "enabled": True,
        "max_mb": 50,
        "max_pages": 1500,
        "per_user_per_day": 3,
    }
    state.settings.uploads.enabled = False
    assert client.get("/api/uploads/limits").json()["enabled"] is False


def test_worker_launch_failure_is_a_503_and_a_failed_job(
    client: TestClient, state: UploadState, tmp_path: Path
) -> None:
    from finsight.jobs import LaunchError

    class Down:
        def launch(self, doc_id: str, job_id: str) -> None:
            raise LaunchError("Cloud Run returned 403")

    state.launcher = Down()
    data = _pdf(tmp_path)
    started = _init(client, data)
    client.post(started["upload_url"], content=data, headers={"Content-Type": "application/pdf"})
    done = client.post(f"/api/uploads/{started['doc_id']}/complete")
    assert done.status_code == 503
    assert done.json()["error"]["code"] == "worker_unavailable"
    assert "403" not in done.text  # internal detail stays in the job row
    detail = client.get(f"/api/docs/{started['doc_id']}").json()
    assert detail["doc"]["status"] == "failed"
    assert _events(client, started["doc_id"])[-1][1] == "done"
