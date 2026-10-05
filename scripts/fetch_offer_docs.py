"""Download the offer documents of ``configs/ipo_universe.csv`` politely (C1.2).

    uv run python scripts/fetch_offer_docs.py [--limit 5] [--only ipo-id ...] [--delay 4]
    uv run python scripts/fetch_offer_docs.py --adopt     # after dropping manual PDFs in the folder
    uv run python scripts/fetch_offer_docs.py --retry     # try the `manual:` rows over the network again

PDFs go to ``data/raw/offer_docs/<ipo_id>.pdf`` (gitignored); only the CSV (status, sha256, pages)
is committed. Showcase IPOs are copied from ``data/raw/rhp/`` instead of downloaded again. The
script stops when free disk is below 15 GB and prints the manual-download list at the end.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.ingest import list_demo_ipos  # noqa: E402
from finsight.ingest.fetch import Fetcher, run  # noqa: E402

CSV = ROOT / "configs" / "ipo_universe.csv"
OUT = ROOT / "data" / "raw" / "offer_docs"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=CSV)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--delay", type=float, default=4.0)
    ap.add_argument("--retry", action="store_true")
    ap.add_argument("--adopt", action="store_true", help="only adopt PDFs already in the folder")
    a = ap.parse_args(argv)
    showcase = {i.ipo_id: i.rhp.file for i in list_demo_ipos()}
    fetcher = Fetcher(delay=a.delay)
    report = run(
        a.csv, a.out, fetcher, only=set(a.only) if a.only else None,
        limit=0 if a.adopt else a.limit, showcase_dirs=showcase, retry=a.retry,
    )  # fmt: skip
    print(f"\ndownloaded {len(report.downloaded)}, adopted {len(report.adopted)}, "
          f"manual {len(report.manual)}; requests {fetcher.requests}")  # fmt: skip
    if report.stopped:
        print("stopped:", report.stopped)
    if report.manual:
        print("\nMANUAL DOWNLOAD LIST (save as data/raw/offer_docs/<ipo_id>.pdf, then --adopt):")
        for ipo, url, why in report.manual:
            print(f"- {ipo}: {url}  [{why}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
