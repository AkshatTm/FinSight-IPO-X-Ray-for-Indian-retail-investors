"""The Phase 2 markers exist and the fast test task skips them (B11 §4, B_EXECUTION_PLAN fix 37)."""

from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _config() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_local_and_postgres_markers_are_registered() -> None:
    markers = _config()["tool"]["pytest"]["ini_options"]["markers"]
    names = {m.split(":", 1)[0] for m in markers}
    assert {"slow", "local", "postgres"} <= names


def test_fast_task_skips_local_slow_and_postgres() -> None:
    cmd = _config()["tool"]["poe"]["tasks"]["test"]["cmd"]
    for marker in ("slow", "local", "postgres"):
        assert f"not {marker}" in cmd
