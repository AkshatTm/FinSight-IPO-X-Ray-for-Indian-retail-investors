"""B1.2: repository behaviour on SQLite (and Postgres in the CI service job)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from finsight.core.schemas import DocRecord
from finsight.db import Database

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def _doc(doc_id: str = "doc_a", sha: str = "a" * 64, **kw: object) -> DocRecord:
    return DocRecord(doc_id=doc_id, sha256=sha, created_at=T0, **kw)  # type: ignore[arg-type]


def test_doc_round_trip_and_update(db: Database) -> None:
    db.insert_doc(_doc(uploaded_by="u1"))
    db.update_doc("doc_a", doc_type="drhp", pages=420, company="Acme Limited")
    doc = db.get_doc("doc_a")
    assert doc is not None
    assert (doc.doc_type, doc.pages, doc.company) == ("drhp", 420, "Acme Limited")
    assert doc.created_at == T0
    assert db.doc_by_sha("a" * 64) == doc
    assert db.get_doc("missing") is None
    assert [d.doc_id for d in db.docs_by_user("u1")] == ["doc_a"]


def test_sha256_is_unique(db: Database) -> None:
    db.insert_doc(_doc())
    with pytest.raises(IntegrityError):
        db.insert_doc(_doc(doc_id="doc_b"))


def test_events_get_increasing_seq_and_replay_from_any_point(db: Database) -> None:
    job = db.create_job("doc_a")
    seqs = [db.append_event(job.job_id, "stage", {"stage": s, "status": "end"}) for s in "abcd"]
    assert seqs == [1, 2, 3, 4]
    assert [e.seq for e in db.events_after(job.job_id)] == [1, 2, 3, 4]
    assert [e.data["stage"] for e in db.events_after(job.job_id, 2)] == ["c", "d"]
    assert db.events_after(job.job_id, 4) == []
    other = db.create_job("doc_b")
    assert db.append_event(other.job_id, "stage", {}) == 1


def test_job_update_and_latest(db: Database) -> None:
    first = db.create_job("doc_a", now=T0)
    second = db.create_job("doc_a", now=T0 + timedelta(minutes=1))
    db.update_job(second.job_id, status="running", stage="parsed", started_at=T0, progress={"x": 1})
    latest = db.latest_job("doc_a")
    assert latest is not None
    assert latest.job_id == second.job_id
    assert (latest.status, latest.stage, latest.progress, latest.started_at) == (
        "running",
        "parsed",
        {"x": 1},
        T0,
    )
    assert db.get_job(first.job_id) is not None


def test_upload_counts_per_user_and_global(db: Database) -> None:
    for user, minutes in (("u1", 0), ("u1", 5), ("u2", 10)):
        db.record_upload(user, "doc", ts=T0 + timedelta(minutes=minutes))
    db.record_upload("u1", "doc", ts=T0 - timedelta(days=1))
    assert db.count_uploads(T0, "u1") == 2
    assert db.count_uploads(T0) == 3


def test_priority_queue_order_bump_and_take(db: Database) -> None:
    db.enqueue("doc_a", ["r1", "r2", "r3"])
    assert db.queue("doc_a") == ["r1", "r2", "r3"]
    assert db.bump("doc_a", "r3") == 0
    assert db.queue("doc_a") == ["r3", "r1", "r2"]
    assert db.bump("doc_a", "r9") == 0  # a click on a risk outside the top 15 adds it at the front
    assert db.queue("doc_a") == ["r9", "r3", "r1", "r2"]
    db.enqueue("doc_a", ["r1", "r4"])  # already-queued risks keep their place
    assert db.queue("doc_a")[-1] == "r4"
    assert db.take_next("doc_a") == "r9"
    db.finish_item("doc_a", "r9", "done")
    assert db.bump("doc_a", "r9") == -1  # a finished risk is not queued again
    assert db.queue("doc_a") == ["r3", "r1", "r2", "r4"]


def test_retention_rows_keep_upload_counts(db: Database) -> None:
    db.insert_doc(_doc("doc_old", "1" * 64))
    db.insert_doc(_doc("doc_show", "2" * 64, is_showcase=True))
    job = db.create_job("doc_old")
    db.append_event(job.job_id, "stage", {})
    db.enqueue("doc_old", ["r1"])
    db.record_upload("u1", "doc_old", ts=T0)
    assert db.expired_docs(T0 + timedelta(days=31)) == ["doc_old"]
    db.delete_doc_rows("doc_old")
    assert db.get_doc("doc_old") is None
    assert db.events_after(job.job_id) == []
    assert db.queue("doc_old") == []
    assert db.count_uploads(T0, "u1") == 1


def test_users_upsert(db: Database) -> None:
    db.upsert_user("u1", None)
    db.upsert_user("u1", "a@example.com")
    db.upsert_user("u1", None)


def test_a_non_utc_filter_is_compared_as_the_same_instant(db: Database) -> None:
    """IST midnight is 18:30 UTC the day before; SQLite must not read it as 00:00 UTC."""
    ist = timezone(timedelta(hours=5, minutes=30))
    db.record_upload("u1", "doc", ts=datetime(2026, 10, 3, 18, 45, tzinfo=UTC))
    assert db.count_uploads(datetime(2026, 10, 4, 0, 0, tzinfo=ist), "u1") == 1
    assert db.count_uploads(datetime(2026, 10, 4, 0, 30, tzinfo=ist), "u1") == 0
