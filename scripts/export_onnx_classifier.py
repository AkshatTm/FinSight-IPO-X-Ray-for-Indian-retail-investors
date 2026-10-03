"""Export the chosen risk classifier to ONNX int8 for the CPU worker, and check it (B03 §4).

    uv run --group ml --group onnx python scripts/export_onnx_classifier.py \\
        --model models/risk_classifier/seed-42/final --out models/risk_classifier/onnx \\
        --dev data/processed/kaggle/risk-classifier/dev.jsonl

Local session only (needs torch). Writes ``model.onnx`` (dynamic int8 weights), ``tokenizer.json``
and ``labels.json`` into ``--out``; with ``--dev`` it scores PyTorch and ONNX on the same rows and
writes ``onnx_check.json`` next to the model (agreement and both macro-F1s). Weights stay in
``models/`` (gitignored).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.risks.classify import MAX_LENGTH, OnnxClassifier, predict  # noqa: E402
from finsight.risks.clf_metrics import scores  # noqa: E402
from finsight.risks.teacher_run import read_jsonl  # noqa: E402


def export(model_dir: Path, out: Path, opset: int = 17) -> Path:
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).eval()
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    out.mkdir(parents=True, exist_ok=True)
    sample = tokenizer(["a sample risk factor"], return_tensors="pt")
    names = [n for n in ("input_ids", "attention_mask", "token_type_ids") if n in sample]
    fp32 = out / "model.fp32.onnx"
    axes = {n: {0: "batch", 1: "seq"} for n in names}
    torch.onnx.export(
        model,
        tuple(sample[n] for n in names),
        str(fp32),
        input_names=names,
        output_names=["logits"],
        dynamic_axes={**axes, "logits": {0: "batch"}},
        opset_version=opset,
        dynamo=False,
    )
    quantize_dynamic(str(fp32), str(out / "model.onnx"), weight_type=QuantType.QInt8)
    fp32.unlink()
    tokenizer.save_pretrained(str(out / "_tok"))
    shutil.move(str(out / "_tok" / "tokenizer.json"), out / "tokenizer.json")
    shutil.rmtree(out / "_tok")
    id2label = model.config.id2label
    labels = [id2label[i] for i in range(len(id2label))]
    (out / "labels.json").write_text(json.dumps(labels) + "\n", encoding="utf-8")
    return out


def check(model_dir: Path, out: Path, dev_path: Path) -> dict[str, Any]:
    """PyTorch vs ONNX int8 on the dev rows: agreement, both macro-F1s, seconds per risk."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    rows = list(read_jsonl(dev_path))
    texts, gold = [r["text"] for r in rows], [r["label"] for r in rows]
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).eval()
    tok = AutoTokenizer.from_pretrained(str(model_dir))
    labels = [model.config.id2label[i] for i in range(model.config.num_labels)]
    torch_pred = []
    with torch.no_grad():
        for lo in range(0, len(texts), 16):
            enc = tok(
                texts[lo : lo + 16],
                truncation=True,
                max_length=MAX_LENGTH,
                padding=True,
                return_tensors="pt",
            )
            torch_pred += [labels[i] for i in model(**enc).logits.argmax(-1).tolist()]
    clf = OnnxClassifier(out)
    t0 = time.perf_counter()
    onnx_pred = [p for p, _ in predict(clf, texts)]
    per_risk = (time.perf_counter() - t0) / max(1, len(texts))
    result = {
        "n": len(rows),
        "agreement": sum(a == b for a, b in zip(torch_pred, onnx_pred, strict=True)) / len(rows),
        "torch_macro_f1": scores(gold, torch_pred, labels)["macro_f1"],
        "onnx_int8_macro_f1": scores(gold, onnx_pred, labels)["macro_f1"],
        "onnx_seconds_per_risk": per_risk,
    }
    (out / "onnx_check.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True, help="a seed-*/final folder")
    p.add_argument("--out", type=Path, default=Path("models/risk_classifier/onnx"))
    p.add_argument("--dev", type=Path, help="dev.jsonl to compare PyTorch and ONNX")
    args = p.parse_args(argv)
    export(args.model, args.out)
    print("wrote", args.out)
    if args.dev:
        print(json.dumps(check(args.model, args.out, args.dev), indent=1))


if __name__ == "__main__":
    main()
