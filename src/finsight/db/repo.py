"""``Database``: every read and write the API and the worker make (SQLite or Postgres)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from finsight.core.ids import new_trace_id
from finsight.core.schemas import DocRecord, Job
from finsight.db.engine import make_engine
from finsight.db.tables import (
    docs,
    job_events,
    jobs,
    metadata,
    simplify_queue,
    uploads,
    users,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite drops the timezone; every stored time is UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@dataclass(frozen=True)
class StoredEvent:
    """One row of ``job_events``: what the SSE stream sends, in ``seq`` order."""

    seq: int
    event: str
    data: dict[str, Any]
    ts: datetime


class Database:
    """Repository over the Core tables. Each method is one short transaction."""

    def __init__(self, url: str, engine: sa.Engine | None = None) -> None:
        self.url = url
        self.engine = engine or make_engine(url)

    def create_all(self) -> None:
        """Create missing tables (tests and the laptop; cloud databases use Alembic)."""
        metadata.create_all(self.engine)

    # ------------------------------------------------------------------ users
    def upsert_user(self, user_id: str, email: str | None, now: datetime | None = None) -> None:
        with self.engine.begin() as conn:
            row = conn.execute(sa.select(users.c.id).where(users.c.id == user_id)).first()
            if row is None:
                conn.execute(
                    users.insert().values(id=user_id, email=email, created_at=now or utcnow())
                )
            elif email:
                conn.execute(users.update().where(users.c.id == user_id).values(email=email))

    # ------------------------------------------------------------------ docs
    def insert_doc(self, doc: DocRecord) -> None:
        with self.engine.begin() as conn:
            conn.execute(docs.insert().values(**doc.model_dump()))

    def get_doc(self, doc_id: str) -> DocRecord | None:
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(docs).where(docs.c.doc_id == doc_id)).mappings().first()
        return self._doc(row) if row else None

    def doc_by_sha(self, sha256: str) -> DocRecord | None:
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(docs).where(docs.c.sha256 == sha256)).mappings().first()
        return self._doc(row) if row else None

    def update_doc(self, doc_id: str, **values: Any) -> None:
        with self.engine.begin() as conn:
            conn.execute(docs.update().where(docs.c.doc_id == doc_id).values(**values))

    def docs_by_user(self, user_id: str) -> list[DocRecord]:
        query = (
            sa.select(docs).where(docs.c.uploaded_by == user_id).order_by(docs.c.created_at.desc())
        )
        with self.engine.connect() as conn:
            return [self._doc(row) for row in conn.execute(query).mappings()]

    def expired_docs(self, before: datetime) -> list[str]:
        """Non-showcase documents created before ``before`` (the retention sweep)."""
        query = sa.select(docs.c.doc_id).where(
            docs.c.created_at < before, docs.c.is_showcase.is_(False)
        )
        with self.engine.connect() as conn:
            return [row.doc_id for row in conn.execute(query)]

    def delete_doc_rows(self, doc_id: str) -> None:
        """Delete a document's rows except ``uploads`` (quota counts survive retention)."""
        with self.engine.begin() as conn:
            job_ids = sa.select(jobs.c.job_id).where(jobs.c.doc_id == doc_id)
            conn.execute(job_events.delete().where(job_events.c.job_id.in_(job_ids)))
            conn.execute(jobs.delete().where(jobs.c.doc_id == doc_id))
            conn.execute(simplify_queue.delete().where(simplify_queue.c.doc_id == doc_id))
            conn.execute(docs.delete().where(docs.c.doc_id == doc_id))

    @staticmethod
    def _doc(row: Any) -> DocRecord:
        values = dict(row)
        values["created_at"] = _aware(values["created_at"])
        return DocRecord.model_validate(values)

    # ------------------------------------------------------------------ uploads (quotas)
    def record_upload(self, user_id: str, doc_id: str, ts: datetime | None = None) -> None:
        with self.engine.begin() as conn:
            conn.execute(uploads.insert().values(user_id=user_id, doc_id=doc_id, ts=ts or utcnow()))

    def count_uploads(self, since: datetime, user_id: str | None = None) -> int:
        query = sa.select(sa.func.count()).select_from(uploads).where(uploads.c.ts >= since)
        if user_id is not None:
            query = query.where(uploads.c.user_id == user_id)
        with self.engine.connect() as conn:
            return int(conn.execute(query).scalar_one())

    # ------------------------------------------------------------------ jobs
    def create_job(self, doc_id: str, now: datetime | None = None) -> Job:
        job = Job(job_id=new_trace_id(), doc_id=doc_id, stage="received", status="queued")
        with self.engine.begin() as conn:
            conn.execute(jobs.insert().values(**job.model_dump(), created_at=now or utcnow()))
        return job

    def get_job(self, job_id: str) -> Job | None:
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(jobs).where(jobs.c.job_id == job_id)).mappings().first()
        return self._job(row) if row else None

    def latest_job(self, doc_id: str) -> Job | None:
        query = (
            sa.select(jobs)
            .where(jobs.c.doc_id == doc_id)
            .order_by(jobs.c.created_at.desc(), jobs.c.job_id.desc())
            .limit(1)
        )
        with self.engine.connect() as conn:
            row = conn.execute(query).mappings().first()
        return self._job(row) if row else None

    def update_job(self, job_id: str, **values: Any) -> None:
        with self.engine.begin() as conn:
            conn.execute(jobs.update().where(jobs.c.job_id == job_id).values(**values))

    @staticmethod
    def _job(row: Any) -> Job:
        values = {k: v for k, v in dict(row).items() if k != "created_at"}
        for key in ("started_at", "finished_at"):
            values[key] = _aware(values[key])
        return Job.model_validate(values)

    # ------------------------------------------------------------------ events
    def append_event(self, job_id: str, event: str, data: dict[str, Any]) -> int:
        """Append an event and return its ``seq`` (1, 2, 3, … per job)."""
        for _ in range(5):  # a concurrent writer took the same seq: read again and retry
            try:
                with self.engine.begin() as conn:
                    last: int | None = conn.execute(
                        sa.select(sa.func.max(job_events.c.seq)).where(
                            job_events.c.job_id == job_id
                        )
                    ).scalar_one()
                    seq = int(last or 0) + 1
                    conn.execute(
                        job_events.insert().values(
                            job_id=job_id, seq=seq, event=event, data=data, ts=utcnow()
                        )
                    )
                return seq
            except IntegrityError:
                continue
        raise RuntimeError(f"could not append an event to job {job_id}")

    def events_after(self, job_id: str, after_seq: int = 0) -> list[StoredEvent]:
        query = (
            sa.select(job_events)
            .where(job_events.c.job_id == job_id, job_events.c.seq > after_seq)
            .order_by(job_events.c.seq)
        )
        with self.engine.connect() as conn:
            return [
                StoredEvent(row.seq, row.event, dict(row.data), _aware(row.ts) or utcnow())
                for row in conn.execute(query)
            ]

    # ------------------------------------------------------------------ simplification queue
    def enqueue(self, doc_id: str, rids: Iterable[str], start: float = 0.0) -> None:
        """Queue risks in the given order (already-queued risks keep their place)."""
        now = utcnow()
        with self.engine.begin() as conn:
            existing = {
                row.rid
                for row in conn.execute(
                    sa.select(simplify_queue.c.rid).where(simplify_queue.c.doc_id == doc_id)
                )
            }
            rows = [
                {
                    "doc_id": doc_id,
                    "rid": rid,
                    "priority": start + i,
                    "status": "queued",
                    "enqueued_at": now,
                }
                for i, rid in enumerate(rids)
                if rid not in existing
            ]
            if rows:
                conn.execute(simplify_queue.insert(), rows)

    def bump(self, doc_id: str, rid: str) -> int:
        """Move a risk to the front (adding it if needed); return its 0-based queue position."""
        with self.engine.begin() as conn:
            lowest: float | None = conn.execute(
                sa.select(sa.func.min(simplify_queue.c.priority)).where(
                    simplify_queue.c.doc_id == doc_id, simplify_queue.c.status == "queued"
                )
            ).scalar_one()
            front = (float(lowest) if lowest is not None else 0.0) - 1.0
            current = conn.execute(
                sa.select(simplify_queue.c.status).where(
                    simplify_queue.c.doc_id == doc_id, simplify_queue.c.rid == rid
                )
            ).first()
            if current is None:
                conn.execute(
                    simplify_queue.insert().values(
                        doc_id=doc_id,
                        rid=rid,
                        priority=front,
                        status="queued",
                        enqueued_at=utcnow(),
                    )
                )
            elif current.status == "queued":
                conn.execute(
                    simplify_queue.update()
                    .where(simplify_queue.c.doc_id == doc_id, simplify_queue.c.rid == rid)
                    .values(priority=front)
                )
        return self.queue_position(doc_id, rid)

    def queue(self, doc_id: str) -> list[str]:
        """Queued risk ids, front first."""
        query = (
            sa.select(simplify_queue.c.rid)
            .where(simplify_queue.c.doc_id == doc_id, simplify_queue.c.status == "queued")
            .order_by(simplify_queue.c.priority, simplify_queue.c.enqueued_at)
        )
        with self.engine.connect() as conn:
            return [row.rid for row in conn.execute(query)]

    def queue_position(self, doc_id: str, rid: str) -> int:
        order = self.queue(doc_id)
        return order.index(rid) if rid in order else -1

    def take_next(self, doc_id: str) -> str | None:
        """Mark the front risk ``running`` and return it (``None`` when the queue is empty)."""
        with self.engine.begin() as conn:
            row = conn.execute(
                sa.select(simplify_queue.c.rid)
                .where(simplify_queue.c.doc_id == doc_id, simplify_queue.c.status == "queued")
                .order_by(simplify_queue.c.priority, simplify_queue.c.enqueued_at)
                .limit(1)
            ).first()
            if row is None:
                return None
            conn.execute(
                simplify_queue.update()
                .where(simplify_queue.c.doc_id == doc_id, simplify_queue.c.rid == row.rid)
                .values(status="running")
            )
            return str(row.rid)

    def finish_item(self, doc_id: str, rid: str, status: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                simplify_queue.update()
                .where(simplify_queue.c.doc_id == doc_id, simplify_queue.c.rid == rid)
                .values(status=status)
            )
