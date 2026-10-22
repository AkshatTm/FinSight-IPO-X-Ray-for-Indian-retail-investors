# ruff: noqa: E501
"""Standalone CPU inference for M3 Event Classifier (`classify_events`).

Contract (`docs/phase4/P4_HANDOFF_CONTRACT.md` §C):
    LABELS = ["actual_event", "hypothetical", "negated", "not_relevant"]
    def classify_events(items: list[dict]) -> list[dict]:
        '''items: [{"id","sentence","context_before","context_after","check_id"}]
        Returns [{"id","label","probs": {label: float}}]. CPU, <= 50 ms/item.'''

Zero product imports (`src/finsight/...` is never imported).
"""

from __future__ import annotations

import json
import math
import os
import pathlib
from typing import Any

LABELS: list[str] = ["actual_event", "hypothetical", "negated", "not_relevant"]
LABEL2ID: dict[str, int] = {lbl: idx for idx, lbl in enumerate(LABELS)}
ID2LABEL: dict[int, str] = dict(enumerate(LABELS))

DEFAULT_MODEL_DIR = pathlib.Path(__file__).resolve().parent / "artifacts"
MAX_LENGTH = 256

_SESSION_CACHE: dict[str, Any] = {}


def format_event_input(item: dict[str, Any]) -> str:
    """Format an event item identically for training and ONNX inference."""
    check_id = str(item.get("check_id") or "unknown").strip()
    ctx_before = " ".join(str(item.get("context_before") or "").split())
    sentence = " ".join(str(item.get("sentence") or "").split())
    ctx_after = " ".join(str(item.get("context_after") or "").split())
    return f"[{check_id}] {ctx_before} [SEP] {sentence} [SEP] {ctx_after}".strip()


def _softmax(logits: list[float]) -> list[float]:
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps)
    return [e / total for e in exps]


def _select_label(probs: dict[str, float], actual_event_threshold: float | None) -> str:
    if actual_event_threshold is not None:
        if probs["actual_event"] >= actual_event_threshold:
            return "actual_event"
        non_ae = [lbl for lbl in LABELS if lbl != "actual_event"]
        return max(non_ae, key=lambda k: probs[k])
    return max(LABELS, key=lambda k: probs[k])


def _load_onnx_bundle(model_dir: pathlib.Path) -> dict[str, Any] | None:
    key = str(model_dir.resolve())
    if key in _SESSION_CACHE:
        return _SESSION_CACHE[key]

    onnx_path = model_dir / "model.onnx"
    if not onnx_path.exists():
        return None

    import onnxruntime as ort  # type: ignore
    from transformers import AutoTokenizer  # type: ignore

    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = int(os.environ.get("FINSIGHT_ORT_THREADS", "4"))
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(
        str(onnx_path),
        sess_options=sess_options,
        providers=["CPUExecutionProvider"],
    )
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    threshold_path = model_dir / "threshold.json"
    actual_event_threshold: float | None = None
    if threshold_path.exists():
        meta = json.loads(threshold_path.read_text(encoding="utf-8"))
        actual_event_threshold = float(meta.get("actual_event_threshold", 0.5))

    bundle = {
        "session": session,
        "tokenizer": tokenizer,
        "input_names": {inp.name for inp in session.get_inputs()},
        "actual_event_threshold": actual_event_threshold,
    }
    _SESSION_CACHE[key] = bundle
    return bundle


def _fallback_logits(item: dict[str, Any]) -> list[float]:
    """Deterministic lexical fallback used only when ONNX weights are not locally present."""
    s = " ".join(str(item.get("sentence") or "").split()).lower()
    ctx = (
        f"{item.get('context_before', '')} {item.get('sentence', '')} {item.get('context_after', '')}"
    ).lower()

    # Check strong negation signals first unless "except for" / "however" / "imposed a penalty"
    has_exception = any(
        kw in s
        for kw in (
            "except for",
            "except as",
            "however,",
            "imposed a penalty",
            "imposed penalty",
            "material uncertainty exists",
            "cast significant doubt",
            "qualified opinion",
            "basis for qualified",
            "disclaimer of opinion",
        )
    )
    if not has_exception and any(
        kw in s
        for kw in (
            "has not defaulted",
            "have not defaulted",
            "no instances of default",
            "not been declared a wilful defaulter",
            "not been declared as wilful defaulter",
            "is not a wilful defaulter",
            "neither our company",
            "disposed of without",
            "no auditor qualifications",
            "there are no defaults",
        )
    ):
        return [-1.5, -1.0, 2.4, -0.8]

    # Check hypothetical / forward-looking risk boilerplate
    if not has_exception and any(
        kw in s
        for kw in (
            "if we default",
            "if any default",
            "in the event of default",
            "in the event we",
            "could result in",
            "may result in",
            "may adversely affect",
            "could adversely affect",
            "would adversely affect",
            "cannot assure",
            "no assurance",
            "cross-default",
            "cross default",
            "failure to comply",
        )
    ):
        return [-1.4, 2.3, -1.0, -0.7]

    # Check actual_event triggers
    if any(
        kw in ctx
        for kw in (
            "material uncertainty exists that may cast significant doubt",
            "uncertainty related to going concern",
            "qualified opinion",
            "disclaimer of opinion",
            "imposed a penalty",
            "warning letter",
            "show cause notice",
            "compounding application",
            "delay in repayment",
            "delays in repayment",
            "instances of delay",
            "defaulted in repayment",
            "fir was registered",
            "embezzlement",
            "misappropriation of funds",
        )
    ):
        return [2.2, -0.9, -1.2, -1.0]

    return [-1.2, -0.6, -0.8, 1.9]


def classify_events(
    items: list[dict[str, Any]],
    model_dir: pathlib.Path | str | None = None,
) -> list[dict[str, Any]]:
    """Classify candidate severe-event sentences into 4 classes on CPU (<= 50 ms/item).

    Args:
        items: List of dicts with keys `{"id", "sentence", "context_before", "context_after", "check_id"}`.
        model_dir: Optional directory containing `model.onnx`, tokenizer files, and `threshold.json`.

    Returns:
        List of dicts: `[{"id": str, "label": str, "probs": {label: float}}]`.
    """
    if not items:
        return []

    resolved_dir = pathlib.Path(
        model_dir or os.environ.get("FINSIGHT_M3_MODEL_DIR") or DEFAULT_MODEL_DIR
    )
    bundle = _load_onnx_bundle(resolved_dir)

    if bundle is not None:
        import numpy as np

        texts = [format_event_input(it) for it in items]
        enc = bundle["tokenizer"](
            texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="np",
        )
        ort_inputs = {
            k: np.asarray(v, dtype=np.int64) for k, v in enc.items() if k in bundle["input_names"]
        }
        logits_arr = bundle["session"].run(None, ort_inputs)[0]
        threshold = bundle["actual_event_threshold"]

        results: list[dict[str, Any]] = []
        for item, row_logits in zip(items, logits_arr, strict=True):
            probs_list = _softmax([float(x) for x in row_logits])
            probs = {lbl: round(float(p), 6) for lbl, p in zip(LABELS, probs_list, strict=True)}
            # Ensure exact sum norm after rounding
            diff = 1.0 - sum(probs.values())
            top_k = max(probs, key=lambda k: probs[k])
            probs[top_k] = round(probs[top_k] + diff, 6)
            pred_label = _select_label(probs, threshold)
            results.append({"id": item["id"], "label": pred_label, "probs": probs})
        return results

    # Fallback path when ONNX weights have not yet been downloaded from Drive/HF
    results = []
    for item in items:
        logits = _fallback_logits(item)
        probs_list = _softmax(logits)
        probs = {lbl: round(float(p), 6) for lbl, p in zip(LABELS, probs_list, strict=True)}
        diff = 1.0 - sum(probs.values())
        top_k = max(probs, key=lambda k: probs[k])
        probs[top_k] = round(probs[top_k] + diff, 6)
        pred_label = _select_label(probs, None)
        results.append({"id": item["id"], "label": pred_label, "probs": probs})
    return results
