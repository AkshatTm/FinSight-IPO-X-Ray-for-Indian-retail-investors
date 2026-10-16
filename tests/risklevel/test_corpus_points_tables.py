"""``scripts/corpus_points.py``: the fit table holds only IPOs with red flags (C2.8)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from finsight.risklevel.reference import read_scores
from finsight.splits import load_splits

ROOT = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "corpus_points_under_test", ROOT / "scripts" / "corpus_points.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _risk(rid: str) -> dict[str, object]:
    return {
        "rid": rid, "order": 0, "title": "t", "body": "b", "page_start": 1, "page_end": 1,
        "seriousness": "high", "novelty": 0.01,
    }  # fmt: skip


def test_full_table_leaves_out_ipos_without_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cp = _load()
    with_flags, without = (e.ipo_id for e in load_splits(ROOT / "configs" / "splits.yaml").ipos[:2])
    scored = tmp_path / "scored"
    scored.mkdir()
    for ipo in (with_flags, without):
        (scored / f"{ipo}.json").write_text(json.dumps([_risk("r1")]), encoding="utf-8")
    (scored / f"{with_flags}.flags.json").write_text(json.dumps({"flags": []}), encoding="utf-8")
    monkeypatch.setattr(cp, "SCORED", scored)
    monkeypatch.setattr(cp, "TABLE", tmp_path / "full.csv")
    monkeypatch.setattr(cp, "POINTS_TABLE", tmp_path / "points.csv")

    cp.cmd_scores(points_only=False)
    cp.cmd_scores(points_only=True)

    assert set(read_scores(tmp_path / "full.csv")) == {with_flags}
    assert set(read_scores(tmp_path / "points.csv")) == {with_flags, without}
    assert read_scores(tmp_path / "points.csv")[without] == 0.25  # one rare high risk: 1 / 4
