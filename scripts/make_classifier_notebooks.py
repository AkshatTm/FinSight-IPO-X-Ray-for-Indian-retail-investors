"""Writes the two risk-category classifier notebooks (B2.4, M3 base and M4 large) for Kaggle.

    uv run python scripts/make_classifier_notebooks.py

Both read the private dataset ``finsight-risk-classifier`` (``train.jsonl``, ``dev.jsonl``,
``labels.json``; made by ``python -m finsight.risks.classify split``). The metric code is pasted
from ``finsight.risks.clf_metrics`` so the best epoch is chosen with the metric the laptop
reports (``tests/risks/test_classifier_notebooks.py`` checks the committed files).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "src" / "finsight" / "risks" / "clf_metrics.py"
DATASET = "finsight-risk-classifier"

NOTEBOOKS: dict[str, dict[str, Any]] = {
    "b2_classifier_base_kaggle.ipynb": {
        "title": "M3 DeBERTa-v3-base, 3 seeds",
        "MODEL": "microsoft/deberta-v3-base",
        "SEEDS": [13, 42, 2026],
        "EPOCHS": 4,
        "LEARNING_RATE": 2e-5,
        "BATCH_SIZE": 16,
        "GRAD_ACCUM": 1,
    },
    "b2_classifier_large_kaggle.ipynb": {
        "title": "M4 DeBERTa-v3-large, 1 seed (first to cut)",
        "MODEL": "microsoft/deberta-v3-large",
        "SEEDS": [42],
        "EPOCHS": 3,
        "LEARNING_RATE": 1e-5,
        "BATCH_SIZE": 4,
        "GRAD_ACCUM": 4,
    },
}

MD = """# B2.4 - Risk-category classifier: {title} (FinSight)

Fine-tunes `{model}` to put each risk factor in one of 10 categories. **Runs on Kaggle (T4, fp16)**;
nothing trains on the laptop. Data: the private dataset `finsight-risk-classifier` (teacher labels,
split 90/10 **by company**, so no company is on both sides).

- Class-weighted cross-entropy, linear warm-up and decay, max_length 384.
- The best epoch is kept by **dev macro-F1**. Gold-150 is never used here.
- A seed whose `metrics-<seed>.json` is in an attached earlier output is skipped (resume).
- Outputs: `metrics-<seed>.json`, `dev-predictions-<seed>.json` and `seed-<seed>/final/` (weights and
  `tokenizer.json`, which the ONNX export needs).
- Labels come from the teacher model (AI-made, `label_source`). Report a seed count with every number.
"""

PARAMS = """# ---- parameters ------------------------------------------------------------------------------
MODEL = {MODEL!r}
DATASET = {DATASET!r}
SEEDS = {SEEDS!r}
EPOCHS = {EPOCHS!r}
LEARNING_RATE = {LEARNING_RATE!r}
BATCH_SIZE = {BATCH_SIZE!r}
GRAD_ACCUM = {GRAD_ACCUM!r}
MAX_LEN = 384
SMOKE = False  # True: 200 train / 100 dev rows, 1 epoch, first seed only
OUT_ROOT = "/kaggle/working/classifier"
"""

BODY = """import json, math, random, shutil, time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

ON_KAGGLE = Path("/kaggle/input").exists()
if ON_KAGGLE:
    DATA_DIR = next(p.parent for p in Path("/kaggle/input").rglob("labels.json"))
else:
    DATA_DIR, OUT_ROOT = Path("data/processed/kaggle") / "risk-classifier", "classifier_out"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
LABELS = json.loads((DATA_DIR / "labels.json").read_text(encoding="utf-8"))

def read(name):
    with (DATA_DIR / f"{name}.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

train, dev = read("train"), read("dev")
assert not {r["company"] for r in train} & {r["company"] for r in dev}, "company on both sides"
if SMOKE:
    train, dev, EPOCHS, SEEDS = train[:200], dev[:100], 1, SEEDS[:1]
print(len(train), "train |", len(dev), "dev | device:", DEVICE, "x", torch.cuda.device_count())

tokenizer = AutoTokenizer.from_pretrained(MODEL)
counts = np.bincount([LABELS.index(r["label"]) for r in train], minlength=len(LABELS))
class_weights = torch.tensor(len(train) / (len(LABELS) * np.maximum(counts, 1)), dtype=torch.float, device=DEVICE)
use_amp = DEVICE.type == "cuda"

def encode(rows):
    enc = tokenizer([r["text"] for r in rows], truncation=True, max_length=MAX_LEN, padding=True,
                    return_tensors="pt")
    return {k: v.to(DEVICE) for k, v in enc.items()}

def dev_probs(model, rows, size=32):
    model.eval()
    out = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16, enabled=use_amp):
        for lo in range(0, len(rows), size):
            logits = model(**encode(rows[lo:lo + size])).logits.float()
            out += torch.softmax(logits, -1).cpu().tolist()
    return out

def earlier_metrics(seed):
    if not ON_KAGGLE:
        return None
    hit = next(Path("/kaggle/input").rglob(f"metrics-{seed}.json"), None)
    return json.loads(hit.read_text(encoding="utf-8")) if hit else None

def run_seed(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)),
        label2id={l: i for i, l in enumerate(LABELS)}).to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    steps = EPOCHS * math.ceil(len(train) / (BATCH_SIZE * GRAD_ACCUM))
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)
    out_dir = Path(OUT_ROOT) / f"seed-{seed}"
    best, per_epoch, t0 = (-1.0, None), [], time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = random.sample(range(len(train)), len(train))
        losses = []
        for i, lo in enumerate(range(0, len(order), BATCH_SIZE)):
            rows = [train[j] for j in order[lo:lo + BATCH_SIZE]]
            y = torch.tensor([LABELS.index(r["label"]) for r in rows], device=DEVICE)
            with torch.autocast("cuda", dtype=torch.float16, enabled=use_amp):
                logits = model(**encode(rows)).logits
            loss = loss_fn(logits.float(), y) / GRAD_ACCUM
            if not torch.isfinite(loss):
                raise FloatingPointError("loss is NaN")
            scaler.scale(loss).backward()
            losses.append(float(loss) * GRAD_ACCUM)
            if (i + 1) % GRAD_ACCUM == 0:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(opt); scaler.update(); sched.step(); opt.zero_grad()
        probs = dev_probs(model, dev)
        pred = [LABELS[int(np.argmax(p))] for p in probs]
        s = scores([r["label"] for r in dev], pred, LABELS)
        per_epoch.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "dev_macro_f1": s["macro_f1"],
                          "dev_accuracy": s["accuracy"]})
        print(f"seed {seed} epoch {epoch}: loss {per_epoch[-1]['train_loss']:.3f} dev macro-F1 {s['macro_f1']:.3f}")
        if s["macro_f1"] > best[0]:
            best = (s["macro_f1"], epoch)
            model.save_pretrained(str(out_dir / "final")); tokenizer.save_pretrained(str(out_dir / "final"))
            best_scores, best_preds = s, [{"risk_id": r["risk_id"], "label": r["label"], "pred": p, "probs": q}
                                         for r, p, q in zip(dev, pred, probs)]
    metrics = {"seed": seed, "model": MODEL, "best_epoch": best[1], "epochs": EPOCHS, "smoke": SMOKE,
               "learning_rate": LEARNING_RATE, "batch_size": BATCH_SIZE * GRAD_ACCUM, "max_len": MAX_LEN,
               "n_train": len(train), "n_dev": len(dev), "dev": best_scores, "per_epoch": per_epoch,
               "train_runtime_s": round(time.time() - t0),
               "gpu": torch.cuda.get_device_name(0) if use_amp else None}
    (Path(OUT_ROOT) / f"metrics-{seed}.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (Path(OUT_ROOT) / f"dev-predictions-{seed}.json").write_text(json.dumps(best_preds), encoding="utf-8")
    del model; torch.cuda.empty_cache()
    return metrics

Path(OUT_ROOT).mkdir(parents=True, exist_ok=True)
for seed in SEEDS:
    m = earlier_metrics(seed)
    if m and not m.get("smoke"):
        print(f"SEED {seed} already done (dev macro-F1 {m['dev']['macro_f1']:.3f}); skipped")
        continue
    m = run_seed(seed)
    print(f"SEED {seed} OK: best epoch {m['best_epoch']}, dev macro-F1 {m['dev']['macro_f1']:.3f}")
"""


def _cell(kind: str, src: str, tags: list[str] | None = None) -> dict[str, Any]:
    cell: dict[str, Any] = {
        "cell_type": kind,
        "metadata": {"tags": tags} if tags else {},
        "source": src.splitlines(keepends=True),
    }
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    return cell


def build(name: str) -> dict[str, Any]:
    cfg = NOTEBOOKS[name]
    return {
        "cells": [
            _cell("markdown", MD.format(title=cfg["title"], model=cfg["MODEL"])),
            _cell("code", PARAMS.format(DATASET=DATASET, **cfg), ["parameters"]),
            _cell("code", METRICS.read_text(encoding="utf-8"), ["clf-metrics"]),
            _cell("code", BODY),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    for name in NOTEBOOKS:
        out = ROOT / "notebooks" / name
        out.write_text(json.dumps(build(name), indent=1) + "\n", encoding="utf-8", newline="\n")
        print("wrote", out)


if __name__ == "__main__":
    main()
