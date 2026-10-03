"""B3.5a: every way a stage can fail, on a stage graph shaped like B02 §3.1.

Only ``validated`` and ``detected`` are real upload stages so far; the later ones are stand-ins
with the B02 dependencies, so the runner's failure rules are pinned before those stages exist.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from finsight.core.config import CostConfig, load_settings
from finsight.core.schemas import DocRecord
from finsight.db import Database
from finsight.jobs import JobContext, Stage, StageRejected, estimate_cost, run_job, upload_stages
from finsight.storage import LocalStorage, doc_key, put_json

T0 = datetime(2026, 10, 3, 6, 0, tzinfo=UTC)

# name -> (requires, critical), in B02 §3.1 order
GRAPH: dict[str, tuple[tuple[str, ...], bool]] = {
    "validated": ((), True),
    "detected": (("validated",), True),
    "parsed": (("detected",), True),
    "sections": (("parsed",), False),
    "facts": (("sections",), False),
    "financials": (("sections",), False),
    "redflags": (("financials",), False),
    "risks_split": (("sections",), False),
    "risks_scored": (("risks_split",), False),
    "risk_level": (("redflags", "risks_scored"), False),
    "index": (("parsed",), False),
    "compare": (("financials",), False),
}


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{(tmp_path / 'f.db').as_posix()}")
    database.create_all()
    return database


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "store")


def _ctx(db: Database, storage: LocalStorage) -> JobContext:
    db.insert_doc(DocRecord(doc_id="doc_f", sha256="f" * 64, created_at=T0))
    return JobContext(
        "doc_f", db.create_job("doc_f").job_id, db, storage, load_settings("dev_light")
    )


def _stages(failing: str | None, error: Exception | None = None) -> list[Stage]:
    def make(name: str):  # type: ignore[no-untyped-def]
        def fn(ctx: JobContext) -> dict[str, object]:
            if name == failing:
                raise error or RuntimeError("boom")
            put_json(ctx.storage, ctx.key(f"{name}.json"), {})
            return {}

        return fn

    return [
        Stage(name, make(name), output=f"{name}.json", requires=req, critical=crit)
        for name, (req, crit) in GRAPH.items()
    ]


def _downstream(name: str) -> set[str]:
    out: set[str] = set()
    for other, (req, _) in GRAPH.items():
        if name in req or out & set(req):
            out.add(other)
    return out


@pytest.mark.parametrize("failing", list(GRAPH))
def test_each_stage_failure_skips_exactly_its_dependents(
    db: Database, storage: LocalStorage, failing: str
) -> None:
    ctx = _ctx(db, storage)
    result = run_job(ctx, _stages(failing))
    critical = GRAPH[failing][1]
    if critical:
        assert result.status == "failed"
        assert result.failed_stages == [failing]
        later = list(GRAPH)[list(GRAPH).index(failing) + 1 :]
        assert not any(storage.exists(doc_key("doc_f", f"{n}.json")) for n in later)
    else:
        assert result.status == "partial"
        assert set(result.failed_stages) == {failing} | _downstream(failing)
        ran = set(GRAPH) - set(result.failed_stages)
        assert all(storage.exists(doc_key("doc_f", f"{n}.json")) for n in ran)
    doc = db.get_doc("doc_f")
    assert doc is not None
    assert doc.status == result.status
    done = db.events_after(ctx.job_id)[-1]
    assert done.event == "done"
    assert done.data == {"status": result.status, "failed_stages": result.failed_stages}


def test_rejection_stops_the_job_with_its_code(db: Database, storage: LocalStorage) -> None:
    ctx = _ctx(db, storage)
    result = run_job(ctx, _stages("validated", StageRejected("password", "encrypted")))
    assert (result.status, result.rejection) == ("failed", "password")
    doc = db.get_doc("doc_f")
    assert doc is not None
    assert (doc.status, doc.rejection) == ("failed", "password")
    failed = [
        e.data
        for e in db.events_after(ctx.job_id)
        if e.event == "stage" and e.data.get("status") == "failed"
    ]
    assert failed == [{"stage": "validated", "status": "failed", "detail": {"reason": "password"}}]
    job = db.get_job(ctx.job_id)
    assert job is not None
    assert (job.status, job.error) == ("failed", "password")


def test_retry_after_a_failure_reruns_only_what_is_missing(
    db: Database, storage: LocalStorage
) -> None:
    ctx = _ctx(db, storage)
    first = run_job(ctx, _stages("financials"))
    assert first.status == "partial"
    retry = JobContext("doc_f", db.create_job("doc_f").job_id, db, storage, ctx.settings)
    second = run_job(retry, _stages(None))
    assert (second.status, second.failed_stages) == ("ready", [])
    cached = {
        e.data["stage"]
        for e in db.events_after(retry.job_id)
        if e.data.get("detail") == {"cached": True}
    }
    assert cached == set(GRAPH) - set(first.failed_stages)


def test_error_messages_never_reach_the_event_stream(db: Database, storage: LocalStorage) -> None:
    ctx = _ctx(db, storage)
    run_job(ctx, _stages("facts", ValueError("secret path /home/x and a token")))
    text = str([e.data for e in db.events_after(ctx.job_id)])
    assert "secret" not in text
    assert "token" not in text


def test_job_records_a_cost_estimate(db: Database, storage: LocalStorage) -> None:
    ctx = _ctx(db, storage)
    run_job(ctx, _stages(None))
    job = db.get_job(ctx.job_id)
    assert job is not None
    cost = job.progress["cost_estimate"]
    assert cost["vcpu_s"] == pytest.approx(cost["wall_s"] * ctx.settings.costs.cpu_vcpu, abs=1e-2)
    assert cost["usd"] is not None


def test_cost_estimate_arithmetic() -> None:
    cfg = CostConfig()
    cpu = estimate_cost(100, cfg)
    assert (cpu["vcpu_s"], cpu["gib_s"], cpu["gpu_s"]) == (400, 800, 0.0)
    assert cpu["usd"] == pytest.approx(400 * 0.000018 + 800 * 0.000002)
    assert estimate_cost(100, cfg, gpu=True)["usd"] is None  # GPU rate not set yet
    assert estimate_cost(-1, cfg)["wall_s"] == 0.0


def test_real_upload_stages_follow_the_b02_graph() -> None:
    stages = upload_stages()
    assert [(s.name, s.critical) for s in stages] == [
        ("validated", True),
        ("detected", True),
        ("parsed", True),
        ("sections", False),
        ("risks_split", False),
    ]
    assert all(s.requires == GRAPH[s.name][0] for s in stages)


def _slow(seconds: float):  # type: ignore[no-untyped-def]
    def fn(ctx: JobContext) -> dict[str, object]:
        threading.Event().wait(seconds)
        return {"finished": True}

    return fn


def test_a_stage_past_its_timeout_fails_and_only_its_dependents_are_skipped(
    db: Database, storage: LocalStorage
) -> None:
    ctx = _ctx(db, storage)
    stages = [
        Stage("risks_split", _slow(5), timeout_s=0.05),
        Stage("risks_scored", _slow(0), requires=("risks_split",)),
        Stage("compare", _slow(0)),
    ]
    result = run_job(ctx, stages)
    assert (result.status, result.failed_stages) == ("partial", ["risks_split", "risks_scored"])
    failed = [e.data for e in db.events_after(ctx.job_id) if e.data.get("status") == "failed"]
    assert failed[0] == {
        "stage": "risks_split",
        "status": "failed",
        "detail": {"error": "StageTimeout"},
    }


def test_a_critical_stage_timeout_from_settings_fails_the_job(
    db: Database, storage: LocalStorage
) -> None:
    ctx = _ctx(db, storage)
    assert ctx.settings.jobs.stage_timeouts_s["parsed"] == 600  # B02 §11: parse ≤ 10 min
    ctx.settings.jobs.stage_timeouts_s["parsed"] = 0.05
    result = run_job(ctx, [Stage("parsed", _slow(5), critical=True), Stage("index", _slow(0))])
    assert (result.status, result.failed_stages) == ("failed", ["parsed"])


def test_a_stage_within_its_timeout_runs_normally_and_errors_still_surface(
    db: Database, storage: LocalStorage
) -> None:
    ctx = _ctx(db, storage)

    def bad(ctx: JobContext) -> dict[str, object]:
        raise StageRejected("password", "encrypted")

    result = run_job(
        ctx, [Stage("facts", _slow(0), timeout_s=5), Stage("validated", bad, timeout_s=5)]
    )
    assert (result.status, result.rejection) == ("failed", "password")
    ends = [e.data for e in db.events_after(ctx.job_id) if e.data.get("status") == "end"]
    assert ends == [{"stage": "facts", "status": "end", "detail": {"finished": True}}]
