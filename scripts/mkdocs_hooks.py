"""MkDocs hooks: publish ``openapi.json`` and the root project files in the docs site.

The repository-root files (changelog, contributing, security, privacy) stay where GitHub expects
them; ``on_files`` adds them to the site as generated pages so there is one copy of each.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from mkdocs.structure.files import File, Files

# Site page -> file at the repository root.
ROOT_PAGES = {
    "changelog.md": "CHANGELOG.md",
    "contributing.md": "CONTRIBUTING.md",
    "security.md": "SECURITY.md",
    "privacy.md": "PRIVACY.md",
}


def on_files(files: Files, config: Any) -> Files:
    """Add the root project files to the site under their lower-case names."""
    root = Path(config["config_file_path"]).parent
    for page, source in ROOT_PAGES.items():
        content = (root / source).read_text(encoding="utf-8")
        files.append(File.generated(config, page, content=content))
    return files


def on_post_build(config: Any) -> None:
    """Copy the committed OpenAPI document into the built site (single source of truth)."""
    root = Path(config["config_file_path"]).parent
    shutil.copyfile(root / "openapi.json", Path(config["site_dir"]) / "openapi.json")
