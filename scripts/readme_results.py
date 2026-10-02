"""Write the results table of README.md from ``eval_results/`` (nothing typed by hand).

    uv run python scripts/readme_results.py          # rewrite the block in README.md
    uv run python scripts/readme_results.py --check  # exit 1 if README.md is out of date

The block sits between ``<!-- results:start -->`` and ``<!-- results:end -->``. A row whose file is
missing is left out, not invented. Numbers are the test-IPO figures; read the intervals in the
files, not only the point scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

START, END = "<!-- results:start -->", "<!-- results:end -->"


def load(eval_dir: Path, name: str) -> dict[str, Any] | None:
    path = eval_dir / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def pct(x: float) -> str:
    return f"{x:.2f}"


def ci(pair: list[float]) -> str:
    return f"[{pair[0]:.2f}, {pair[1]:.2f}]"


def ladder_rows(eval_dir: Path) -> list[str]:
    table = load(eval_dir, "ladder_table.json")
    if table is None:
        return []
    rows = []
    for data in table["ladder"].values():
        test = data["test"]
        full, body = test["full"], test["body_only"]
        rows.append(
            f"| Extractor ladder, {data['label']} | NVM, 7 test IPOs | full {pct(full['nvm'])}, "
            f"body-only {pct(body['nvm'])} | `ladder_table.json` |"
        )
    return rows


def simple_rows(eval_dir: Path) -> list[str]:
    rows = []
    verifier = load(eval_dir, "verifier.json")
    if verifier:
        held = verifier["headline"]["scale_mismatch_recall"]["held_out"]
        rows.append(
            f"| Number verifier, seeded errors | scale-mismatch recall, held out | "
            f"{held['hits']}/{held['n']} {ci(held['wilson_95'])} | `verifier.json` |"
        )
    guard = load(eval_dir, "guard.json")
    if guard:
        o = guard["overall"]
        rows.append(
            f"| Advice guard (keyword), in-sample | block / false-block | "
            f"{o['block_rate']['hits']}/{o['block_rate']['n']} / "
            f"{o['false_block_rate']['hits']}/{o['false_block_rate']['n']} | `guard.json` |"
        )
    retrieval = load(eval_dir, "retrieval.json")
    if retrieval:
        for method in ("bm25", "hybrid+rerank"):
            m = retrieval["methods"].get(method)
            if m:
                t = m["test"]["all"]
                rows.append(
                    f"| Retrieval, {method} | recall@1 / recall@5, 56 test questions | "
                    f"{pct(t['recall@1']['mean'])} / {pct(t['recall@5']['mean'])} | `retrieval.json` |"
                )
    e7 = load(eval_dir, "e7.json")
    if e7:
        for split, s in e7.items():
            share = s.get("verified_share")
            if share is not None:
                rows.append(
                    f"| Chat answers (E7, {split}), one run | numbers marked ✅ | "
                    f"{pct(share)} of {s['n_numbers']} | `e7.json` |"
                )
    return rows


def render(eval_dir: Path) -> str:
    rows = [*ladder_rows(eval_dir), *simple_rows(eval_dir)]
    head = ["| Experiment | Metric | Result | File |", "|---|---|---|---|"]
    return "\n".join([*head, *rows])


def replace_block(readme: str, body: str) -> str:
    start, end = readme.index(START), readme.index(END)
    return readme[: start + len(START)] + "\n" + body + "\n" + readme[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--eval-dir", type=Path, default=Path("eval_results"))
    args = parser.parse_args(argv)
    current = args.readme.read_text(encoding="utf-8")
    updated = replace_block(current, render(args.eval_dir))
    if args.check:
        return 0 if updated == current else 1
    args.readme.write_text(updated, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
