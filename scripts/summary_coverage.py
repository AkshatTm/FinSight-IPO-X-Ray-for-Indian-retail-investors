"""How often the financial fields are found on the dev slice (C3.1a tuning; not E14).

    uv run python scripts/summary_coverage.py [--slice dev] [--processed data/processed]

Runs ``extract_summary`` on every parsed RHP of the slice (batch store for new IPOs, the showcase
folders for showcase IPOs) and writes ``eval_results/c/summary_coverage_<slice>.json``: per field
the share found / placeholder / not found, and per IPO the fields that were not found. Coverage
only: no values are compared with gold. Only ``dev`` and ``train`` may be run (C-ADR-02: test and
bench documents never inform tuning; E14 measures them once, after gold v3 is verified).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pydantic import TypeAdapter  # noqa: E402

from finsight.core.ids import make_doc_id  # noqa: E402
from finsight.core.schemas import FinancialSummary, ParsedDoc, Section, SummaryValue  # noqa: E402
from finsight.ingest.fetch import read_rows  # noqa: E402
from finsight.parse import find_subsection_pages  # noqa: E402
from finsight.splits import load_splits  # noqa: E402
from finsight.summary import extract_summary, values_by_source  # noqa: E402

ALLOWED = ("dev", "train")
SECTIONS = TypeAdapter(list[Section])
AGREE = Decimal("0.01")  # sources agree within 1 % (tables round differently)


def cross_check(by_source: dict[str, dict[str, Decimal]]) -> tuple[int, list[str]]:
    """(fields printed by 2+ sources, fields where those sources disagree)."""
    compared, disagree = 0, []
    for name, values in sorted(by_source.items()):
        vals = list(values.values())
        if len(vals) < 2:
            continue
        compared += 1
        top = max(abs(v) for v in vals) or Decimal(1)
        if (max(vals) - min(vals)) / top > AGREE:
            disagree.append(name)
    return compared, disagree


def fields(summary: FinancialSummary) -> dict[str, SummaryValue | None]:
    """Field name → value for the C3.1a fields (yearly fields get a period suffix)."""
    out: dict[str, SummaryValue | None] = {}
    for key in ("revenue", "profit_after_tax", "operating_cash_flow"):
        for v in getattr(summary, key):
            out[f"{key}:{v.period}"] = v
    out["total_borrowings"] = summary.total_borrowings
    out["net_worth"] = summary.net_worth
    return out


def doc_paths(processed: Path, ipo_id: str, sha: str | None) -> tuple[Path, Path]:
    """``parsed.json`` and ``sections.json`` of one IPO's RHP.

    The batch store (same stages as an upload) is preferred; showcase IPOs that were never
    batch-parsed fall back to their Phase 1 folder.
    """
    base = processed / "batch" / "store" / "docs" / make_doc_id(sha) if sha else None
    if base is None or not (base / "parsed.json").exists():
        base = processed / ipo_id
    return base / "parsed.json", base / "sections.json"


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-field status shares over the IPOs that were read."""
    read = [r for r in rows if r["status"] == "read"]
    per_field: dict[str, Counter[str]] = {}
    for r in read:
        for name, status in r["fields"].items():
            per_field.setdefault(name, Counter())[status] += 1
    n = len(read)
    return {
        name: {s: round(c[s] / n, 3) for s in ("found", "placeholder", "not_found")}
        for name, c in sorted(per_field.items())
    } | ({"all_fields_found": round(sum(r["n_found"] == 11 for r in read) / n, 3)} if n else {})


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice", default="dev", choices=ALLOWED)
    ap.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)
    splits = load_splits(ROOT / "configs" / "splits.yaml")
    sha = {r["ipo_id"]: r["sha256"] for r in read_rows(ROOT / "configs" / "ipo_universe.csv")}
    entries = [e for e in splits.ipos if e.slice == a.slice and e.source != "corpus"]
    rows: list[dict[str, Any]] = []
    for entry in entries[: a.limit]:
        parsed, sections = doc_paths(a.processed, entry.ipo_id, sha.get(entry.ipo_id))
        if not parsed.exists() or not sections.exists():
            rows.append({"ipo_id": entry.ipo_id, "status": "no_parse"})
            continue
        t0 = time.perf_counter()
        doc = ParsedDoc.model_validate_json(parsed.read_bytes())
        secs = SECTIONS.validate_json(sections.read_bytes())
        summary = extract_summary(doc, secs, entry.ipo_id)
        seconds = round(time.perf_counter() - t0, 2)
        status = {k: (v.status if v else "not_found") for k, v in fields(summary).items()}
        cash = find_subsection_pages(doc, secs).get("cash_flows", [])
        compared, disagree = cross_check(values_by_source(doc, secs, entry.ipo_id, cash))
        rows.append({
            "ipo_id": entry.ipo_id,
            "status": "read",
            "unit": summary.currency_unit,
            "n_found": sum(s == "found" for s in status.values()),
            "missing": sorted(k for k, s in status.items() if s != "found"),
            "fields": status,
            "compared": compared,
            "disagree": disagree,
            "seconds": seconds,
        })  # fmt: skip
        print(f"{entry.ipo_id:55s} {rows[-1]['n_found']:2d}/11", flush=True)
    result = {
        "slice": a.slice,
        "written_by": "scripts/summary_coverage.py",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_ipos": len(entries),
        "n_read": sum(r["status"] == "read" for r in rows),
        "share": summarise(rows),
        "cross_check": {
            "fields_compared": sum(r.get("compared", 0) for r in rows),
            "fields_disagreeing": sum(len(r.get("disagree", [])) for r in rows),
            "rule": "same field from 2+ sources (summary / sfi / cash) within 1 %",
        },
        "ipos": [{k: v for k, v in r.items() if k != "fields"} for r in rows],
    }
    out = a.out or ROOT / "eval_results" / "c" / f"summary_coverage_{a.slice}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out}: {result['n_read']}/{result['n_ipos']} read", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
