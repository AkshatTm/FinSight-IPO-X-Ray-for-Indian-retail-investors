"""Compare rule candidates with gold v1 on the DEV IPOs only (tuning discipline, ADR-026).

    uv run python scripts/rules_dev_check.py

Test IPOs are never compared here; they are first scored in P2.6.
"""

from __future__ import annotations

import json
import sys

from finsight.core.config import get_settings
from finsight.core.schemas import Count, ListValue, Money, Placeholder, Range, TableValue, TextValue
from finsight.evaluate.gold import FIELDS, _compact
from finsight.ingest.registry import list_demo_ipos
from finsight.normalize import equal, parse_amount
from finsight.pipeline.rules_stage import load_candidates


def agrees(field_id: str, gold: dict[str, object], value: object) -> bool:
    kind = FIELDS[field_id]
    if gold["status"] == "not_in_document":
        return value is None
    if value is None:
        return False
    if kind in ("money", "count", "range"):
        g = parse_amount(str(gold["value_raw"]))
        if isinstance(g, Placeholder):
            return isinstance(value, Placeholder)
        if isinstance(value, Money | Count | Range) and g is not None:
            return equal(g, value)
        return False
    if kind == "text":
        return isinstance(value, TextValue) and _compact(value.text) == _compact(
            str(gold["value_raw"])
        )
    if kind == "list":
        got = {_compact(x) for x in value.items} if isinstance(value, ListValue) else set()
        return got == {_compact(x) for x in gold["value_raw"]}  # type: ignore[attr-defined]
    if isinstance(value, TableValue):
        return {_compact(r[0]) for r in value.rows} == {_compact(p[0]) for p in gold["value_raw"]}  # type: ignore[attr-defined]
    return False


def main() -> int:
    settings = get_settings()
    gold = [
        json.loads(line)
        for line in (settings.paths.gold_dir / "gold_values.jsonl").read_text("utf-8").splitlines()
    ]
    dev = {i.ipo_id for i in list_demo_ipos() if i.split == "dev"}
    n = ok = 0
    for row in gold:
        if row["ipo_id"] not in dev:
            continue
        found = load_candidates(settings.paths.processed_dir, row["ipo_id"], row["doc"])
        top = found[row["field_id"]][0] if found[row["field_id"]] else None
        value = top.value if top else None
        good = agrees(row["field_id"], row, value)
        n += 1
        ok += good
        if not good:
            print(
                f"MISS {row['ipo_id'][:8]} {row['field_id']:26} {row['doc'][:3]} "
                f"gold={str(row['value_raw'])[:50]!r} got={(top.raw if top else None)!r:.60}"
            )
    print(f"dev agreement: {ok}/{n}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    raise SystemExit(main())
