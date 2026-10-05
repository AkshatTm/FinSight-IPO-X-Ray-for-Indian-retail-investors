"""Build or refresh ``configs/ipo_universe.csv`` from SEBI's public filings (C1.1).

    uv run python scripts/build_ipo_universe.py --since 2024-01-01            # crawl + write
    uv run python scripts/build_ipo_universe.py --since 2024-01-01 --dry-run   # print counts only

Crawls two SEBI listing sections politely (one request every 3 s), keeps one offer document per
company, maps the showcase IPOs to their existing ids, keeps the ``status``/``sha256``/``pages``/
``reason`` of rows already in the file, and prints the count by year and type for Akshat to approve.
Metadata only: no PDF is downloaded here (that is C1.2).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.ingest import list_demo_ipos  # noqa: E402
from finsight.ingest.universe import (  # noqa: E402
    SMID_FINAL,
    SMID_RHP,
    UniverseCandidate,
    UrllibTransport,
    build_candidates,
    crawl,
    name_key,
)
from finsight.splits import UNIVERSE_COLUMNS  # noqa: E402

OUT = ROOT / "configs" / "ipo_universe.csv"


def showcase_map() -> dict[str, str]:
    """``company_key -> ipo_id`` for the showcase IPOs (they keep their existing ids)."""
    return {name_key(i.company): i.ipo_id for i in list_demo_ipos()}


def to_rows(
    cands: list[UniverseCandidate], previous: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    """CSV rows; exchange is ``both`` and listing_date empty (SEBI does not say; see universe.py)."""
    rows = []
    for c in sorted(cands, key=lambda c: (c.doc_date, c.ipo_id)):
        row = {k: "" for k in UNIVERSE_COLUMNS}
        row.update(
            ipo_id=c.ipo_id, company=c.company, exchange="both", doc_type=c.doc_type,
            doc_date=c.doc_date.isoformat(), source_url=c.source_url, status="listed",
        )  # fmt: skip
        old = previous.get(c.ipo_id)
        if old:  # keep what C1.2/C1.3 already filled in
            for k in ("exchange", "listing_date", "sha256", "pages", "status", "reason"):
                row[k] = old.get(k, "") or row[k]
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", default="2024-01-01")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    since = datetime.strptime(a.since, "%Y-%m-%d").date()
    transport = UrllibTransport(delay=a.delay)
    entries = []
    for smid in (SMID_RHP, SMID_FINAL):
        entries += crawl(transport, smid, since, log=lambda m: print(m, flush=True))
    cands = build_candidates(entries, since, showcase_map())
    previous: dict[str, dict[str, str]] = {}
    if a.out.exists():
        with a.out.open(encoding="utf-8", newline="") as fh:
            previous = {r["ipo_id"]: r for r in csv.DictReader(fh)}
    rows = to_rows(cands, previous)
    by_year = Counter((r["doc_date"][:4], r["doc_type"]) for r in rows)
    print(f"\n{len(rows)} companies since {since}")
    for (year, kind), n in sorted(by_year.items()):
        print(f"  {year} {kind:<10} {n}")
    missing = sorted(set(showcase_map().values()) - {r["ipo_id"] for r in rows})
    print("showcase ids not found on SEBI:", missing or "none")
    if not a.dry_run:
        with a.out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=UNIVERSE_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print("wrote", a.out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
