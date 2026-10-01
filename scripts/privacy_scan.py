"""Count personal-address-like text left in the search index (ADR-048). Prints no address text.

    uv run python scripts/privacy_scan.py [--show 12]

For every IPO's ``chunks.jsonl``: passages with a residential-address cue, a bare "Address"
next to director particulars (DIN, date of birth, designation), or address-like tokens (house
number, apartments, "Sector 22", a street in a foreign address). After ``redact`` every count
should be zero; the "business" count (registered office, registrar) is allowed to stay.
``--show N`` prints up to N lines of the 30 characters *before* a cue, never the address itself.
"""

from __future__ import annotations

import argparse
import json
import re

from finsight.core.config import get_settings
from finsight.retrieve import find_personal_addresses

TOKEN = re.compile(
    r"\b(?:house|flat|plot|door|villa)\s*(?:no\.?|number|#)\s*\w+|\bapartments?\b|\bsector[\s-]*\d+\b|"
    r"\b\d{1,4}\s+[A-Z][a-z]+\s+(?:Ct|Court|St|Street|Ave|Avenue|Dr|Drive|Ln|Lane|Rd)\b",
    re.IGNORECASE,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", type=int, default=0)
    args = parser.parse_args()
    settings = get_settings()
    shown = 0
    print(f"{'ipo':34s} {'passages':>8s} {'cue/director':>12s} {'tokens':>7s}")
    for ipo_dir in sorted(p for p in settings.paths.processed_dir.iterdir() if p.is_dir()):
        chunks = ipo_dir / "index" / "chunks.jsonl"
        if not chunks.exists():
            continue
        n = cue = tok = 0
        for line in chunks.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            text = json.loads(line)["text"]
            n += 1
            found = find_personal_addresses(text)
            cue += bool(found)
            hit = TOKEN.search(text)
            tok += bool(hit)
            if shown < args.show and (found or hit):
                at = found[0][0] if found else hit.start()  # type: ignore[union-attr]
                print(f"    {ipo_dir.name[:14]:14s} ...{text[max(0, at - 30) : at]!r}")
                shown += 1
        print(f"{ipo_dir.name:34s} {n:8d} {cue:12d} {tok:7d}")


if __name__ == "__main__":
    main()
