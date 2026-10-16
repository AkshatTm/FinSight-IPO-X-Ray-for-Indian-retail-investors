"""E14 / E15 side by side: frozen v1, the wiring-only run, v2 and v2 on gold v3.1, by IPO slice.

    uv run python scripts/e14_e15_versions.py [--out eval_results/c/e14_e15_versions.json]

Reads the result files only (never the gold or the documents) and re-uses the two scorers'
``summarise`` on the rows of each IPO slice (``configs/demo_ipos.yaml``). The v1 files are never
rewritten. Prints a markdown table; writes the same numbers as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import redflag_eval  # noqa: E402
import summary_eval  # noqa: E402

B = ROOT / "eval_results" / "b"
E14 = {
    "v1 (frozen)": B / "summary_extraction.json",
    "v2": B / "summary_extraction_v2.json",
    "v2 on gold v3.1": B / "summary_extraction_v2_on_v31.json",
}
E15 = {
    "v1 (frozen)": B / "redflags.json",
    "v1 + offer-fact wiring": B / "redflags_v1_wired.json",
    "v2": B / "redflags_v2.json",
    "v2 on gold v3.1": B / "redflags_v2_on_v31.json",
}


def _split() -> dict[str, str]:
    demo = yaml.safe_load((ROOT / "configs" / "demo_ipos.yaml").read_text(encoding="utf-8"))
    return {e["ipo_id"]: e["split"] for e in demo["ipos"]}


def _rows(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["rows"]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out", type=Path, default=ROOT / "eval_results" / "c" / "e14_e15_versions.json"
    )
    a = ap.parse_args(argv)
    split = _split()
    result: dict[str, Any] = {"e14": {}, "e15": {}}
    lines = ["| run | slice | E14 NVM | n | E14 status | page |", "|---|---|---|---|---|---|"]
    for name, path in E14.items():
        rows = _rows(path)
        for sl in ("all", "dev", "test"):
            part = [r for r in rows if sl == "all" or split.get(r["ipo_id"]) == sl]
            s = summary_eval.summarise(part)
            result["e14"].setdefault(name, {})[sl] = s
            lines.append(
                f"| {name} | {sl} | {s['nvm']} | {s['n_valued']} | "
                f"{s['status_accuracy_on_blanks']} | {s['page_agreement']} |"
            )
    lines += ["", "| run | slice | E15 accuracy | n | serious |", "|---|---|---|---|---|"]
    for name, path in E15.items():
        rows = _rows(path)
        for sl in ("all", "dev", "test"):
            part = [r for r in rows if sl == "all" or split.get(r["ipo_id"]) == sl]
            s = redflag_eval.summarise(part)
            result["e15"].setdefault(name, {})[sl] = s
            lines.append(
                f"| {name} | {sl} | {s['accuracy']} | {s['n_rows']} | {s['serious_disagreements']} |"
            )
    keys = sorted(result["e14"]["v2"]["all"]["per_key"])
    lines += ["", "| E14 key | v1 | v2 | v2 on v3.1 |", "|---|---|---|---|"]
    for k in keys:
        vals = [result["e14"][n]["all"]["per_key"].get(k, {}).get("accuracy") for n in E14]
        lines.append(f"| {k} | " + " | ".join(str(v) for v in vals) + " |")
    checks = sorted(result["e15"]["v2"]["all"]["per_check"])
    lines += ["", "| E15 check | v1 | wired | v2 | v2 on v3.1 |", "|---|---|---|---|---|"]
    for c in checks:
        vals = [result["e15"][n]["all"]["per_check"][c]["accuracy"] for n in E15]
        lines.append(f"| {c} | " + " | ".join(str(v) for v in vals) + " |")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
