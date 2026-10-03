"""Engines for SQLite (laptop, tests) and Postgres through the Supabase pooler (B02 §9)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.pool import NullPool

from finsight.core.config import Settings


def normalise_url(url: str) -> str:
    """Use the psycopg 3 driver for ``postgres://`` and ``postgresql://`` URLs."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def make_engine(url: str) -> sa.Engine:
    """An engine for ``url``.

    Postgres goes through the Supavisor pooler in transaction mode (port 6543), which cannot
    keep prepared statements between transactions, so psycopg's automatic preparation is off
    and SQLAlchemy keeps no pool of its own (the pooler is the pool).
    """
    url = normalise_url(url)
    if url.startswith("postgresql"):
        return sa.create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}  # API threads + the inline worker
    engine = sa.create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @sa.event.listens_for(engine, "connect")
        def _pragmas(conn: Any, _: Any) -> None:  # pragma: no cover - trivial
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def url_from_settings(settings: Settings) -> str:
    cfg = settings.db
    if cfg.backend == "postgres":
        if not cfg.url:
            raise ValueError("db.backend is postgres but FINSIGHT_DB__URL is not set")
        return cfg.url
    path = cfg.sqlite_path if cfg.sqlite_path.is_absolute() else settings.root / cfg.sqlite_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"
