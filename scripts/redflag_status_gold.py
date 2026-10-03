"""Compute the red-flag status gold from gold v3 (B04 §2): 13 statuses per showcase IPO.

    uv run python scripts/redflag_status_gold.py            # verified rows only
    uv run python scripts/redflag_status_gold.py --allow-unverified   # a draft, labelled as such

Reads ``data/gold/gold_v3_summary.jsonl`` (the filled, verified copy of
``gold_v3_template.jsonl``), runs the same ``finsight.redflags`` rules as the pipeline on each
IPO's rows and writes ``data/gold/redflag_status_gold.jsonl``. Statuses are computed, never typed;
Akshat spot-checks them (B04). E15 then compares the pipeline's statuses with these.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

from finsight.redflags import evaluate, inputs_from_gold, load_config

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "gold" / "gold_v3_summary.jsonl"
OUT = ROOT / "data" / "gold" / "redflag_status_gold.jsonl"
VERIFIED = "akshat_verified"


def doc_ids_by_ipo() -> dict[str, dict[str, str]]:
    """``{ipo_id: {"rhp": doc_id, "prospectus": doc_id}}`` from ``configs/demo_ipos.yaml``."""
    demo = yaml.safe_load((ROOT / "configs" / "demo_ipos.yaml").read_text(encoding="utf-8"))
    return {
        e["ipo_id"]: {
            d: e[d]["doc_id"] for d in ("rhp", "prospectus") if isinstance(e.get(d), dict)
        }
        for e in demo["ipos"]
    }


def unverified(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """``ipo_id:key:period`` of every row a person has not verified."""
    return [
        f"{r['ipo_id']}:{r['key']}:{r['period']}"
        for r in rows
        if VERIFIED not in str(r.get("label_source") or "")
    ]


def status_rows(
    rows: list[Mapping[str, Any]], docs: Mapping[str, Mapping[str, str]], draft: bool
) -> list[dict[str, Any]]:
    """One output row per IPO and check."""
    by_ipo: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for r in rows:
        by_ipo[str(r["ipo_id"])].append(r)
    version = str(load_config()["version"])
    out: list[dict[str, Any]] = []
    for ipo_id, ipo_rows in sorted(by_ipo.items()):
        ids = docs.get(ipo_id, {})
        doc_id = ids.get("rhp") or ids.get("prospectus") or ipo_id
        for flag in evaluate(inputs_from_gold(doc_id, ipo_rows, ids)).flags:
            out.append(
                {
                    "ipo_id": ipo_id,
                    "rf": flag.id,
                    "status": flag.status,
                    "sentence": flag.sentence,
                    "numbers_used": flag.numbers_used,
                    "thresholds_version": version,
                    "label_source": "computed_from_gold_v3"
                    + ("_unverified_draft" if draft else ""),
                    "spot_checked_by_akshat": None,
                }
            )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--gold", type=Path, default=GOLD)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--allow-unverified", action="store_true")
    args = p.parse_args(argv)
    if not args.gold.exists():
        print(f"{args.gold} not found: fill and verify gold v3 first (B04 §2).", file=sys.stderr)
        return 1
    rows = [
        json.loads(line)
        for line in args.gold.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    missing = unverified(rows)
    if missing and not args.allow_unverified:
        print(
            f"{len(missing)} gold v3 rows are not verified yet, e.g. {missing[:3]}", file=sys.stderr
        )
        return 1
    out = status_rows(rows, doc_ids_by_ipo(), draft=bool(missing))
    args.out.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8"
    )
    print(f"wrote {len(out)} statuses for {len(out) // 13} IPOs to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
