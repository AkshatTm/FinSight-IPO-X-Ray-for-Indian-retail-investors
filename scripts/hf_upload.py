"""Private Hugging Face upload helper for trained artefacts (C03 §2.5).

    uv run python scripts/hf_upload.py --check                       # token works? (never printed)
    uv run python scripts/hf_upload.py --repo finsight-student-4b path/to/adapter_dir [--dry-run]

Only adapters, GGUF and ONNX go up. Merged fp16/bf16 weight files are refused (HF private storage
is limited). The token comes from ``HF_TOKEN`` (env or ``.env``) and is never printed or logged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_SUFFIXES = {".gguf", ".onnx", ".json", ".md", ".txt", ".model", ".yaml", ".yml", ".jinja"}
ADAPTER_NAMES = {"adapter_model.safetensors", "adapter_model.bin", "adapter_config.json"}


class UploadRefused(ValueError):
    """Raised when a file is not an allowed artefact type."""


def check_file(path: Path) -> None:
    """Raise ``UploadRefused`` for merged weights or unknown binary types."""
    name = path.name
    if name in ADAPTER_NAMES:
        return
    suffix = path.suffix.lower()
    if suffix in (".safetensors", ".bin", ".pt", ".pth", ".ckpt"):
        raise UploadRefused(
            f"{path}: merged/full weights are never uploaded (adapters, GGUF, ONNX only)"
        )
    if suffix not in ALLOWED_SUFFIXES:
        raise UploadRefused(f"{path}: file type {suffix or '(none)'} not allowed")


def collect(paths: list[Path]) -> list[Path]:
    """Expand directories to files and validate each one."""
    files: list[Path] = []
    for p in paths:
        files.extend(sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p])
    for f in files:
        check_file(f)
    return files


def load_token() -> str | None:
    """``HF_TOKEN`` from the environment, else from ``.env`` (value never printed)."""
    tok = os.environ.get("HF_TOKEN")
    if tok:
        return tok
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].split("#")[0].strip().strip('"') or None
    return None


def repo_id(name: str) -> str:
    """``<HF_USER>/<name>`` unless ``name`` already has an owner."""
    if "/" in name:
        return name
    return f"{os.environ.get('HF_USER', 'AkshatTm')}/{name}"


def upload(
    files: list[Path], base: Path, repo: str, client: Any, dry_run: bool = False
) -> list[str]:
    """Create a private repo and upload files; returns the repo-relative names (dry run: no calls)."""
    names = [
        str(f.relative_to(base)).replace("\\", "/") if base in f.parents else f.name for f in files
    ]
    if dry_run:
        return names
    client.create_repo(repo, private=True, exist_ok=True)
    for f, n in zip(files, names, strict=True):
        client.upload_file(path_or_fileobj=str(f), path_in_repo=n, repo_id=repo)
    return names


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--repo")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    token = load_token()
    if a.check:
        if not token:
            print("HF_TOKEN not set (env or .env)")
            return 1
        from huggingface_hub import HfApi

        who = HfApi(token=token).whoami()
        print(f"HF token OK for user {who.get('name')}")
        return 0
    if not a.repo or not a.paths:
        ap.error("need --repo and at least one path")
    files = collect(a.paths)
    base = a.paths[0] if a.paths[0].is_dir() else a.paths[0].parent
    client = None
    if not a.dry_run:
        if not token:
            print("HF_TOKEN not set")
            return 1
        from huggingface_hub import HfApi

        client = HfApi(token=token)
    names = upload(files, base, repo_id(a.repo), client, dry_run=a.dry_run)
    print(
        json.dumps(
            {"repo": repo_id(a.repo), "private": True, "files": names, "dry_run": a.dry_run},
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
