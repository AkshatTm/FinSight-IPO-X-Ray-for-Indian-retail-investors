"""B3.3a: the Cloud Run job launcher (Run Admin API v2) and the worker's simplify command."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from finsight.core.config import load_settings
from finsight.core.ids import make_doc_id
from finsight.core.schemas import DocRecord, Risk
from finsight.db import Database, utcnow
from finsight.jobs import CloudRunLauncher, LaunchError, cloud_run_launcher
from finsight.jobs import launcher as launcher_mod
from finsight.jobs.__main__ import simplify_document
from finsight.storage import LocalStorage, doc_key, get_json, put_json


def test_run_request_targets_the_job_with_env_overrides() -> None:
    calls: list[tuple[str, dict[str, Any], str]] = []
    launcher = CloudRunLauncher(
        "proj-1",
        "asia-southeast1",
        "finsight-worker",
        token=lambda: "tok",
        post=lambda url, body, token: calls.append((url, body, token)) or {},
    )
    launcher.launch("d_abc", "j_1")
    url, body, token = calls[0]
    assert url == (
        "https://run.googleapis.com/v2/projects/proj-1/locations/asia-southeast1/"
        "jobs/finsight-worker:run"
    )
    assert token == "tok"
    assert body == {
        "overrides": {
            "containerOverrides": [
                {"env": [{"name": "DOC_ID", "value": "d_abc"}, {"name": "JOB_ID", "value": "j_1"}]}
            ],
            "taskCount": 1,
        }
    }


def test_env_defaults_and_missing_project() -> None:
    launcher = cloud_run_launcher("finsight-worker", {"GCP_PROJECT": "p"})
    assert (launcher.project, launcher.region) == ("p", "asia-southeast1")
    with pytest.raises(LaunchError, match="GCP_PROJECT"):
        cloud_run_launcher("finsight-worker", {}).launch("d", "j")


def test_http_errors_become_launch_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(req: Any, timeout: float) -> Any:
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(launcher_mod.urllib.request, "urlopen", refuse)
    with pytest.raises(LaunchError, match="403"):
        launcher_mod.post_json("https://run.googleapis.com/v2/x:run", {}, "t")
    with pytest.raises(LaunchError, match="metadata"):
        launcher_mod.metadata_token()


def test_post_json_sends_bearer_json(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class Resp:
        def __enter__(self) -> Resp:
            return self

        def __exit__(self, *a: object) -> None:
            return None

        def read(self, *a: object) -> bytes:
            return b'{"name": "operations/1"}'

    def fake(req: Any, timeout: float) -> Resp:
        seen.update(url=req.full_url, auth=req.get_header("Authorization"), body=req.data)
        return Resp()

    monkeypatch.setattr(launcher_mod.urllib.request, "urlopen", fake)
    out = launcher_mod.post_json("https://run.googleapis.com/v2/x:run", {"a": 1}, "tok")
    assert out == {"name": "operations/1"}
    assert seen["auth"] == "Bearer tok"
    assert json.loads(seen["body"]) == {"a": 1}


class FakeSimplifier:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def rewrite(self, title: str, body: str) -> Any:
        self.seen.append(title)

        class R:
            status = "ready"

            def as_dict(self) -> dict[str, Any]:
                return {"simple": f"plain {title}", "simple_status": "ready"}

        return R()


def test_simplify_command_queues_top_n_by_importance(tmp_path: Path) -> None:
    settings = load_settings("dev_light")
    settings.simplify.auto_top_n = 2
    db = Database(f"sqlite:///{(tmp_path / 'w.db').as_posix()}")
    db.create_all()
    storage = LocalStorage(tmp_path / "store")
    doc_id = make_doc_id("a" * 64)
    db.insert_doc(DocRecord(doc_id=doc_id, sha256="a" * 64, created_at=utcnow(), status="ready"))
    job = db.create_job(doc_id)
    risks = [
        Risk(
            rid=f"r{i}", order=i, title=f"t{i}", body="b", page_start=1, page_end=1, importance=imp
        )
        for i, imp in enumerate([0.1, 0.9, None, 0.5])
    ]
    put_json(storage, doc_key(doc_id, "risks.json"), [r.model_dump(mode="json") for r in risks])
    fake = FakeSimplifier()
    counts = simplify_document(db, storage, settings, doc_id, fake)
    assert fake.seen == ["t1", "t3"]  # the two most important, most important first
    assert counts["ready"] == 2
    assert set(get_json(storage, doc_key(doc_id, "simplified.json"))) == {"r1", "r3"}
    events = [e.event for e in db.events_after(job.job_id)]
    assert events == ["risk_simplified", "risk_simplified"]
