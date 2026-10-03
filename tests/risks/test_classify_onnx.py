"""The ONNX inference path with a tiny hand-built model (no torch, no download)."""

import json
from pathlib import Path

import pytest

onnx = pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")
tokenizers = pytest.importorskip("tokenizers")

import numpy as np  # noqa: E402
from onnx import TensorProto, helper, numpy_helper  # noqa: E402

from finsight.risks.classify import OnnxClassifier, predict  # noqa: E402

LABELS = ["financial", "regulatory"]
VOCAB = {"[PAD]": 0, "[UNK]": 1, "losses": 2, "licence": 3, "the": 4}


def build(folder: Path) -> Path:
    """logits[b, c] = sum over unmasked tokens of E[token, c]."""
    emb = np.zeros((len(VOCAB), len(LABELS)), dtype=np.float32)
    emb[VOCAB["losses"], 0] = 3.0
    emb[VOCAB["licence"], 1] = 3.0
    nodes = [
        helper.make_node("Gather", ["E", "input_ids"], ["g"]),
        helper.make_node("Cast", ["attention_mask"], ["m"], to=TensorProto.FLOAT),
        helper.make_node("Unsqueeze", ["m", "axis2"], ["m3"]),
        helper.make_node("Mul", ["g", "m3"], ["gm"]),
        helper.make_node("ReduceSum", ["gm", "axis1"], ["logits"], keepdims=0),
    ]
    graph = helper.make_graph(
        nodes,
        "tiny",
        [
            helper.make_tensor_value_info("input_ids", TensorProto.INT64, ["b", "l"]),
            helper.make_tensor_value_info("attention_mask", TensorProto.INT64, ["b", "l"]),
        ],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["b", len(LABELS)])],
        [
            numpy_helper.from_array(emb, "E"),
            numpy_helper.from_array(np.array([2], dtype=np.int64), "axis2"),
            numpy_helper.from_array(np.array([1], dtype=np.int64), "axis1"),
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8
    folder.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(folder / "model.onnx"))
    tok = tokenizers.Tokenizer(tokenizers.models.WordLevel(VOCAB, unk_token="[UNK]"))
    tok.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()
    tok.save(str(folder / "tokenizer.json"))
    (folder / "labels.json").write_text(json.dumps(LABELS), encoding="utf-8")
    return folder


def test_onnx_classifier_predicts_with_padding_and_batches(tmp_path: Path) -> None:
    clf = OnnxClassifier(build(tmp_path / "onnx"))
    texts = ["the losses", "the licence the the the", "the", "losses losses licence"]
    probs = clf.predict_proba(texts, batch_size=3)
    assert len(probs) == 4
    assert all(sum(p) == pytest.approx(1.0) for p in probs)
    assert [c for c, _ in predict(clf, texts)] == [
        "financial",
        "regulatory",
        "financial",
        "financial",
    ]
    assert probs[2] == pytest.approx([0.5, 0.5])  # padding is masked out


def test_truncation_uses_max_length(tmp_path: Path) -> None:
    clf = OnnxClassifier(build(tmp_path / "onnx"), max_length=2)
    [(label, _)] = predict(clf, ["the the licence losses losses"])
    assert label == "financial" or label == "regulatory"
    assert clf.predict_proba(["the the licence"])[0] == pytest.approx([0.5, 0.5])
