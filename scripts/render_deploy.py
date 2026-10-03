"""Fill the ``${NAME}`` placeholders in ``deploy/gcp/`` and write ready-to-apply files (B3.3a).

    uv run python scripts/render_deploy.py --set IMAGE_TAG=v1 [--out dist/deploy]

Values come from ``--set NAME=value`` or the environment. Every placeholder must have a value:
the script lists the missing names and writes nothing otherwise. The rendered files are for
``gcloud run services|jobs replace`` (docs/runbooks/DEPLOY_RUNBOOK.md); they hold no secrets,
since secrets are Secret Manager references. ``dist/`` is git-ignored.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deploy" / "gcp"
PLACEHOLDER = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
# Every name a template may use; tests/deploy keeps the templates to this list.
NAMES = (
    "GCP_PROJECT",
    "GCP_REGION",
    "IMAGE_TAG",
    "FINSIGHT_BUCKET",
    "SUPABASE_URL",
    "VERCEL_HOST",
)


def templates(source: Path = SOURCE) -> list[Path]:
    return sorted(p for p in source.iterdir() if p.suffix in {".yaml", ".json"})


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text))


def render(text: str, values: Mapping[str, str]) -> str:
    missing = sorted(placeholders(text) - set(values))
    if missing:
        raise KeyError(", ".join(missing))
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="render_deploy.py")
    p.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument("--out", type=Path, default=ROOT / "dist" / "deploy")
    args = p.parse_args(argv)
    values = {k: v for k, v in os.environ.items() if k in NAMES and v}
    values.setdefault("GCP_REGION", "asia-southeast1")
    for item in args.set:
        name, _, value = item.partition("=")
        values[name] = value
    files = templates()
    needed = set().union(*(placeholders(f.read_text(encoding="utf-8")) for f in files))
    missing = sorted(needed - set(values))
    if missing:
        print("missing values: " + ", ".join(missing), file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    for f in files:
        (args.out / f.name).write_text(render(f.read_text(encoding="utf-8"), values), "utf-8")
        print(f"wrote {args.out / f.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
