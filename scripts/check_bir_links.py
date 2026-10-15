"""C1.5: how many BIR spreadsheet PDF links still answer? (HEAD, then a 1-byte range GET.)

    uv run python scripts/check_bir_links.py [--limit N]    # -> eval_results/c/bir_links.json

Only the link columns of ``data/raw/ipo_dataset/ipo_mainline_final_data_v18.xlsx`` are read. One
request per link, a pause between requests, a descriptive User-Agent; nothing is downloaded beyond
one byte. The backfill itself (fetching the live PDFs) is Akshat's decision, see AKSHAT_TODO.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data" / "raw" / "ipo_dataset" / "ipo_mainline_final_data_v18.xlsx"
OUT = ROOT / "eval_results" / "c" / "bir_links.json"
LINK_COLUMNS = ("dhrp_rhp_links_pdf", "most_relevant_link")
UA = "FinSight-course-project link check (non-commercial; contact: repo owner)"
URL = re.compile(r"https?://[^\s'\",\]\[]+")


def extract_links(cell: object) -> list[str]:
    """Every http(s) URL in a spreadsheet cell (a cell may hold a list written as text)."""
    return URL.findall(str(cell)) if cell else []


def probe(url: str, timeout: float = 20.0) -> tuple[int | None, str]:
    """``(HTTP status, content-type)`` from HEAD, falling back to a 1-byte range GET."""
    for method, headers in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as err:
            if method == "GET" or err.code not in (403, 405, 501):
                return err.code, err.headers.get("Content-Type", "") if err.headers else ""
        except (urllib.error.URLError, TimeoutError, OSError):
            if method == "GET":
                return None, ""
    return None, ""


def main() -> None:
    """Probe every distinct link once and write the counts by close year."""
    from openpyxl import load_workbook

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pause", type=float, default=0.4)
    a = ap.parse_args()

    ws = load_workbook(XLSX, read_only=True).worksheets[0]
    rows = ws.iter_rows(values_only=True)
    head = list(next(rows))
    idx = {h: i for i, h in enumerate(head)}
    jobs: list[tuple[str, str, str]] = []  # (key, year, url)
    for row in rows:
        year = str(row[idx["Close Year"]] or "")[:4]
        links: list[str] = []
        for col in LINK_COLUMNS:
            links += extract_links(row[idx[col]])
        for url in dict.fromkeys(links):
            jobs.append((str(row[idx["mapping_key"]]), year, url))
    if a.limit:
        jobs = jobs[: a.limit]

    seen: dict[str, tuple[int | None, str]] = {}
    by_year: dict[str, Counter] = {}
    for n, (_, year, url) in enumerate(jobs, 1):
        if url not in seen:
            seen[url] = probe(url)
            time.sleep(a.pause)
        status, ctype = seen[url]
        live = status is not None and 200 <= status < 300
        pdf = live and ("pdf" in ctype.lower() or url.lower().split("?")[0].endswith(".pdf"))
        bucket = "live_pdf" if pdf else "live_other" if live else f"dead_{status}"
        by_year.setdefault(year, Counter())[bucket] += 1
        if n % 25 == 0:
            print(n, "/", len(jobs), flush=True)
    total: Counter = Counter()
    for c in by_year.values():
        total.update(c)
    out = {
        "checked_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "links": len(jobs),
        "distinct_urls": len(seen),
        "total": dict(total),
        "by_close_year": {y: dict(c) for y, c in sorted(by_year.items())},
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
