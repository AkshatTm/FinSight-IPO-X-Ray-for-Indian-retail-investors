"""Tests for Phase 4 L2 event classification dataset (AR-03)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENT_DIR = ROOT / "data" / "gold" / "event_labels"
HANDOFF_DATA = ROOT / "ml" / "handoff" / "data"

VALID_LABELS = {"actual_event", "hypothetical", "negated", "not_relevant"}
VALID_CHECK_IDS = {
    "going_concern",
    "default_or_recall",
    "regulator_order",
    "fraud",
    "qualified_audit",
}


def _load_jsonl(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_l2_files_exist_and_schema_valid() -> None:
    expected_files = (
        "train.jsonl",
        "dev.jsonl",
        "test.jsonl",
        "akshat_verification_gold.csv",
        "LABELS_CARD.md",
    )
    for fname in expected_files:
        assert (EVENT_DIR / fname).exists(), f"Missing {fname}"

    train = _load_jsonl(EVENT_DIR / "train.jsonl")
    dev = _load_jsonl(EVENT_DIR / "dev.jsonl")
    test = _load_jsonl(EVENT_DIR / "test.jsonl")
    all_rows = train + dev + test

    assert len(all_rows) >= 800, f"Expected >= 800 rows, got {len(all_rows)}"
    unique_ipos = {r["ipo_id"] for r in all_rows}
    assert len(unique_ipos) >= 60, f"Expected >= 60 unique IPOs, got {len(unique_ipos)}"

    seen_ids: set[str] = set()
    for split_name, rows in (("train", train), ("dev", dev), ("test", test)):
        for r in rows:
            assert r["id"] not in seen_ids, f"Duplicate id: {r['id']}"
            seen_ids.add(r["id"])
            assert r["slice"] == split_name
            assert r["label"] in VALID_LABELS
            assert r["check_id"] in VALID_CHECK_IDS
            assert r["label_source"] == "ai"
            assert isinstance(r["page"], int)
            assert r["page"] >= 1
            quote = r["evidence_quote"]
            assert bool(quote)
            assert len(quote.split()) <= 25, f"Quote > 25 words in {r['id']}"
            assert quote in r["sentence"], f"Quote not substring of sentence in {r['id']}"


def test_l2_class_minimums_and_no_split_overlap() -> None:
    train = _load_jsonl(EVENT_DIR / "train.jsonl")
    dev = _load_jsonl(EVENT_DIR / "dev.jsonl")
    test = _load_jsonl(EVENT_DIR / "test.jsonl")
    all_rows = train + dev + test

    for lbl in VALID_LABELS:
        count = sum(1 for r in all_rows if r["label"] == lbl)
        assert count >= 150, f"Class {lbl} has {count} < 150 rows"

    train_ipos = {r["ipo_id"] for r in train}
    dev_ipos = {r["ipo_id"] for r in dev}
    test_ipos = {r["ipo_id"] for r in test}
    assert not (train_ipos & dev_ipos)
    assert not (train_ipos & test_ipos)
    assert not (dev_ipos & test_ipos)

    excl_path = HANDOFF_DATA / "excluded_ipos.json"
    excluded = set(json.loads(excl_path.read_text(encoding="utf-8"))["ipos"].keys())
    assert not (train_ipos & excluded), f"Excluded IPOs in train: {train_ipos & excluded}"
    assert not (dev_ipos & excluded), f"Excluded IPOs in dev: {dev_ipos & excluded}"


def test_l2_verification_csv_covers_all_actual_events() -> None:
    all_rows = (
        _load_jsonl(EVENT_DIR / "train.jsonl")
        + _load_jsonl(EVENT_DIR / "dev.jsonl")
        + _load_jsonl(EVENT_DIR / "test.jsonl")
    )
    actual_ids = {r["id"] for r in all_rows if r["label"] == "actual_event"}

    with (EVENT_DIR / "akshat_verification_gold.csv").open("r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    csv_ids = {r["id"] for r in csv_rows}
    assert actual_ids.issubset(csv_ids), "Verification CSV must contain 100% of actual_event rows"
    assert len(csv_rows) == len(actual_ids) + 100
