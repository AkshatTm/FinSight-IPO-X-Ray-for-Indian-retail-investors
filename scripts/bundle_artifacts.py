"""Collect everything the deployed API reads into one folder (P6.1, ADR-022).

    uv run python scripts/bundle_artifacts.py [--out dist/space] [--no-pages] [--dense]

The Space gets the built outputs of the demo IPOs, never the source PDFs or model weights:

- ``data/processed/<ipo>/``: xray.json, parsed*.json, sections*.json, index/ (BM25 chunks), and
  the page images (pages/, pages_prospectus/; ``--no-pages`` leaves them out);
- ``data/demo_cache/`` (recorded real answers), ``data/gold/`` is not copied;
- ``eval_results/*.json`` and ``ladder_table.*`` for the Model Lab;
- ``configs/`` and a ``MANIFEST.json`` listing every file with its size and SHA-256.

The dense index (``index/dense.npy``) is left out because ``deploy_cpu`` retrieves with BM25 only;
``--dense`` adds it. Nothing under ``data/raw`` is touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import yaml

PER_IPO_FILES = (
    "xray.json",
    "parsed.json",
    "parsed_prospectus.json",
    "sections.json",
    "sections_prospectus.json",
)
PAGE_DIRS = ("pages", "pages_prospectus")


def demo_ids(config: Path) -> list[str]:
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    return [row["ipo_id"] for row in data["ipos"]]


def plan(
    root: Path, ids: list[str], *, pages: bool = True, dense: bool = False
) -> list[tuple[Path, Path]]:
    """``(source, path relative to the bundle)`` for every file that goes into the bundle."""
    out: list[tuple[Path, Path]] = []

    def add(base: Path, pattern: str = "*") -> None:
        for src in sorted(p for p in base.rglob(pattern) if p.is_file()):
            out.append((src, src.relative_to(root)))

    for ipo in ids:
        base = root / "data" / "processed" / ipo
        out += [
            (base / n, (base / n).relative_to(root)) for n in PER_IPO_FILES if (base / n).is_file()
        ]
        if (base / "index").is_dir():
            for src in sorted(p for p in (base / "index").iterdir() if p.is_file()):
                if src.name != "dense.npy" or dense:
                    out.append((src, src.relative_to(root)))
        if pages:
            for name in PAGE_DIRS:
                if (base / name).is_dir():
                    add(base / name)
    if (root / "data" / "demo_cache").is_dir():
        add(root / "data" / "demo_cache", "*.json")
    for src in sorted((root / "eval_results").glob("*.json")) + sorted(
        (root / "eval_results").glob("ladder_table.*")
    ):
        out.append((src, src.relative_to(root)))
    if (root / "eval_results" / "ladder").is_dir():
        add(root / "eval_results" / "ladder", "*.json")
    add(root / "configs")
    return list(dict.fromkeys(out))  # ladder_table.json matches both globs


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bundle(root: Path, out: Path, ids: list[str], *, pages: bool, dense: bool) -> dict[str, object]:
    files = plan(root, ids, pages=pages, dense=dense)
    if out.exists():
        shutil.rmtree(out)
    entries = []
    for src, rel in files:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        entries.append({"path": rel.as_posix(), "bytes": dst.stat().st_size, "sha256": sha256(dst)})
    manifest = {
        "ipos": ids,
        "pages": pages,
        "dense": dense,
        "n_files": len(entries),
        "total_bytes": sum(int(e["bytes"]) for e in entries),
        "files": entries,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("dist/space"))
    parser.add_argument("--no-pages", action="store_true")
    parser.add_argument("--dense", action="store_true")
    args = parser.parse_args(argv)
    root = Path.cwd()
    ids = demo_ids(root / "configs" / "demo_ipos.yaml")
    manifest = bundle(root, args.out, ids, pages=not args.no_pages, dense=args.dense)
    print(f"{manifest['n_files']} files, {int(manifest['total_bytes']) / 1e6:.1f} MB -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
