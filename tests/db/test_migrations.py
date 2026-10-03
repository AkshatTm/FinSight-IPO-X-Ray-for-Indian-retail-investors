"""B1.2: the Alembic migrations build exactly the tables in ``finsight.db.tables``."""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from finsight.core.config import DbConfig, load_settings
from finsight.db import metadata, normalise_url, upgrade, url_from_settings


def test_migrations_match_the_tables(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    upgrade(url)
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), metadata)
    assert diff == []


def test_postgres_urls_use_psycopg3() -> None:
    assert normalise_url("postgres://u@h:6543/db") == "postgresql+psycopg://u@h:6543/db"
    assert normalise_url("postgresql://u@h/db") == "postgresql+psycopg://u@h/db"
    assert normalise_url("sqlite:///x.db") == "sqlite:///x.db"


def test_postgres_backend_needs_the_env_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FINSIGHT_DB__URL", raising=False)
    with pytest.raises(ValueError, match="DB__URL"):
        url_from_settings(
            load_settings("full").model_copy(update={"db": DbConfig(backend="postgres")})
        )


@pytest.mark.postgres
def test_migrations_match_the_tables_on_postgres() -> None:
    import os

    url = os.environ.get("FINSIGHT_TEST_PG_URL")
    if not url:
        pytest.skip("FINSIGHT_TEST_PG_URL not set")
    engine = sa.create_engine(normalise_url(url))
    metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version"))
    upgrade(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), metadata)
    metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version"))
    assert diff == []
