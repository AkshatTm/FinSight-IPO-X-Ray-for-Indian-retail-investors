"""B3.5a: admin cost and failed-job endpoints (B06 §6), allow-listed by email."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterator
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from make_fixture_pdf import build_offer_pdf

from finsight.api.app import create_app
from finsight.api.uploads_state import UploadState, get_upload_state
from finsight.core.config import AuthConfig, load_settings
from finsight.db import Database
from finsight.jobs import InlineLauncher, process_document
from finsight.storage import LocalStorage

SECRET = "s" * 40
SUPABASE = "https://x.supabase.co"


@pytest.fixture
def state(tmp_path: Path) -> UploadState:
    settings = load_settings("dev_light")
    db = Database(f"sqlite:///{(tmp_path / 'admin.db').as_posix()}")
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


def _upload(client: TestClient, data: bytes) -> str:
    body = {
        "filename": "x.pdf",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    started = client.post("/api/uploads/init", json=body).json()
    client.post(started["upload_url"], content=data, headers={"Content-Type": "application/pdf"})
    assert client.post(f"/api/uploads/{started['doc_id']}/complete").status_code == 200
    return str(started["doc_id"])


def _token(email: str) -> str:
    now = int(time.time())
    claims = {
        "sub": f"user-{email}",
        "email": email,
        "aud": "authenticated",
        "iss": f"{SUPABASE}/auth/v1",
        "iat": now,
        "exp": now + 600,
    }
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_failed_jobs_list_names_the_reason(client: TestClient, tmp_path: Path) -> None:
    _upload(client, build_offer_pdf(tmp_path / "ok.pdf", "rhp").read_bytes())
    doc_id = _upload(client, build_offer_pdf(tmp_path / "s.pdf", "scanned").read_bytes())
    rows = client.get("/api/admin/jobs").json()
    assert [(r["job"]["doc_id"], r["job"]["error"]) for r in rows] == [(doc_id, "scanned")]
    assert len(client.get("/api/admin/jobs", params={"status": "done"}).json()) == 1
    assert client.get("/api/admin/jobs", params={"status": "nope"}).status_code == 422


def test_only_allow_listed_emails_get_in(client: TestClient, state: UploadState) -> None:
    state.settings.auth = AuthConfig(
        mode="supabase",
        supabase_url=SUPABASE,
        jwt_secret=SECRET,
        admin_emails=["Akshat@Example.com"],
    )
    assert client.get("/api/admin/jobs").status_code == 401
    other = {"Authorization": f"Bearer {_token('someone@example.com')}"}
    resp = client.get("/api/admin/jobs", headers=other)
    assert (resp.status_code, resp.json()["error"]["code"]) == (403, "forbidden")
    assert client.get("/api/admin/jobs", headers=other).status_code == 403
    admin = {"Authorization": f"Bearer {_token('akshat@example.com')}"}
    assert client.get("/api/admin/jobs", headers=admin).status_code == 200
