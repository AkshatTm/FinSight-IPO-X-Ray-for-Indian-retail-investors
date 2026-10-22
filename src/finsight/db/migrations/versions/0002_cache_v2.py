"""Cache v2 (CC-04): pipeline version, models fingerprint, analysis status on ``docs``.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the cache-key parts and the complete / degraded / failed status."""
    op.add_column("docs", sa.Column("pipeline_version", sa.String(32), nullable=True))
    op.add_column("docs", sa.Column("fingerprint", sa.String(64), nullable=True))
    op.add_column("docs", sa.Column("analysis_status", sa.String(16), nullable=True))
    for name in ("degraded_reasons", "skipped_models"):
        op.add_column("docs", sa.Column(name, sa.JSON, nullable=False, server_default="[]"))


def downgrade() -> None:
    """Drop the cache v2 columns."""
    for name in (
        "skipped_models", "degraded_reasons", "analysis_status", "fingerprint", "pipeline_version"
    ):  # fmt: skip
        op.drop_column("docs", name)
