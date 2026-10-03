"""B3.3a: scripts/cloud_smoke.py against the real API app (local profile, synthetic RHP)."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from make_fixture_pdf import build_offer_pdf

from finsight.api.app import create_app
from finsight.api.uploads_state import UploadState, get_upload_state
from finsight.core.config import load_settings
from finsight.db import Database
from finsight.jobs import InlineLauncher, process_document
from finsight.storage import LocalStorage

SPEC = importlib.util.spec_from_file_location(
    "cloud_smoke", Path(__file__).resolve().parents[2] / "scripts" / "cloud_smoke.py"
)
assert SPEC is not None
assert SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
sys.modules["cloud_smoke"] = smoke
SPEC.loader.exec_module(smoke)

BASE = "https://api.example.test"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = load_settings("dev_light")
    db = Database(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    db.create_all()
    storage = LocalStorage(tmp_path / "store")
    launcher = InlineLauncher(lambda d, j: process_document(db, storage, settings, d, j), sync=True)
    app = create_app()
    app.dependency_overrides[get_upload_state] = lambda: UploadState(
        settings, db, storage, launcher
    )
    with TestClient(app) as test_client:
        yield test_client


def adapter(client: TestClient, seen: list[tuple[str, str, dict[str, str]]]) -> Any:
    def http(method: str, url: str, body: bytes | None, headers: dict[str, str]) -> Any:
        seen.append((method, url, headers))
        resp = client.request(method, url.removeprefix(BASE), content=body, headers=headers)
        return smoke.Response(resp.status_code, resp.content)

    return http


def test_full_smoke_passes_on_the_local_api(client: TestClient, tmp_path: Path) -> None:
    pdf = build_offer_pdf(tmp_path / "rhp.pdf", "rhp").read_bytes()
    seen: list[tuple[str, str, dict[str, str]]] = []
    run = smoke.Smoke(BASE, http=adapter(client, seen), token="t0k", sleep=lambda s: None)
    summary = run.run(pdf, "rhp.pdf", timeout_s=30)
    assert summary["ok"], summary
    assert [s["step"] for s in summary["steps"]] == [
        "health",
        "limits",
        "upload",
        "process",
        "report",
    ]
    assert summary["steps"][3]["status"] == "ready"
    assert all(h.get("Authorization") == "Bearer t0k" for _, _, h in seen)
    assert "t0k" not in str(summary)  # the token never reaches the printed summary
    again = smoke.Smoke(BASE, http=adapter(client, []), sleep=lambda s: None).run(
        pdf, "rhp.pdf", 30
    )
    assert again["steps"][2]["exists"] is True


def test_signed_gcs_url_gets_the_file_without_the_api_token() -> None:
    calls: list[tuple[str, str, dict[str, str]]] = []

    def http(method: str, url: str, body: bytes | None, headers: dict[str, str]) -> Any:
        calls.append((method, url, headers))
        if url.endswith("/init"):
            return smoke.Response(
                200,
                b'{"status": "upload", "doc_id": "d1", "upload_method": "PUT",'
                b' "upload_url": "https://storage.googleapis.com/b/docs/d1/source.pdf?sig=x"}',
            )
        if url.endswith("/complete"):
            return smoke.Response(200, b'{"doc_id": "d1", "job_id": "j1", "status": "queued"}')
        return smoke.Response(200, b"")

    out = smoke.Smoke(BASE, http=http, token="secret").upload(b"%PDF-1.7", "x.pdf")
    assert out == {"doc_id": "d1", "job_id": "j1", "exists": False}
    put = calls[1]
    assert put[0] == "PUT"
    assert put[1].startswith("https://storage.googleapis.com/")
    assert "Authorization" not in put[2]


def test_failures_are_reported_not_raised() -> None:
    def down(method: str, url: str, body: bytes | None, headers: dict[str, str]) -> Any:
        return smoke.Response(503, b'{"error": {"code": "worker_unavailable"}}')

    summary = smoke.Smoke(BASE, http=down).run(b"%PDF", "x.pdf", 1)
    assert summary["ok"] is False
    assert summary["steps"][0]["error"] == "health returned 503 worker_unavailable"
    assert [s["step"] for s in summary["steps"]] == ["health", "limits", "upload"]


def test_wait_times_out() -> None:
    def processing(method: str, url: str, body: bytes | None, headers: dict[str, str]) -> Any:
        return smoke.Response(200, b'{"doc": {"status": "processing"}, "stages": []}')

    ticks = iter(range(100))
    run = smoke.Smoke(BASE, http=processing, clock=lambda: float(next(ticks)), sleep=lambda s: None)
    with pytest.raises(smoke.SmokeFailed, match="still processing"):
        run.wait("d1", timeout_s=3)
