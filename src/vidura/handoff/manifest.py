"""Pack manifest: size, sha256 and where each data file lives (git or the private HF repo).

Files up to 4.5 MB are committed; larger ones go to the private HF dataset repo (C-ADR-13) and are
listed in ``data/.gitignore``. ``MANIFEST.json`` records both kinds so ARGON can verify a download.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GIT_LIMIT_BYTES = 4_500_000  # margin under the 5 MB commit hook (CLAUDE.md: nothing over 5 MB)


def sha256_file(path: Path) -> str:
    """Hex sha256 of a file, read in chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    data_dir: Path, hf_repo: str, hf_prefix: str, hf_revision: str | None
) -> dict[str, Any]:
    """Describe every file under ``data_dir`` and write ``data_dir/.gitignore`` for HF files."""
    files: list[dict[str, Any]] = []
    ignore: list[str] = []
    for path in sorted(
        p
        for p in data_dir.rglob("*")
        if p.is_file() and p.name not in (".gitignore", "MANIFEST.json")
    ):
        rel = path.relative_to(data_dir).as_posix()
        size = path.stat().st_size
        where = "git" if size <= GIT_LIMIT_BYTES else "hf"
        row: dict[str, Any] = {
            "path": rel,
            "bytes": size,
            "sha256": sha256_file(path),
            "where": where,
        }
        if where == "hf":
            row["hf"] = {
                "repo": hf_repo,
                "type": "dataset",
                "path": f"{hf_prefix}/{rel}",
                "revision": hf_revision,
            }
            ignore.append(rel)
        files.append(row)
    (data_dir / ".gitignore").write_text(
        "# files over 4.5 MB live in the private HF dataset repo (see MANIFEST.json)\n"
        + "".join(f"/{rel}\n" for rel in ignore),
        encoding="utf-8",
        newline="\n",
    )
    return {"hf_repo": hf_repo, "hf_prefix": hf_prefix, "hf_revision": hf_revision, "files": files}


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Write ``MANIFEST.json`` (sorted keys, LF)."""
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
