"""MkDocs hooks: publish ``openapi.json`` next to the site so the Redoc page can load it."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def on_post_build(config: Any) -> None:
    """Copy the committed OpenAPI document into the built site (single source of truth)."""
    root = Path(config["config_file_path"]).parent
    shutil.copyfile(root / "openapi.json", Path(config["site_dir"]) / "openapi.json")
