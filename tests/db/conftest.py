"""A fresh database per test: SQLite always; Postgres too when ``FINSIGHT_TEST_PG_URL`` is set
(the CI service job runs ``pytest -m postgres``)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa

from finsight.db import Database, metadata

PG_URL = os.environ.get("FINSIGHT_TEST_PG_URL")


@pytest.fixture(
    params=[
        "sqlite",
        pytest.param("postgres", marks=pytest.mark.postgres),
    ]
)
def db(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Database]:
    if request.param == "sqlite":
        database = Database(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
        database.create_all()
        yield database
        return
    if not PG_URL:
        pytest.skip("FINSIGHT_TEST_PG_URL not set")
    database = Database(PG_URL)
    metadata.drop_all(database.engine)
    with database.engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version"))
    database.create_all()
    yield database
    metadata.drop_all(database.engine)
