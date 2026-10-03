"""B1.2: the stage runner, events, quotas, kill switch and retention."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from make_fixture_pdf import build_offer_pdf

from finsight.core.config import UploadsConfig, load_settings
from finsight.core.ids import make_doc_id
from finsight.core.schemas import DocRecord
from finsight.db import Database
from finsight.jobs import (
    IST,
    JobContext,
    Stage,
    UploadBlocked,
    check_upload_allowed,
    day_window,
    process_document,
    run_job,
    sweep,
)
from finsight.storage import LocalStorage, doc_key, put_json

T0 = datetime(2026, 10, 3, 6, 0, tzinfo=UTC)  # 11:30 IST


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{(tmp_path / 'j.db').as_posix()}")
    database.create_all()
    return database


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "store")


def _ctx(db: Database, storage: LocalStorage, doc_id: str = "doc_a") -> JobContext:
    db.insert_doc(DocRecord(doc_id=doc_id, sha256=doc_id[-1] * 64, created_at=T0))
    job = db.create_job(doc_id)
    return JobContext(doc_id, job.job_id, db, storage, load_settings("dev_light"))


def _write(name: str, value: object = None) -> Stage:
    def fn(ctx: JobContext) -> dict[str, object]:
        put_json(ctx.storage, ctx.key(f"{name}.json"), {"stage": name})
        return {"ready": True}

    return Stage(name, fn, output=f"{name}.json")


def _boom(ctx: JobContext) -> None:
    raise RuntimeError("model crashed")


def test_three_stages_succeed(db: Database, storage: LocalStorage) -> None:
    ctx = _ctx(db, storage)
    result = run_job(ctx, [_write("facts"), _write("redflags"), _write("risk_level")])
    assert (result.status, result.failed_stages) == ("ready", [])
    events = [
        (e.event, e.data.get("stage") or e.data.get("part") or e.data.get("status"))
        for e in db.events_after(ctx.job_id)
    ]
    assert events == [
        ("stage", "facts"),
        ("stage", "facts"),
        ("ready", "facts"),
        ("stage", "redflags"),
        ("stage", "redflags"),
        ("ready", "redflags"),
        ("stage", "risk_level"),
        ("stage", "risk_level"),
        ("ready", "risk_level"),
        ("done", "ready"),
    ]
    doc, job = db.get_doc("doc_a"), db.get_job(ctx.job_id)
    assert doc is not None
    assert job is not None
    assert (doc.status, job.status) == ("ready", "done")
    assert set(job.progress["timings_s"]) == {"facts", "redflags", "risk_level"}


def test_one_failing_stage_gives_partial_and_keeps_earlier_outputs(
    db: Database, storage: LocalStorage
) -> None:
    ctx = _ctx(db, storage)
    stages = [
        _write("facts"),
        Stage("redflags", _boom, requires=("facts",)),
        Stage("risk_level", _write("risk_level").fn, requires=("redflags",)),
        _write("compare"),
    ]
    result = run_job(ctx, stages)
    assert result.status == "partial"
    assert result.failed_stages == ["redflags", "risk_level"]
    assert storage.exists(doc_key("doc_a", "facts.json"))
    assert storage.exists(doc_key("doc_a", "compare.json"))
    last = db.events_after(ctx.job_id)[-1]
    assert (last.event, last.data) == (
        "done",
        {"status": "partial", "failed_stages": ["redflags", "risk_level"]},
    )
    failed = [e.data for e in db.events_after(ctx.job_id) if e.data.get("status") == "failed"]
    assert failed[0]["detail"] == {
        "error": "RuntimeError"
    }  # no message or trace leaks to the client
    assert failed[1]["detail"] == {"skipped_because": ["redflags"]}


def test_stage_failure_is_logged_as_json_with_the_ids(db: Database, storage: LocalStorage) -> None:
    import io
    import json
    import logging

    from finsight.core.logging import configure_logging

    out = io.StringIO()
    configure_logging(stream=out)
    try:
        ctx = _ctx(db, storage)
        run_job(ctx, [Stage("redflags", _boom)])
    finally:
        logging.getLogger("finsight").handlers.clear()
    line = json.loads(out.getvalue().splitlines()[0])
    assert (line["doc_id"], line["job_id"], line["stage"]) == ("doc_a", ctx.job_id, "redflags")
    assert line["level"] == "ERROR"
    assert "model crashed" in line["exc"]


def test_critical_failure_fails_the_job(db: Database, storage: LocalStorage) -> None:
    ctx = _ctx(db, storage)
    result = run_job(ctx, [Stage("parsed", _boom, critical=True), _write("facts")])
    assert (result.status, result.failed_stages) == ("failed", ["parsed"])
    assert not storage.exists(doc_key("doc_a", "facts.json"))


def test_stages_are_idempotent_on_retry(db: Database, storage: LocalStorage) -> None:
    calls: list[str] = []

    def count(ctx: JobContext) -> None:
        calls.append(ctx.job_id)
        put_json(ctx.storage, ctx.key("facts.json"), {})

    ctx = _ctx(db, storage)
    run_job(ctx, [Stage("facts", count, output="facts.json")])
    retry = JobContext("doc_a", db.create_job("doc_a").job_id, db, storage, ctx.settings)
    run_job(retry, [Stage("facts", count, output="facts.json")])
    assert len(calls) == 1
    assert db.events_after(retry.job_id)[0].data["detail"] == {"cached": True}


@pytest.mark.parametrize(
    ("kind", "status", "rejection", "doc_type"),
    [("drhp", "ready", None, "drhp"), ("scanned", "failed", "scanned", None)],
)
def test_upload_pipeline_validates_and_detects(
    db: Database,
    storage: LocalStorage,
    tmp_path: Path,
    kind: str,
    status: str,
    rejection: str | None,
    doc_type: str | None,
) -> None:
    pdf = build_offer_pdf(tmp_path / f"{kind}.pdf", kind).read_bytes()
    import hashlib

    sha = hashlib.sha256(pdf).hexdigest()
    doc_id = make_doc_id(sha)
    db.insert_doc(DocRecord(doc_id=doc_id, sha256=sha, created_at=T0))
    storage.put_bytes(doc_key(doc_id, "source.pdf"), pdf)
    job = db.create_job(doc_id)
    result = process_document(db, storage, load_settings("dev_light"), doc_id, job.job_id)
    doc = db.get_doc(doc_id)
    assert doc is not None
    assert (result.status, doc.status, doc.rejection, doc.doc_type) == (
        status,
        status,
        rejection,
        doc_type,
    )
    if doc_type:
        assert doc.pages == 5


# ---------------------------------------------------------------- quotas and kill switch
def test_day_window_is_the_indian_calendar_day() -> None:
    start, end = day_window(datetime(2026, 10, 3, 20, 0, tzinfo=UTC))  # 01:30 IST on 4 Oct
    assert start == datetime(2026, 10, 4, tzinfo=IST)
    assert end - start == timedelta(days=1)


def test_three_per_user_then_blocked_until_midnight(db: Database) -> None:
    limits = UploadsConfig()
    for _ in range(3):
        check_upload_allowed(db, limits, "u1", T0)
        db.record_upload("u1", "doc", T0)
    with pytest.raises(UploadBlocked) as err:
        check_upload_allowed(db, limits, "u1", T0)
    assert (err.value.code, err.value.limit) == ("quota_exceeded", 3)
    assert err.value.resets_at == datetime(2026, 10, 4, tzinfo=IST)
    check_upload_allowed(db, limits, "u1", T0 + timedelta(days=1))  # next day is fine


def test_global_limit_of_ten(db: Database) -> None:
    for i in range(10):
        db.record_upload(f"user{i}", "doc", T0)
    with pytest.raises(UploadBlocked) as err:
        check_upload_allowed(db, UploadsConfig(), "new-user", T0)
    assert (err.value.code, err.value.limit) == ("global_quota_exceeded", 10)


def test_kill_switch_blocks_everyone(db: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPLOADS_ENABLED", "false")
    with pytest.raises(UploadBlocked) as err:
        check_upload_allowed(db, load_settings("dev_light").uploads, "u1", T0)
    assert err.value.code == "uploads_disabled"


# ---------------------------------------------------------------- retention
def test_retention_deletes_only_expired_non_showcase(db: Database, storage: LocalStorage) -> None:
    for doc_id, sha, showcase, age in (
        ("doc_old", "1", False, 31),
        ("doc_new", "2", False, 5),
        ("doc_show", "3", True, 400),
    ):
        db.insert_doc(
            DocRecord(
                doc_id=doc_id,
                sha256=sha * 64,
                is_showcase=showcase,
                created_at=T0 - timedelta(days=age),
            )
        )
        storage.put_bytes(doc_key(doc_id, "report.json"), b"{}")
    db.record_upload("u1", "doc_old", T0 - timedelta(days=31))
    assert sweep(db, storage, 30, now=T0) == ["doc_old"]
    assert not storage.exists("docs/doc_old/report.json")
    assert storage.exists("docs/doc_new/report.json")
    assert storage.exists("docs/doc_show/report.json")
    assert db.count_uploads(T0 - timedelta(days=40), "u1") == 1
