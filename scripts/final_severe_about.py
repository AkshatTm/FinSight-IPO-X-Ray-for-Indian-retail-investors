"""C-ADR-26 count: showcase IPOs whose severe findings still force High (rules only, no models).

    uv run python scripts/final_severe_about.py > eval_results/final/severe_about.jsonl

One JSON row per showcase IPO (its findings with ``about`` and page, and whether they force High
before and after C-ADR-26), then a summary line. Reads the cached parses in ``data/processed``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from summary_eval import SECTIONS, load_summary  # noqa: E402

from finsight.core.schemas import ParsedDoc  # noqa: E402
from finsight.ingest.registry import list_demo_ipos  # noqa: E402
from finsight.redflags import detect_severe  # noqa: E402
from finsight.redflags.severe import forcing, with_auditor  # noqa: E402


def main() -> int:
    """Print one row per showcase IPO and the before / after counts."""
    processed = ROOT / "data" / "processed"
    rows: list[dict[str, object]] = []
    for ipo in list_demo_ipos():
        summary, _ = load_summary(processed, ipo.ipo_id, "rhp")
        parsed = processed / ipo.ipo_id / "parsed.json"
        sections = processed / ipo.ipo_id / "sections.json"
        if summary is None or not parsed.exists():
            rows.append({"ipo_id": ipo.ipo_id, "split": ipo.split, "missing": True})
            continue
        doc = ParsedDoc.model_validate_json(parsed.read_bytes())
        found = detect_severe(doc, SECTIONS.validate_json(sections.read_bytes()), ipo.ipo_id)
        remark = next((v.evidence for v in summary.auditor_remarks if v.evidence), None)
        qualified = any(
            "qualif" in str(getattr(v.value, "text", "")).lower() for v in summary.auditor_remarks
        )
        found = with_auditor(qualified, found, remark)
        rows.append(
            {
                "ipo_id": ipo.ipo_id,
                "split": ipo.split,
                "findings": [(o.id, o.about, o.evidence.page) for o in found],
                "forced_high_before": bool(found),
                "forced_high_now": bool(forcing(found)),
            }
        )
    for r in rows:
        print(json.dumps(r))
    before = sum(bool(r.get("forced_high_before")) for r in rows)
    now = sum(bool(r.get("forced_high_now")) for r in rows)
    print(f"forced High: before {before} / {len(rows)}, now {now} / {len(rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
