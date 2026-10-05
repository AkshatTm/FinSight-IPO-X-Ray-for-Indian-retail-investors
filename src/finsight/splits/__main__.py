"""Split CLI (C1.4).

uv run python -m finsight.splits build              # print counts only (dry run)
uv run python -m finsight.splits build --freeze     # write configs/splits.yaml + manifests
uv run python -m finsight.splits build --freeze --adr C-ADR-NN   # replace a frozen split
uv run python -m finsight.splits check              # leakage check on data/manifests/

Prints counts and ids only, never document text.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from finsight.core.config import get_settings, project_root
from finsight.splits.assign import SplitError, SplitRules
from finsight.splits.build import BuildError, BuildPaths, build
from finsight.splits.leakage import check_manifests
from finsight.splits.manifest import read_manifests
from finsight.splits.store import FrozenSplitError, load_splits


def _paths(args: argparse.Namespace) -> BuildPaths:
    root = project_root()
    processed = get_settings().paths.processed_dir
    processed = processed if processed.is_absolute() else root / processed
    return BuildPaths(
        universe=Path(args.universe or root / "configs" / "ipo_universe.csv"),
        corpus_dir=Path(args.corpus_dir or processed / "corpus"),
        demo=root / "configs" / "demo_ipos.yaml",
        out=Path(args.out or root / "configs" / "splits.yaml"),
        manifests=Path(args.manifests or root / "data" / "manifests"),
        processed=processed,
        root=root,
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    p = argparse.ArgumentParser(prog="python -m finsight.splits")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="assign the strict time split and print counts")
    b.add_argument("--freeze", action="store_true", help="write splits.yaml + manifests")
    b.add_argument("--adr", help="C-ADR id that allows replacing a frozen split")
    b.add_argument("--dev-share", type=float, default=SplitRules.dev_share)
    b.add_argument("--train-share", type=float, default=SplitRules.train_share)
    b.add_argument("--demo-newest", type=int, default=SplitRules.demo_newest)
    for cmd in (b, sub.add_parser("check", help="leakage check on the committed manifests")):
        cmd.add_argument("--universe")
        cmd.add_argument("--corpus-dir")
        cmd.add_argument("--out", help="splits.yaml path")
        cmd.add_argument("--manifests")
    args = p.parse_args(argv)
    paths = _paths(args)

    if args.cmd == "check":
        if not paths.out.is_file():
            print(f"{paths.out} not found: the split is not frozen yet")
            return 1
        leaks = check_manifests(read_manifests(paths.manifests), load_splits(paths.out))
        for v in leaks:
            print(v)
        print("leakage check clean" if not leaks else f"{len(leaks)} leaks")
        return 1 if leaks else 0

    rules = SplitRules(dev_share=args.dev_share, train_share=args.train_share,
                       demo_newest=args.demo_newest)  # fmt: skip
    try:
        outcome = build(paths, rules, freeze=args.freeze, adr=args.adr)
    except (BuildError, SplitError, FrozenSplitError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    print("\n".join(outcome.report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
