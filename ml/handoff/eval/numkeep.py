"""Number-keeping filter for teacher outputs (M1): drop outputs with a number not in their source.

    python numkeep.py --in teacher_raw.jsonl --out teacher_kept.jsonl \
        --source-field passages --output-field answer

``unmatched_numbers`` is a copy of the product's check (``risks.checks``): money and percentages
are compared by value within the printed precision, plain numbers must appear verbatim (commas
ignored). Each rejected row is written to ``<out>.rejected.jsonl`` with the numbers that failed, so
the drop rate can be reported. Runs anywhere; uses the bundled ``vendor/finsight_lite``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))

from finsight_lite.numcheck import unmatched_numbers  # noqa: E402


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_text(v) for v in value)
    return json.dumps(value, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--in", dest="src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--source-field", required=True)
    ap.add_argument("--output-field", required=True)
    args = ap.parse_args(argv)
    kept = dropped = 0
    rejected = args.out.with_suffix(".rejected.jsonl")
    with (
        args.src.open(encoding="utf-8") as f,
        args.out.open("w", encoding="utf-8", newline="\n") as ok,
        rejected.open("w", encoding="utf-8", newline="\n") as bad,
    ):
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            missing = unmatched_numbers(
                _text(row[args.source_field]), _text(row[args.output_field])
            )
            if missing:
                dropped += 1
                bad.write(
                    json.dumps({**row, "unmatched_numbers": missing}, ensure_ascii=False) + "\n"
                )
            else:
                kept += 1
                ok.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "kept": kept,
                "dropped": dropped,
                "drop_rate": round(dropped / max(kept + dropped, 1), 4),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
