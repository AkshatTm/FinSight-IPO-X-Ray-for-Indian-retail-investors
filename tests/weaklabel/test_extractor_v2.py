"""C2.7 helpers: the v1-vs-v2 scoring maths and the weak-label manifests' slices."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_scores_match_squad_definitions() -> None:
    cmp = _load("extractor_v2_compare")
    rows = [
        {"answers": {"text": ["Rs. 10"]}},
        {"answers": {"text": ["the Offer"]}},
        {"answers": {"text": []}},
        {"answers": {"text": []}},
    ]
    s = cmp.scores(rows, ["10", "Offer", "", "something"])
    assert s["EM"] == 0.5  # "Rs. 10" != "10" after normalising; "the Offer" == "Offer"
    assert s["NoAns_acc"] == 0.5
    assert 0.0 < s["HasAns_F1"] <= 1.0
    assert cmp.token_f1("", "") == 1.0


def test_v3_manifests_hold_only_train_and_dev_slice_ipos() -> None:
    from finsight.splits import load_splits

    slices = {e.ipo_id: e.slice for e in load_splits(ROOT / "configs" / "splits.yaml").ipos}
    for name, allowed in (("weaklabel_v3_train", {"train"}), ("weaklabel_v3_dev", {"dev"})):
        text = (ROOT / "data" / "manifests" / f"{name}.json").read_text("utf-8")
        ids = json.loads(text)["ipo_ids"]
        assert ids, name
        assert {slices[i] for i in ids} <= allowed, name
