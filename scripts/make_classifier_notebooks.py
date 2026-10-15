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

Fine-tunes `{model}` twice per seed: **category** (one of 10) and **seriousness band** (1, 2, 3,
4 = severe; levels 4 and 5 merged). **Runs on Kaggle (T4, fp16)**; nothing trains on the laptop.
Data: the private dataset `finsight-risk-classifier` (teacher labels after the C2.3b clean-up and
category remap, split 90/10 **by company**, so no company is on both sides) and `test.jsonl`
(gold-150 from held-out test IPOs).

- Class-weighted cross-entropy, linear warm-up and decay, max_length 384.
- The best epoch is kept by **dev macro-F1** (category or band). Gold-150 never chooses anything:
  it is scored once, at the epoch dev chose.
- Gold-150 category labels are human-verified; its seriousness band is the teacher's (no human
  seriousness label exists), so band scores on test measure agreement with the teacher.
- A task and seed whose metrics file is in an attached earlier output is skipped (resume).
- Outputs: `metrics-<seed>.json` / `metrics-band-<seed>.json`, dev and test predictions, and
  `seed-<seed>/final/` / `seed-<seed>-band/final/` (weights and `tokenizer.json` for the ONNX export).
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
TASKS = ["category", "band"]
SMOKE = False  # True: 200 train / 100 dev / 50 test rows, 1 epoch, first seed only
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
CATS = json.loads((DATA_DIR / "labels.json").read_text(encoding="utf-8"))
BANDS = ["1", "2", "3", "4"]  # 4 = severe (levels 4 and 5)

def read(name):
    path = DATA_DIR / f"{name}.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

train_all, dev_all, test_all = read("train"), read("dev"), read("test")
assert not {r["company"] for r in train_all} & {r["company"] for r in dev_all}, "company on both sides"
assert not {r["company"] for r in test_all} & {r["company"] for r in train_all + dev_all}, "test company in train/dev"
if SMOKE:
    train_all, dev_all, test_all, EPOCHS, SEEDS = train_all[:200], dev_all[:100], test_all[:50], 1, SEEDS[:1]
print(len(train_all), "train |", len(dev_all), "dev |", len(test_all), "test | device:", DEVICE, "x", torch.cuda.device_count())

tokenizer = AutoTokenizer.from_pretrained(MODEL)
use_amp = DEVICE.type == "cuda"

def target(task, r):
    return CATS.index(r["label"]) if task == "category" else BANDS.index(str(r["band"]))

def rows_for(task, rows):
    return rows if task == "category" else [r for r in rows if r.get("band") is not None]

def task_scores(task, rows, pred_idx):
    if task == "category":
        return scores([r["label"] for r in rows], [CATS[i] for i in pred_idx], CATS)
    return band_scores([int(r["band"]) for r in rows], [i + 1 for i in pred_idx])

def encode(rows):
    enc = tokenizer([r["text"] for r in rows], truncation=True, max_length=MAX_LEN, padding=True,
                    return_tensors="pt")
    return {k: v.to(DEVICE) for k, v in enc.items()}

def predict(model, rows, size=32):
    model.eval()
    out = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16, enabled=use_amp):
        for lo in range(0, len(rows), size):
            logits = model(**encode(rows[lo:lo + size])).logits.float()
            out += torch.softmax(logits, -1).cpu().tolist()
    return out

def names(task, seed):
    tag = "" if task == "category" else "band-"
    return (f"metrics-{tag}{seed}.json", f"dev-predictions-{tag}{seed}.json",
            f"test-predictions-{tag}{seed}.json", f"seed-{seed}" + ("" if task == "category" else "-band"))

def earlier_metrics(task, seed):
    if not ON_KAGGLE:
        return None
    hit = next(Path("/kaggle/input").rglob(names(task, seed)[0]), None)
    return json.loads(hit.read_text(encoding="utf-8")) if hit else None

def run(task, seed):
    labels = CATS if task == "category" else BANDS
    train, dev, test = rows_for(task, train_all), rows_for(task, dev_all), rows_for(task, test_all)
    counts = np.bincount([target(task, r) for r in train], minlength=len(labels))
    class_weights = torch.tensor(len(train) / (len(labels) * np.maximum(counts, 1)), dtype=torch.float, device=DEVICE)
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, num_labels=len(labels), id2label=dict(enumerate(labels)),
        label2id={l: i for i, l in enumerate(labels)}).float().to(DEVICE)  # fp32 master weights: recent transformers load the checkpoint dtype (fp16)
    opt = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    steps = EPOCHS * math.ceil(len(train) / (BATCH_SIZE * GRAD_ACCUM))
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)
    metrics_name, dev_name, test_name, folder = names(task, seed)
    out_dir = Path(OUT_ROOT) / folder
    best, per_epoch, t0 = (-1.0, None), [], time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = random.sample(range(len(train)), len(train))
        losses = []
        for i, lo in enumerate(range(0, len(order), BATCH_SIZE)):
            rows = [train[j] for j in order[lo:lo + BATCH_SIZE]]
            y = torch.tensor([target(task, r) for r in rows], device=DEVICE)
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
        probs = predict(model, dev)
        pred = [int(np.argmax(p)) for p in probs]
        s = task_scores(task, dev, pred)
        per_epoch.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "dev_macro_f1": s["macro_f1"],
                          "dev_accuracy": s["accuracy"]})
        print(f"{task} seed {seed} epoch {epoch}: loss {per_epoch[-1]['train_loss']:.3f} dev macro-F1 {s['macro_f1']:.3f}")
        if s["macro_f1"] > best[0]:  # chosen on dev only
            best = (s["macro_f1"], epoch)
            model.save_pretrained(str(out_dir / "final")); tokenizer.save_pretrained(str(out_dir / "final"))
            best_scores = s
            best_preds = [{"risk_id": r["risk_id"], "gold": labels[target(task, r)], "pred": labels[p], "probs": q}
                          for r, p, q in zip(dev, pred, probs)]
            test_probs = predict(model, test) if test else []
            test_pred = [int(np.argmax(p)) for p in test_probs]
            test_scores = task_scores(task, test, test_pred) if test else None
            test_preds = [{"risk_id": r["risk_id"], "gold": labels[target(task, r)], "pred": labels[p], "probs": q}
                          for r, p, q in zip(test, test_pred, test_probs)]
    metrics = {"task": task, "seed": seed, "model": MODEL, "best_epoch": best[1], "epochs": EPOCHS, "smoke": SMOKE,
               "learning_rate": LEARNING_RATE, "batch_size": BATCH_SIZE * GRAD_ACCUM, "max_len": MAX_LEN,
               "n_train": len(train), "n_dev": len(dev), "n_test": len(test), "dev": best_scores,
               "test": test_scores, "selected_on": "dev macro-F1; test scored once at that epoch",
               "test_label_source": ("human:akshat (gold-150)" if task == "category"
                                     else "teacher:gemma-4-31b-it band (no human seriousness label)"),
               "per_epoch": per_epoch, "train_runtime_s": round(time.time() - t0),
               "gpu": torch.cuda.get_device_name(0) if use_amp else None}
    (Path(OUT_ROOT) / metrics_name).write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (Path(OUT_ROOT) / dev_name).write_text(json.dumps(best_preds), encoding="utf-8")
    (Path(OUT_ROOT) / test_name).write_text(json.dumps(test_preds), encoding="utf-8")
    del model; torch.cuda.empty_cache()
    return metrics

Path(OUT_ROOT).mkdir(parents=True, exist_ok=True)
for seed in SEEDS:
    for task in TASKS:
        m = earlier_metrics(task, seed)
        if m and not m.get("smoke"):
            print(f"{task} SEED {seed} already done (dev macro-F1 {m['dev']['macro_f1']:.3f}); skipped")
            continue
        m = run(task, seed)
        t = m["test"] or {}
        print(f"{task} SEED {seed} OK: best epoch {m['best_epoch']}, dev macro-F1 {m['dev']['macro_f1']:.3f}, "
              f"test macro-F1 {t.get('macro_f1', float('nan')):.3f}")
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
    cells = [
        _cell("markdown", MD.format(title=cfg["title"], model=cfg["MODEL"])),
        _cell("code", PARAMS.format(DATASET=DATASET, **cfg), ["parameters"]),
        _cell("code", METRICS.read_text(encoding="utf-8"), ["clf-metrics"]),
        _cell("code", BODY),
    ]
    for i, c in enumerate(cells):
        c["id"] = str(i)  # the ids nbstripout writes, so the hook leaves the file alone
    return {
        "cells": cells,
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
