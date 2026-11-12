"""The bench manifest and the freeze guard (C-ADR-06).

``bench/<v>/manifest.yaml`` names the IPOs, tasks, systems and run settings, pins the red-flag
rules version, and lists ``frozen_files`` with their sha256. Once ``frozen: true``, those files
never change: ``changed_files`` reports any that differ, and ``tests/bench/test_bench_freeze.py``
fails on them. Answers, rating sheets and results are outputs, never frozen inputs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

MANIFEST = "manifest.yaml"
OUTPUT_DIRS = ("answers", "paste", "sheets")  # never frozen


class Manifest(BaseModel):
    """``bench/<v>/manifest.yaml``."""

    version: str
    frozen: bool = False
    frozen_utc: str | None = None
    built_from_git_sha: str = ""
    ipos: list[str]
    slice: str = "bench"
    tasks: dict[str, dict[str, Any]] = Field(default_factory=dict)
    systems: dict[str, dict[str, Any]] = Field(default_factory=dict)
    run_settings: dict[str, Any] = Field(default_factory=dict)
    redflags_version: str = ""
    retrieval: dict[str, Any] = Field(default_factory=dict)
    disclosures: list[str] = Field(default_factory=list)
    frozen_files: dict[str, str] = Field(default_factory=dict)  # path relative to the bench dir
    # Scoring code and configs outside the bench dir, hashed at the freeze. A later change is
    # reported with the results (``scorer_changed_since_freeze``), not blocked.
    scorer_sha256: dict[str, str] = Field(default_factory=dict)  # path relative to the repo


def sha256(path: Path) -> str:
    """Hex sha256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(bench_dir: Path) -> Manifest:
    """Read ``manifest.yaml`` from a bench directory."""
    data = yaml.safe_load((bench_dir / MANIFEST).read_text(encoding="utf-8"))
    return Manifest.model_validate(data)


def dump(manifest: Manifest, bench_dir: Path) -> None:
    """Write ``manifest.yaml`` (block style, keys in model order)."""
    text = yaml.safe_dump(
        manifest.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=100
    )
    (bench_dir / MANIFEST).write_text(text, encoding="utf-8", newline="\n")


def input_files(bench_dir: Path) -> list[str]:
    """Every file of the bench that is an input (all but the manifest and output folders)."""
    out = []
    for p in sorted(bench_dir.rglob("*")):
        rel = p.relative_to(bench_dir).as_posix()
        if p.is_file() and rel != MANIFEST and rel.split("/", 1)[0] not in OUTPUT_DIRS:
            out.append(rel)
    return out


def hashes(bench_dir: Path, files: list[str]) -> dict[str, str]:
    """``{relative path: sha256}`` for ``files``."""
    return {rel: sha256(bench_dir / rel) for rel in files}


def changed_files(bench_dir: Path, manifest: Manifest) -> list[str]:
    """Frozen files that are missing or whose bytes differ from the recorded hash."""
    bad = []
    for rel, digest in manifest.frozen_files.items():
        path = bench_dir / rel
        if not path.is_file() or sha256(path) != digest:
            bad.append(rel)
    return bad


def unlisted_inputs(bench_dir: Path, manifest: Manifest) -> list[str]:
    """Input files added after the freeze (they would change the bench without a new version)."""
    return [f for f in input_files(bench_dir) if f not in manifest.frozen_files]
