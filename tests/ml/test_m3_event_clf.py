# ruff: noqa: E501
"""Tests for M3 Event Classifier (`ml/m3_event_clf/predict.py` and `ml/notebooks/m3_event_clf.ipynb`)."""

from __future__ import annotations

import ast
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.m3_event_clf.predict import LABELS, classify_events, format_event_input  # noqa: E402

PREDICT_PATH = ROOT / "ml" / "m3_event_clf" / "predict.py"
NB_PATH = ROOT / "ml" / "notebooks" / "m3_event_clf.ipynb"


def test_m3_predict_contract_and_no_product_imports() -> None:
    assert LABELS == ["actual_event", "hypothetical", "negated", "not_relevant"]

    tree = ast.parse(PREDICT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("finsight"), f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("finsight"), f"Forbidden import: {node.module}"

    items = [
        {
            "id": "hit000028",
            "check_id": "going_concern",
            "context_before": "We draw attention to Note 42 to the Restated Consolidated Financial Information.",
            "sentence": "These events or conditions indicate that a material uncertainty exists that may cast significant doubt on the Company's ability to continue as a going concern.",
            "context_after": "Our opinion is not modified in respect of this matter.",
        },
        {
            "id": "hit_hyp_01",
            "check_id": "default_or_recall",
            "context_before": "We have entered into various financing arrangements with banks.",
            "sentence": "In the event of default on our repayment obligations, our lenders could recall the loans and accelerate repayment, which may adversely affect our business.",
            "context_after": "We seek to maintain adequate liquidity.",
        },
        {
            "id": "hit_neg_01",
            "check_id": "default_or_recall",
            "context_before": "Track record of debt servicing.",
            "sentence": "Our Company has not defaulted in repayment of any loans or borrowings from any bank or financial institution.",
            "context_after": "Further, none of our Promoters have been declared wilful defaulters.",
        },
    ]

    formatted = format_event_input(items[0])
    assert formatted.startswith("[going_concern]")
    assert "[SEP]" in formatted

    t0 = time.perf_counter()
    preds = classify_events(items)
    elapsed_ms_per_item = ((time.perf_counter() - t0) * 1000.0) / len(items)
    assert elapsed_ms_per_item <= 50.0

    assert len(preds) == 3
    for inp, out in zip(items, preds, strict=True):
        assert out["id"] == inp["id"]
        assert out["label"] in LABELS
        assert set(out["probs"].keys()) == set(LABELS)
        assert abs(sum(out["probs"].values()) - 1.0) < 1e-4

    assert preds[0]["label"] == "actual_event"
    assert preds[1]["label"] == "hypothetical"
    assert preds[2]["label"] == "negated"


def test_m3_notebook_structure_and_colab_rules() -> None:
    assert NB_PATH.exists(), "ml/notebooks/m3_event_clf.ipynb must exist"
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    cells = nb["cells"]
    assert len(cells) >= 4

    header_src = "".join(cells[0]["source"])
    assert "DEBUG = True" in header_src
    assert "2.90 G4 units" in header_src

    all_code = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
    for c in cells:
        if c["cell_type"] == "code":
            ast.parse("".join(c["source"]))
    assert 'JOB = "m3_event_clf"' in all_code
    assert "DEBUG = True" in all_code
    assert "SEEDS = [13, 42, 2026]" in all_code
    assert "RESUME = True" in all_code
    assert 'HF_REVISION = "a285902d91a5557cf6d6d7cf23a9e266410d6c3d"' in all_code
    assert 'HF_PACK_REVISION = "af028c61cde3f0aee6e52fc40593ac47b2a7aa1b"' in all_code
    assert "git clone" not in all_code
    assert "warmup_ratio" not in all_code
    assert "torch.onnx.export" in all_code
    assert "excluded_ipos.json" in all_code
    assert "metrics.json" in all_code
