"""How many of the 13 red-flag checks are decided per parsed RHP (P4 regression guard, CC-05b).

    uv run python scripts/p4_decided_counts.py --data-root <main checkout> --out <file.json>
    uv run python scripts/p4_decided_counts.py --compare before.json after.json

Runs the summary path on cached parses only (no models): ``find_sections`` → ``extract_summary``
→ a rules-only X-Ray for the offer facts → ``redflags.evaluate``. "Decided" = any status except
``not_available`` (and ``pending_price`` once it exists). Coverage only: no gold is read, so the
test slice is counted but never used for tuning (C-ADR-02); ``--compare`` lists drops by slice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

UNDECIDED = {"not_available", "pending_price"}
OFFER_FIELDS = ("offer_price", "fresh_issue_size", "ofs_amount", "ofs_shares", "price_band")


def _parsed_dir(data_root: Path, ipo_id: str) -> Path | None:
    from finsight.core.ids import make_doc_id

    raw = data_root / "data" / "raw"
    pdf = next(
        (p for p in (raw / "offer_docs" / f"{ipo_id}.pdf", raw / "rhp" / f"{ipo_id}.pdf")
         if p.exists()),
        None,
    )  # fmt: skip
    proc = data_root / "data" / "processed"
    if pdf is not None:
        base = (
            proc
            / "batch"
            / "store"
            / "docs"
            / make_doc_id(hashlib.sha256(pdf.read_bytes()).hexdigest())
        )
        if (base / "parsed.json").exists():
            return base
    base = proc / ipo_id
    return base if (base / "parsed.json").exists() else None


def run_one(args: tuple[str, str, str]) -> dict[str, Any]:
    """Statuses of the 13 checks for one IPO (an ``error`` key when the path fails)."""
    from finsight.core.schemas import ParsedDoc
    from finsight.extract.fields import load_fields
    from finsight.extract.rules import RulesExtractor
    from finsight.extract.xray import DocInputs, build_xray
    from finsight.parse import find_sections
    from finsight.redflags import evaluate, inputs_from_summary
    from finsight.summary import extract_summary

    ipo_id, slice_, base_s = args
    try:
        doc = ParsedDoc.model_validate_json((Path(base_s) / "parsed.json").read_bytes())
        sections = find_sections(doc)
        summary = extract_summary(doc, sections, ipo_id)
        fields = load_fields()
        rules = RulesExtractor()
        cands = {f.id: rules.extract(doc, sections, [], f) for f in fields if f.id in OFFER_FIELDS}
        xray = build_xray(ipo_id, ipo_id, {"rhp": DocInputs(candidates=cands)},
                          datetime.now(UTC), fields=fields)  # fmt: skip
        flags = evaluate(inputs_from_summary(summary, xray))
        statuses = {f.id: f.status for f in flags.flags}
        return {
            "ipo_id": ipo_id,
            "slice": slice_,
            "statuses": statuses,
            "decided": sum(s not in UNDECIDED for s in statuses.values()),
            "has_sod": any(s.id == "summary" for s in sections),
        }
    except Exception as exc:  # report, don't stop the sweep
        return {"ipo_id": ipo_id, "slice": slice_, "error": f"{type(exc).__name__}: {exc}"[:300]}


def sweep(data_root: Path, workers: int, limit: int | None) -> dict[str, Any]:
    splits = json.loads(
        (ROOT / "ml" / "handoff" / "data" / "splits_by_ipo.json").read_text("utf-8")
    )
    jobs, missing = [], []
    for row in splits["ipos"]:
        if row.get("source") == "corpus":
            continue
        base = _parsed_dir(data_root, row["ipo_id"])
        if base is None:
            missing.append(row["ipo_id"])
            continue
        jobs.append((row["ipo_id"], str(row.get("slice")), str(base)))
    jobs = jobs[:limit] if limit else jobs
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(run_one, jobs, chunksize=2))
    ok = [r for r in rows if "error" not in r]
    return {
        "written_by": "scripts/p4_decided_counts.py",
        "written_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_docs": len(rows),
        "n_errors": len(rows) - len(ok),
        "no_parse": missing,
        "decided_total": sum(r["decided"] for r in ok),
        "decided_mean": round(sum(r["decided"] for r in ok) / max(len(ok), 1), 3),
        "rows": rows,
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> None:
    b = {r["ipo_id"]: r for r in before["rows"] if "error" not in r}
    a = {r["ipo_id"]: r for r in after["rows"] if "error" not in r}
    common = sorted(set(a) & set(b))
    print(f"docs compared: {len(common)}  decided before {sum(b[i]['decided'] for i in common)}"
          f"  after {sum(a[i]['decided'] for i in common)}")  # fmt: skip
    per_check: dict[str, list[int]] = {}
    for i in common:
        for rf in b[i]["statuses"]:
            d = per_check.setdefault(rf, [0, 0])
            d[0] += b[i]["statuses"][rf] not in UNDECIDED
            d[1] += a[i]["statuses"].get(rf) not in UNDECIDED
    for rf, (x, y) in per_check.items():
        print(f"  {rf}: {x} -> {y}")
    by_slice: dict[str, list[int]] = {}
    for i in common:
        s = by_slice.setdefault(b[i]["slice"], [0, 0, 0])
        s[0] += 1
        s[1] += b[i]["decided"]
        s[2] += a[i]["decided"]
    for s, (n, x, y) in sorted(by_slice.items()):
        print(f"  slice {s}: n={n} decided {x} -> {y}")
    down = [(i, b[i]["slice"], b[i]["decided"], a[i]["decided"]) for i in common
            if a[i]["decided"] < b[i]["decided"]]  # fmt: skip
    print(f"docs with FEWER decided checks: {len(down)}")
    for i, s, x, y in down:
        lost = [rf for rf, st in b[i]["statuses"].items()
                if st not in UNDECIDED and a[i]["statuses"].get(rf) in UNDECIDED]  # fmt: skip
        print(f"  {i} [{s}] {x} -> {y} lost {lost}")
    changed = sum(b[i]["statuses"] != a[i]["statuses"] for i in common)
    print(f"docs with any status change: {changed}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--compare", nargs=2, type=Path, metavar=("BEFORE", "AFTER"))
    a = ap.parse_args()
    if a.compare:
        compare(*(json.loads(p.read_text("utf-8")) for p in a.compare))
        return
    result = sweep(a.data_root, a.workers, a.limit)
    if a.out:
        a.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{result['n_docs']} docs, {result['n_errors']} errors, no parse {len(result['no_parse'])},"
          f" decided mean {result['decided_mean']}")  # fmt: skip


if __name__ == "__main__":
    main()
