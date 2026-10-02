"""Copy one recorded demo-cache answer into the frontend (landing section 5.7).

    uv run python scripts/export_landing_answer.py

Real output only: the answer text, its citation markers and the retrieved passages (page, section,
snippet) are copied unchanged from ``data/demo_cache``; nothing is edited or re-worded.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CACHE = Path("data/demo_cache/lenskart-2025")
QUESTION = "प्रमोटर कौन हैं?"
OUT = Path("frontend/lib/content/landing_answer.json")


def main() -> int:
    for path in sorted(CACHE.glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec["language"] != "hi" or QUESTION not in rec["question"]:
            continue
        events = {e["event"]: e["data"] for e in rec["events"] if e["event"] != "token"}
        passages = [
            {k: p[k] for k in ("n", "doc", "page_start", "section", "snippet")}
            for p in events["retrieval"]["passages"]
        ]
        out = {
            "ipo_id": rec["ipo_id"],
            "question": rec["question"],
            "answer": events["answer"]["text"],
            "passages": passages,
        }
        OUT.write_text(
            json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {OUT} from {path.name}")
        return 0
    print("no recorded Hindi promoter answer found", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
