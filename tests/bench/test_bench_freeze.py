"""Freeze guard and leakage guard for the committed bench (C-ADR-06, C-ADR-02, C4.1).

Reads only ``bench/``, ``configs/splits.yaml`` and ``data/manifests/`` (no processed data), so it
runs in ``poe test``.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from finsight.bench import changed_files, load, unlisted_inputs
from finsight.splits import load_splits

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "bench" / "v1"
EXCLUDED = {"ather-energy-2025", "hexaware-technologies-2025", "urban-company-2025"}

pytestmark = pytest.mark.skipif(not (BENCH / "manifest.yaml").exists(), reason="bench not built")


def _jsonl(rel: str) -> list[dict]:
    return [json.loads(x) for x in (BENCH / rel).read_text(encoding="utf-8").splitlines() if x]


def _prompts() -> list[dict]:
    text = gzip.decompress((BENCH / "inputs" / "prompts.jsonl.gz").read_bytes()).decode("utf-8")
    return [json.loads(x) for x in text.splitlines() if x]


def test_frozen_files_are_unchanged() -> None:
    m = load(BENCH)
    if not m.frozen:
        pytest.skip("bench v1 not frozen yet")
    assert changed_files(BENCH, m) == [], "frozen bench files changed: make bench/v2 (C-ADR-06)"
    assert unlisted_inputs(BENCH, m) == [], "new input files after the freeze: make bench/v2"


def test_bench_ipos_are_the_test_slice_bench() -> None:
    m = load(BENCH)
    splits = load_splits(ROOT / "configs" / "splits.yaml")
    by = splits.by_id()
    assert sorted(splits.bench) == sorted(m.ipos)
    assert all(by[i].slice == "test" for i in m.ipos)
    assert not EXCLUDED & set(m.ipos)


def test_every_bench_file_holds_bench_ipos_only() -> None:
    ipos = set(load(BENCH).ipos)
    for rel in ("items/task_a.jsonl", "items/task_c.jsonl", "items/task_d.jsonl",
                "items/task_g.jsonl", "keys/task_a.jsonl", "keys/task_b.jsonl",
                "keys/task_c.jsonl"):  # fmt: skip
        assert {r["ipo_id"] for r in _jsonl(rel)} <= ipos, rel
    for p in _prompts():
        assert p["ipo_id"] in ipos
        assert {x["ipo_id"] for x in p["passages"]} <= {p["ipo_id"]}  # no other IPO's text
    for r in _jsonl("items/task_d.jsonl"):
        assert r["risk_id"].split("#")[0] == r["ipo_id"]


def test_bench_ipos_never_train_anything() -> None:
    ipos = set(load(BENCH).ipos)
    for path in (ROOT / "data" / "manifests").glob("*.json"):
        m = json.loads(path.read_text(encoding="utf-8"))
        if m.get("kind") == "train":
            assert not ipos & set(m["ipo_ids"]), path.name


def test_keys_come_from_verified_gold() -> None:
    assert all("akshat_verified" in r["label_source"] for r in _jsonl("keys/task_a.jsonl"))
    answerable = [r for r in _jsonl("keys/task_c.jsonl") if r["answerable"]]
    assert answerable
    assert all("akshat_verified" in r["label_source"] for r in answerable)
