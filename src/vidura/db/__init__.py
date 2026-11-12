"""Database: SQLAlchemy Core tables, a repository and Alembic migrations (SQLite or Postgres)."""

from __future__ import annotations

from vidura.core.config import Settings
from vidura.db.engine import make_engine, normalise_url, url_from_settings
from vidura.db.migrate import upgrade
from vidura.db.repo import Database, StoredEvent, utcnow
from vidura.db.tables import metadata


def make_database(settings: Settings, create: bool = True) -> Database:
    """The profile's database; SQLite tables are created on first use (Postgres uses Alembic)."""
    db = Database(url_from_settings(settings))
    if create and settings.db.backend == "sqlite":
        db.create_all()
    return db


__all__ = [
    "Database",
    "StoredEvent",
    "make_database",
    "make_engine",
    "metadata",
    "normalise_url",
    "upgrade",
    "url_from_settings",
    "utcnow",
]
