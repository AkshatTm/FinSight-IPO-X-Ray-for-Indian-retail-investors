"""SQLAlchemy Core tables (B02 §9). The Alembic migrations in ``migrations/`` mirror these;
``tests/db/test_migrations.py`` fails if they drift apart.
"""

from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()
TS = sa.DateTime(timezone=True)

users = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),  # Supabase user id ("local-dev" offline)
    sa.Column("email", sa.String(320), nullable=True),
    sa.Column("created_at", TS, nullable=False),
)

docs = sa.Table(
    "docs",
    metadata,
    sa.Column("doc_id", sa.String(40), primary_key=True),
    sa.Column("sha256", sa.String(64), nullable=False, unique=True),
    sa.Column("doc_type", sa.String(16), nullable=True),
    sa.Column("company", sa.String(300), nullable=True),
    sa.Column("pages", sa.Integer, nullable=True),
    sa.Column("uploaded_by", sa.String(64), nullable=True),
    sa.Column("is_showcase", sa.Boolean, nullable=False, default=False),
    sa.Column("companion_of", sa.String(40), nullable=True),
    sa.Column("created_at", TS, nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("rejection", sa.String(32), nullable=True),
)

jobs = sa.Table(
    "jobs",
    metadata,
    sa.Column("job_id", sa.String(40), primary_key=True),
    sa.Column("doc_id", sa.String(40), nullable=False, index=True),
    sa.Column("stage", sa.String(32), nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("progress", sa.JSON, nullable=False),
    sa.Column("error", sa.Text, nullable=True),
    sa.Column("created_at", TS, nullable=False),
    sa.Column("started_at", TS, nullable=True),
    sa.Column("finished_at", TS, nullable=True),
)

job_events = sa.Table(
    "job_events",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("job_id", sa.String(40), nullable=False),
    sa.Column("seq", sa.Integer, nullable=False),
    sa.Column("event", sa.String(32), nullable=False),
    sa.Column("data", sa.JSON, nullable=False),
    sa.Column("ts", TS, nullable=False),
    sa.UniqueConstraint("job_id", "seq", name="uq_job_events_job_seq"),
)

# One row per accepted upload start; kept after retention so the daily quotas stay honest.
uploads = sa.Table(
    "uploads",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("user_id", sa.String(64), nullable=False, index=True),
    sa.Column("doc_id", sa.String(40), nullable=False),
    sa.Column("ts", TS, nullable=False, index=True),
)

# Simplification priority queue (B02 §3.1): lower priority value = sooner.
simplify_queue = sa.Table(
    "simplify_queue",
    metadata,
    sa.Column("doc_id", sa.String(40), primary_key=True),
    sa.Column("rid", sa.String(64), primary_key=True),
    sa.Column("priority", sa.Float, nullable=False),
    sa.Column("status", sa.String(16), nullable=False),  # queued | running | done | failed
    sa.Column("enqueued_at", TS, nullable=False),
)

traces = sa.Table(
    "traces",
    metadata,
    sa.Column("trace_id", sa.String(40), primary_key=True),
    sa.Column("doc_id", sa.String(40), nullable=True),
    sa.Column("payload", sa.JSON, nullable=False),
    sa.Column("created_at", TS, nullable=False),
)

demo_cache = sa.Table(
    "demo_cache",
    metadata,
    sa.Column("key", sa.String(200), primary_key=True),
    sa.Column("payload", sa.JSON, nullable=False),
    sa.Column("created_at", TS, nullable=False),
)
