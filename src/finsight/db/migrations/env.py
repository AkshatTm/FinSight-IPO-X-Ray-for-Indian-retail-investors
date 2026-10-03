"""Alembic environment: the URL comes from ``finsight.db.migrate.alembic_config``."""

from __future__ import annotations

from alembic import context

from finsight.db.engine import make_engine
from finsight.db.tables import metadata

config = context.config
engine = make_engine(config.get_main_option("sqlalchemy.url") or "")
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
