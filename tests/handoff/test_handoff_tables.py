"""Row exports of the handoff pack."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from finsight.handoff import five_things, risk_bank_rows, with_ipo, write_jsonl_gz, write_parquet


def _bank(risk_id: str, ipo_id: str, split: str) -> dict[str, object]:
    return {
        "risk_id": risk_id,
        "ipo_id": ipo_id,
        "company": ipo_id,
        "year": 2024,
        "title": "T",
        "doc_date": "2024-01-01",
        "split": split,
    }


BANK = [
    _bank("a-2024#r1", "a-2024", "train"),
    _bank("a-2024#r2", "a-2024", "train"),
    _bank("x-2025#r1", "x-2025", "dev"),
]
SCORED = {
    "a-2024": [
        {
            "rid": "r1",
            "body": "body one",
            "page_start": 12,
            "page_end": 13,
            "seriousness": "high",
            "importance": 0.4,
            "order": 0,
            "title": "T1",
            "category": "financial",
        },
        {
            "rid": "r2",
            "body": "body two",
            "page_start": 14,
            "page_end": 14,
            "seriousness": "low",
            "importance": 0.9,
            "order": 1,
            "title": "T2",
            "category": "operations",
        },
    ]
}
TEACHER = {"a-2024#r1": {"category": "debt_liquidity", "seriousness_band": 4}}
CATS = {"a-2024#r2": ["market_macro", 0.97]}


def test_risk_bank_sources_and_exclusion() -> None:
    rows, st = risk_bank_rows(BANK, SCORED, TEACHER, CATS, {"x-2025"})
    by = {r["risk_id"]: r for r in rows}
    assert set(by) == {"a-2024#r1", "a-2024#r2"}
    assert by["a-2024#r1"]["category"] == "debt_liquidity"
    assert by["a-2024#r1"]["label_source"] == "ai"
    assert by["a-2024#r1"]["severity_band"] == 4
    assert by["a-2024#r1"]["severity_source"] == "ai"
    assert by["a-2024#r2"]["category"] == "market_macro"
    assert by["a-2024#r2"]["label_source"] == "model"
    assert by["a-2024#r2"]["severity_band"] is None
    assert by["a-2024#r2"]["rule_seriousness"] == "low"
    assert by["a-2024#r1"]["page"] == 12
    assert by["a-2024#r1"]["text"] == "body one"
    assert st["dropped_excluded"] == 1
    assert st["teacher"] == 1
    assert st["model"] == 1


def test_teacher_level_five_is_merged_into_band_four() -> None:
    rows, _ = risk_bank_rows(
        BANK[:1], SCORED, {"a-2024#r1": {"category": "x", "seriousness_band": 5}}, {}, set()
    )
    assert rows[0]["severity_band"] == 4


def test_with_ipo_drops_excluded_unless_eval_only() -> None:
    src = [{"risk_id": "a-2024#r1"}, {"risk_id": "x-2025#r1"}]
    kept, dropped = with_ipo(src, "ai", {"x-2025"})
    assert [r["ipo_id"] for r in kept] == ["a-2024"]
    assert dropped == 1
    both, none = with_ipo(src, "human_verified_ai", {"x-2025"}, keep=True)
    assert none == 0
    assert [r["eval_only"] for r in both] == [False, True]
    assert all(r["label_source"] == "human_verified_ai" for r in both)


def test_five_things_matches_the_report_rule() -> None:
    rows = five_things(SCORED)
    assert [r["risk_id"] for r in rows] == ["a-2024#r2", "a-2024#r1"]
    assert rows[0]["rank"] == 1
    assert rows[0]["page"] == 14


def test_gzip_output_is_deterministic(tmp_path: Path) -> None:
    rows = [{"b": 1, "a": "é"}]
    write_jsonl_gz(tmp_path / "x.gz", rows)
    write_jsonl_gz(tmp_path / "y.gz", rows)
    assert (tmp_path / "x.gz").read_bytes() == (tmp_path / "y.gz").read_bytes()
    with gzip.open(tmp_path / "x.gz", "rt", encoding="utf-8") as f:
        assert json.loads(f.read()) == {"a": "é", "b": 1}


def test_parquet_roundtrip(tmp_path: Path) -> None:
    import pyarrow.parquet as pq

    write_parquet(tmp_path / "t.parquet", [{"risk_id": "a#r1", "page": None, "text": "x"}])
    assert pq.read_table(tmp_path / "t.parquet").to_pylist()[0]["risk_id"] == "a#r1"
