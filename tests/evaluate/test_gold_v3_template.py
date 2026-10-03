"""Gold v3 template covers every red flag for every showcase IPO (B04 §2)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "data" / "gold" / "gold_v3_template.jsonl"


def _rows() -> list[dict[str, object]]:
    return [json.loads(line) for line in TEMPLATE.read_text(encoding="utf-8").splitlines() if line]


def test_every_ipo_has_the_same_rows() -> None:
    per_ipo = Counter(str(r["ipo_id"]) for r in _rows())
    assert len(per_ipo) == 10
    assert len(set(per_ipo.values())) == 1


def test_all_13_red_flags_have_inputs() -> None:
    flags = {f for r in _rows() for f in str(r["red_flags"]).split(",")}
    assert flags == {f"RF{i:02d}" for i in range(1, 14)}


def test_rows_are_empty_until_labelled() -> None:
    assert all(r["value_raw"] == "" and r["page"] is None for r in _rows())
