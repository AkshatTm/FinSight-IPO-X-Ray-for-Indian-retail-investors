"""Alembic environment: the URL comes from ``vidura.db.migrate.alembic_config``."""

from __future__ import annotations

from alembic import context

from vidura.db.engine import make_engine
from vidura.db.tables import metadata

config = context.config
engine = make_engine(config.get_main_option("sqlalchemy.url") or "")
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
