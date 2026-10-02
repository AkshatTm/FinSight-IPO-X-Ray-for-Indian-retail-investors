"""Writes notebooks/03_muril_guard.ipynb.

uv run python scripts/make_muril_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "notebooks" / "03_muril_guard.ipynb"

MD = """# 03 - MuRIL advice classifier (FinSight, P5.4, E8 classifier row)

Fine-tunes `google/muril-base-cased` (Indian-language BERT, covers Hindi and Hinglish) to say whether a
question asks for investment advice, a forecast or a rating (`advice`) or for a fact (`fact`). **Runs on
Kaggle** with the private dataset `finsight-advice` (the E8 set, split 70/15/15 by question and
stratified by language and label, seed 2026). Nothing trains on the laptop.

- Best epoch by **validation** F1 of the advice class; the test part is scored once per seed, after
  training, and never used to choose anything.
- The set is small (about 84 train questions) and was drafted by Claude chat, not by Akshat: a result
  here is a signal, not a guarantee. Intervals on the test part are wide.
- Outputs: `metrics-<seed>.json`, `predictions-<seed>.json` (probability per val/test question) and
  `seed-<seed>/final/` (weights).
"""

PARAMS = """# ---- parameters ------------------------------------------------------------------------------
MODEL = "google/muril-base-cased"
DATASET = "finsight-advice"
SEEDS = [13, 42, 2026]
EPOCHS = 8
LEARNING_RATE = 3e-5
BATCH_SIZE = 16
MAX_LEN = 64
OUT_ROOT = "/kaggle/working/guard"
"""

BODY = """import csv, json, random, shutil, time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ON_KAGGLE = Path("/kaggle/input").exists()
if ON_KAGGLE:
    DATA_DIR = next(Path("/kaggle/input").glob(f"**/{DATASET}"), None) or next(Path("/kaggle/input").iterdir())
else:
    DATA_DIR = Path("data/processed/kaggle") / DATASET
    OUT_ROOT = "guard_out"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
LABELS = ["fact", "advice"]

def read(name):
    with (Path(DATA_DIR) / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

train, val, test = read("train"), read("val"), read("test")
assert not {r["question"] for r in train} & {r["question"] for r in val + test}, "question in two parts"
print(len(train), len(val), len(test), "questions | device:", DEVICE)
tokenizer = AutoTokenizer.from_pretrained(MODEL)

def encode(rows):
    enc = tokenizer([r["question"] for r in rows], truncation=True, max_length=MAX_LEN,
                    padding=True, return_tensors="pt")
    return {k: v.to(DEVICE) for k, v in enc.items()}

def probs(model, rows):
    model.eval()
    out = []
    with torch.no_grad():
        for lo in range(0, len(rows), 32):
            logits = model(**encode(rows[lo:lo + 32])).logits.float()
            out += torch.softmax(logits, -1)[:, 1].cpu().tolist()
    return out

def scores(rows, p, threshold=0.5):
    y = np.array([r["label"] == "advice" for r in rows])
    pred = np.array(p) >= threshold
    tp, fp, fn, tn = int((y & pred).sum()), int((~y & pred).sum()), int((y & ~pred).sum()), int((~y & ~pred).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    out = {"n": len(rows), "accuracy": (tp + tn) / len(rows), "precision": prec, "recall": rec,
           "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
           "block_rate": rec, "false_block_rate": fp / (fp + tn) if fp + tn else 0.0,
           "tp": tp, "fp": fp, "fn": fn, "tn": tn}
    out["per_language"] = {}
    for lang in sorted({r["language"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["language"] == lang]
        yl, pl = y[idx], pred[idx]
        out["per_language"][lang] = {"n": len(idx), "accuracy": float((yl == pl).mean()),
                                     "blocked": int((yl & pl).sum()), "advice": int(yl.sum()),
                                     "false_blocks": int((~yl & pl).sum()), "facts": int((~yl).sum())}
    return out

def run_seed(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL, num_labels=2).to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    steps = EPOCHS * ((len(train) + BATCH_SIZE - 1) // BATCH_SIZE)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (0.1 * steps)) * max(0.0, 1 - s / steps))
    out_dir = Path(OUT_ROOT) / f"seed-{seed}"
    best = (-1.0, 1e9, None)
    per_epoch, history = [], []
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = random.sample(range(len(train)), len(train))
        losses = []
        for lo in range(0, len(order), BATCH_SIZE):
            rows = [train[i] for i in order[lo:lo + BATCH_SIZE]]
            labels = torch.tensor([int(r["label"] == "advice") for r in rows], device=DEVICE)
            loss = model(**encode(rows), labels=labels).loss
            if not torch.isfinite(loss):
                raise FloatingPointError("loss is NaN")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            losses.append(float(loss))
        history.append({"epoch": epoch, "loss": float(np.mean(losses))})
        v = scores(val, probs(model, val))
        per_epoch.append({"epoch": epoch, "train_loss": history[-1]["loss"], "val_f1": v["f1"],
                          "val_accuracy": v["accuracy"]})
        print(f"epoch {epoch}: loss {history[-1]['loss']:.3f} val F1 {v['f1']:.3f} acc {v['accuracy']:.3f}")
        if (v["f1"], -history[-1]["loss"]) > (best[0], -best[1]):
            best = (v["f1"], history[-1]["loss"], epoch)
            model.save_pretrained(str(out_dir / "final")); tokenizer.save_pretrained(str(out_dir / "final"))
    final = AutoModelForSequenceClassification.from_pretrained(str(out_dir / "final")).to(DEVICE)
    pv, pt = probs(final, val), probs(final, test)
    metrics = {"seed": seed, "model": MODEL, "best_epoch": best[2], "epochs": EPOCHS,
               "learning_rate": LEARNING_RATE, "batch_size": BATCH_SIZE, "n_train": len(train),
               "val": scores(val, pv), "test": scores(test, pt), "per_epoch": per_epoch,
               "train_runtime_s": round(time.time() - t0), "n_gpu": torch.cuda.device_count()}
    (Path(OUT_ROOT) / f"metrics-{seed}.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (Path(OUT_ROOT) / f"predictions-{seed}.json").write_text(json.dumps({
        "val": [{"question": r["question"], "language": r["language"], "label": r["label"], "p_advice": p} for r, p in zip(val, pv)],
        "test": [{"question": r["question"], "language": r["language"], "label": r["label"], "p_advice": p} for r, p in zip(test, pt)],
    }, ensure_ascii=False), encoding="utf-8")
    del model, final; torch.cuda.empty_cache()
    return metrics

Path(OUT_ROOT).mkdir(parents=True, exist_ok=True)
for seed in SEEDS:
    m = run_seed(seed)
    print(f"SEED {seed} OK: best epoch {m['best_epoch']}, val F1 {m['val']['f1']:.3f}, test F1 {m['test']['f1']:.3f}, "
          f"block {m['test']['block_rate']:.3f}, false block {m['test']['false_block_rate']:.3f}")
"""


def code(src: str, tags: list[str] | None = None) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": tags} if tags else {},
        "outputs": [],
        "source": src.splitlines(keepends=True),
    }


def main() -> None:
    nb = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": MD.splitlines(keepends=True)},
            code(PARAMS, ["parameters"]),
            code(BODY),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
