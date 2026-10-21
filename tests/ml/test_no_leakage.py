"""Phase 4 leakage guard: no excluded IPO appears in any training file under ``ml/`` (CC-owned).

``ml/handoff/data/excluded_ipos.json`` is the stricter C-ADR-02 list: all test-slice IPOs, SME,
demo, Bench v1 and Platform Bench IPOs. A "training file" is any file under ``ml/`` or the label
folders ``data/gold/{event_labels,top_risks}`` whose name says train / dev, or the exported risk
bank and student sets. Evaluation-only files (test, eval, gold, bench, hits) are exempt.
Files that are not in the checkout (the big ones live on HF) are skipped.
"""

from __future__ import annotations

import gzip
import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = ROOT / "ml" / "handoff" / "data" / "excluded_ipos.json"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRAIN_NAME = re.compile(r"(train|dev|risk_bank|student_v1)", re.I)
EXEMPT_NAME = re.compile(r"(test|eval|gold|bench|hits|baseline|excluded|splits|MANIFEST)", re.I)
SUFFIXES = (".jsonl", ".jsonl.gz", ".parquet", ".csv")


def _excluded() -> set[str]:
    return set(json.loads(EXCLUDED.read_text(encoding="utf-8"))["ipos"])


def _training_files() -> Iterator[Path]:
    roots = [
        ROOT / "ml",
        ROOT / "data" / "gold" / "event_labels",
        ROOT / "data" / "gold" / "top_risks",
    ]
    for base in roots:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or not p.name.endswith(SUFFIXES):
                continue
            rel = p.relative_to(ROOT).as_posix()
            if "/vendor/" in rel or EXEMPT_NAME.search(p.name) or "/bench_v1/" in rel:
                continue
            if "/gold/" in rel and "data/gold/event_labels" not in rel and "top_risks" not in rel:
                continue
            if TRAIN_NAME.search(p.name):
                yield p


def _ipo_ids(path: Path) -> set[str]:
    """The ``ipo_id`` values of a data file (derived from ``risk_id`` when absent)."""
    name = path.name
    if name.endswith(".parquet"):
        import pyarrow.parquet as pq

        cols = pq.read_schema(path).names
        col = "ipo_id" if "ipo_id" in cols else "risk_id"
        values = {str(v) for v in pq.read_table(path, columns=[col]).column(col).to_pylist()}
        return {v.split("#")[0] for v in values}
    if name.endswith(".csv"):
        import csv

        with path.open(encoding="utf-8-sig", newline="") as f:
            return {
                (r.get("ipo_id") or str(r.get("risk_id", "")).split("#")[0])
                for r in csv.DictReader(f)
            } - {""}
    opener = gzip.open if name.endswith(".gz") else open
    ids: set[str] = set()
    with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[operator]
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            ids.add(str(row.get("ipo_id") or str(row.get("risk_id", "")).split("#")[0]))
    return ids - {""}


def test_excluded_list_is_complete_and_uses_the_repo_id_format() -> None:
    ex = _excluded()
    splits = yaml.safe_load((ROOT / "configs" / "splits.yaml").read_text(encoding="utf-8"))
    test_slice = {r["ipo_id"] for r in splits["ipos"] if r["slice"] == "test"}
    assert len(test_slice) == 110
    assert test_slice <= ex
    assert {r["ipo_id"] for r in splits["excluded"]} <= ex
    assert set(splits["bench"]) <= ex
    assert "jio-platforms-2026" in ex
    assert all(SLUG.match(i) for i in ex), "ids must be lowercase hyphen slugs"


def test_no_excluded_ipo_in_any_training_file() -> None:
    ex = _excluded()
    files = list(_training_files())
    assert files, "expected at least the exported classifier/student sets"
    leaks = {p.relative_to(ROOT).as_posix(): sorted(_ipo_ids(p) & ex)[:5] for p in files}
    leaks = {k: v for k, v in leaks.items() if v}
    assert not leaks, f"excluded IPOs found in training files: {leaks}"


def test_the_leak_check_catches_a_leak(tmp_path: Path) -> None:
    bad = tmp_path / "x_train.jsonl"
    bad.write_text(json.dumps({"ipo_id": "jio-platforms-2026"}) + "\n", encoding="utf-8")
    assert _ipo_ids(bad) & _excluded() == {"jio-platforms-2026"}


@pytest.mark.parametrize("name", ["classifier_test.jsonl.gz", "gold150.jsonl"])
def test_eval_only_files_are_exempt(name: str) -> None:
    assert EXEMPT_NAME.search(name)
