"""Run the Alembic migrations from code: ``python -m finsight.db.migrate`` (uses the profile)."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from finsight.db.engine import normalise_url

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def alembic_config(url: str) -> Config:
    """An Alembic config pointing at the bundled migrations and ``url``."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.set_main_option("sqlalchemy.url", normalise_url(url).replace("%", "%%"))
    return config


def upgrade(url: str, revision: str = "head") -> None:
    """Migrate the database at ``url`` to ``revision`` (default: the latest)."""
    command.upgrade(alembic_config(url), revision)


if __name__ == "__main__":  # pragma: no cover
    from finsight.core.config import get_settings
    from finsight.db.engine import url_from_settings

    upgrade(url_from_settings(get_settings()))
    print("database is at the latest migration")
