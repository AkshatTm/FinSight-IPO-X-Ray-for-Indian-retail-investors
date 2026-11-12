"""Phase 2 tables: users, docs, jobs, job_events, uploads, simplify_queue, traces, demo_cache.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    """Create users, docs, jobs, job events, uploads, the simplify queue, traces, demo cache."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_table(
        "docs",
        sa.Column("doc_id", sa.String(40), primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("doc_type", sa.String(16), nullable=True),
        sa.Column("company", sa.String(300), nullable=True),
        sa.Column("pages", sa.Integer, nullable=True),
        sa.Column("uploaded_by", sa.String(64), nullable=True),
        sa.Column("is_showcase", sa.Boolean, nullable=False),
        sa.Column("companion_of", sa.String(40), nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("rejection", sa.String(32), nullable=True),
    )
    op.create_table(
        "jobs",
        sa.Column("job_id", sa.String(40), primary_key=True),
        sa.Column("doc_id", sa.String(40), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("progress", sa.JSON, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("started_at", TS, nullable=True),
        sa.Column("finished_at", TS, nullable=True),
    )
    op.create_index("ix_jobs_doc_id", "jobs", ["doc_id"])
    op.create_table(
        "job_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(40), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("ts", TS, nullable=False),
        sa.UniqueConstraint("job_id", "seq", name="uq_job_events_job_seq"),
    )
    op.create_table(
        "uploads",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("doc_id", sa.String(40), nullable=False),
        sa.Column("ts", TS, nullable=False),
    )
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"])
    op.create_index("ix_uploads_ts", "uploads", ["ts"])
    op.create_table(
        "simplify_queue",
        sa.Column("doc_id", sa.String(40), primary_key=True),
        sa.Column("rid", sa.String(64), primary_key=True),
        sa.Column("priority", sa.Float, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("enqueued_at", TS, nullable=False),
    )
    op.create_table(
        "traces",
        sa.Column("trace_id", sa.String(40), primary_key=True),
        sa.Column("doc_id", sa.String(40), nullable=True),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_table(
        "demo_cache",
        sa.Column("key", sa.String(200), primary_key=True),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )


def downgrade() -> None:
    """Drop every table this migration created."""
    for table in (
        "demo_cache",
        "traces",
        "simplify_queue",
        "uploads",
        "job_events",
        "jobs",
        "docs",
        "users",
    ):
        op.drop_table(table)
