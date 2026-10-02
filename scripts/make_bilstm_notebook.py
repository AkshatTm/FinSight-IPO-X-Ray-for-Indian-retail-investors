"""Writes notebooks/02_bilstm_crf.ipynb (the notebook is generated so its cells stay reviewable).

uv run python scripts/make_bilstm_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "notebooks" / "02_bilstm_crf.ipynb"

MD = """# 02 - BiLSTM-CRF extractor (FinSight, Rung 4, E11)

A word + character BiLSTM with a CRF on top, tagging BIO spans (one tag set for all eight ladder
fields) on the weak labels (ADR-038/041). **Runs on Kaggle** (GPU, Internet off is enough) with the
private dataset `finsight-weaklabel` attached; nothing trains on the laptop.

- Input: `bio_train.jsonl` (tokens + BIO tags) and `bio_dev.jsonl` (dev contexts with the SQuAD
  rows they answer; same IPO split as the QA rungs).
- No pretrained vectors: word embeddings are learned from the training text, a character CNN reads
  digits and rare words.
- The model code is `src/finsight/extract/bilstm_crf_model.py`, pasted into the cell below when the run is
  pushed (`python -m finsight.weaklabel.kaggle push bilstm-smoke|bilstm-13|...`). One source of truth.
- Dev is scored after every epoch with the same EM / token-F1 as the QA rungs; the best epoch by
  dev F1 is kept in `final/`. The trivial baseline (the most common training answer of each field,
  predicted when it occurs in the context) is scored on the same dev rows and written to
  `metrics-baseline.json`: a seed must beat it.
- `predictions-<seed>.json` holds every epoch's dev answer per row so NVM is computed on the laptop
  with the FinSight normalizer.
"""

PARAMS = """# ---- parameters (the only cell you normally edit) -------------------------------------------
DATASET = "finsight-weaklabel"
SEEDS = [13, 42, 2026]
SLICE = None            # 200 = smoke test on bio_train_200.jsonl / bio_dev_200.jsonl
EPOCHS = 30
PATIENCE = 6            # stop when dev F1 has not improved for this many epochs
LEARNING_RATE = 1e-3
BATCH_SIZE = 32
MIN_WORD_FREQ = 2
OUT_ROOT = "/kaggle/working/bilstm"
"""

SETUP = """import json, random, re, string, time, warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch

warnings.filterwarnings("ignore", category=UserWarning)
ON_KAGGLE = Path("/kaggle/input").exists()
if ON_KAGGLE:
    DATA_DIR = next(Path("/kaggle/input").glob(f"**/{DATASET}"), None) or next(Path("/kaggle/input").iterdir())
else:
    DATA_DIR = Path("data/processed/kaggle") / DATASET
    OUT_ROOT = "bilstm_out"
suffix = f"_{SLICE}" if SLICE else ""
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]

train_seqs = read_jsonl(Path(DATA_DIR) / f"bio_train{suffix}.jsonl")
dev_seqs = read_jsonl(Path(DATA_DIR) / f"bio_dev{suffix}.jsonl")
assert not {s["ipo_id"] for s in train_seqs} & {s["ipo_id"] for s in dev_seqs}, "IPO leaked train->dev"
dev_rows = [dict(r, context=s["context"]) for s in dev_seqs for r in s["rows"]]
print(len(train_seqs), "train sequences,", len(dev_seqs), "dev sequences,", len(dev_rows), "dev rows | device:", DEVICE)
"""

SHARED = "# SHARED-MODEL (replaced with src/finsight/extract/bilstm_crf_model.py when the run is pushed)\n"

METRICS = """# ---- metrics (mirror finsight/evaluate/metrics.py: SQuAD EM and token F1) ---------------------
_ART = re.compile(r"\\b(a|an|the)\\b")
def normalize_text(t):
    t = "".join(c for c in t.lower() if c not in set(string.punctuation))
    return " ".join(_ART.sub(" ", t).split())
def exact_match(p, g):
    return normalize_text(p) == normalize_text(g)
def token_f1(p, g):
    p, g = normalize_text(p).split(), normalize_text(g).split()
    if not p and not g: return 1.0
    common = sum((Counter(p) & Counter(g)).values())
    if common == 0: return 0.0
    pr, rc = common / len(p), common / len(g)
    return 2 * pr * rc / (pr + rc)

def squad_scores(rows, preds):
    gold = [r["answers"]["text"][0] if r["answers"]["text"] else "" for r in rows]
    pos = [(g, p) for g, p in zip(gold, preds) if g]
    neg = [p for g, p in zip(gold, preds) if not g]
    return {
        "n_dev": len(rows), "n_answerable": len(pos), "n_unanswerable": len(neg),
        "HasAns_EM": float(np.mean([exact_match(p, g) for g, p in pos])) if pos else None,
        "HasAns_F1": float(np.mean([token_f1(p, g) for g, p in pos])) if pos else None,
        "NoAns_acc": float(np.mean([p == "" for p in neg])) if neg else None,
        "EM": float(np.mean([exact_match(p, g) for g, p in zip(gold, preds)])),
        "F1": float(np.mean([token_f1(p, g) for g, p in zip(gold, preds)])),
    }

# ---- the trivial baseline: each field's most common training answer, if it occurs in the context
def span_texts(seq):
    out, cur = [], None
    for tok, (s, e), tag in zip(seq["tokens"], seq["offsets"], seq["tags"]):
        if tag.startswith("B-"):
            cur = [tag[2:], s, e]; out.append(cur)
        elif tag.startswith("I-") and cur and cur[0] == tag[2:]:
            cur[2] = e
    return out

def baseline_answers(rows):
    common = defaultdict(Counter)
    for s in train_seqs:
        # the context text is not stored for train; rebuild each answer from tokens (single spaces)
        for field, a, b in span_texts(s):
            toks = [t for t, (x, y) in zip(s["tokens"], s["offsets"]) if x >= a and y <= b]
            common[field][" ".join(toks)] += 1
    out = {}
    for r in rows:
        best = common[r["field_id"]].most_common(1)
        guess = ""
        if best:
            # find the tokens of the most common answer in this row's context
            words = best[0][0].split()
            toks = [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(r["context"])]
            for i in range(len(toks) - len(words) + 1):
                if [t for t, _, _ in toks[i:i + len(words)]] == words:
                    guess = r["context"][toks[i][1]:toks[i + len(words) - 1][2]]
                    start = toks[i][1]
                    break
        out[r["id"]] = {"text": guess, "start": start if guess else -1}
    return out

TOKEN = re.compile(r"\\d+(?:,\\d+)*(?:\\.\\d+)?|\\w+|[^\\w\\s]")
"""

TRAIN = '''# ---- dev prediction, one training run per seed ------------------------------------------------
def predict_dev(model, vocab):
    """{row id: {"text", "start"}}: the first span of the row's field the model tags in its context."""
    model.eval()
    out = {}
    for lo in range(0, len(dev_seqs), 32):
        batch = dev_seqs[lo:lo + 32]
        words, chars, mask = pad_batch(vocab, [s["tokens"] for s in batch])
        paths = model.predict(words.to(DEVICE), chars.to(DEVICE), mask.to(DEVICE))
        for seq, path in zip(batch, paths):
            spans = spans_from_tags([vocab.tags[i] for i in path])
            for row in seq["rows"]:
                hit = next(((a, b) for f, a, b in spans if f == row["field_id"]), None)
                if hit is None:
                    out[row["id"]] = {"text": "", "start": -1}
                else:
                    s, e = seq["offsets"][hit[0]][0], seq["offsets"][hit[1]][1]
                    out[row["id"]] = {"text": seq["context"][s:e], "start": s}
    return out

def run_seed(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    out_dir = Path(OUT_ROOT) / f"seed-{seed}"
    (out_dir / "final").mkdir(parents=True, exist_ok=True)
    vocab = Vocab.build(train_seqs, MIN_WORD_FREQ)
    hp = dict(word_dim=100, char_dim=30, char_filters=50, hidden=128, dropout=0.4)
    model = BiLSTMCRF(len(vocab.words), len(vocab.chars), len(vocab.tags), **hp).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    order = list(range(len(train_seqs)))
    history, per_epoch, predictions = [], [], {}
    best_f1, best_epoch, since_best = -1.0, None, 0
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        random.shuffle(order)
        losses = []
        for lo in range(0, len(order), BATCH_SIZE):
            batch = [train_seqs[i] for i in order[lo:lo + BATCH_SIZE]]
            words, chars, mask = pad_batch(vocab, [s["tokens"] for s in batch])
            tags = torch.zeros_like(words)
            for i, s in enumerate(batch):
                tags[i, :len(s["tags"])] = torch.tensor([vocab.t2i[t] for t in s["tags"]])
            opt.zero_grad()
            loss = model.loss(words.to(DEVICE), chars.to(DEVICE), mask.to(DEVICE), tags.to(DEVICE))
            if not torch.isfinite(loss):
                raise FloatingPointError("loss is NaN")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            losses.append(float(loss))
        history.append({"step": epoch * len(range(0, len(order), BATCH_SIZE)), "epoch": float(epoch),
                        "loss": float(np.mean(losses))})
        preds = predict_dev(model, vocab)
        scores = squad_scores(dev_rows, [preds[r["id"]]["text"] for r in dev_rows])
        per_epoch.append({"epoch": epoch, **scores})
        predictions[str(epoch)] = preds
        print(f"epoch {epoch}: loss {history[-1]['loss']:.3f} dev EM {scores['EM']:.4f} F1 {scores['F1']:.4f} "
              f"HasAns_F1 {scores['HasAns_F1']:.4f} NoAns_acc {scores['NoAns_acc']:.4f}")
        if scores["F1"] > best_f1:
            best_f1, best_epoch, since_best = scores["F1"], epoch, 0
            torch.save(model.state_dict(), out_dir / "final" / "model.pt")
            (out_dir / "final" / "vocab.json").write_text(json.dumps(vocab.to_json()), encoding="utf-8")
            (out_dir / "final" / "config.json").write_text(json.dumps(hp), encoding="utf-8")
        else:
            since_best += 1
            if since_best >= PATIENCE:
                print("early stop at epoch", epoch)
                break
    best = next(e for e in per_epoch if e["epoch"] == best_epoch)
    metrics = {k: v for k, v in best.items() if k != "epoch"} | {
        "seed": seed, "model": "bilstm-crf", "epochs": len(per_epoch), "max_epochs": EPOCHS,
        "learning_rate": LEARNING_RATE, "batch_size": BATCH_SIZE, "hyperparameters": hp,
        "n_train": len(train_seqs), "n_params": sum(p.numel() for p in model.parameters()),
        "train_runtime_s": round(time.time() - t0), "slice": SLICE, "n_gpu": torch.cuda.device_count(),
        "best_epoch": best_epoch, "per_epoch": per_epoch, "loss_history": history,
        "final_train_loss": history[-1]["loss"],
    }
    (Path(OUT_ROOT) / f"metrics-{seed}.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (Path(OUT_ROOT) / f"predictions-{seed}.json").write_text(json.dumps(predictions), encoding="utf-8")
    return metrics

Path(OUT_ROOT).mkdir(parents=True, exist_ok=True)
base = baseline_answers(dev_rows)
base_scores = squad_scores(dev_rows, [base[r["id"]]["text"] for r in dev_rows])
(Path(OUT_ROOT) / "metrics-baseline.json").write_text(
    json.dumps(base_scores | {"model": "most-common-answer", "zero_shot": True, "slice": SLICE}, indent=1), encoding="utf-8")
(Path(OUT_ROOT) / "predictions-baseline.json").write_text(json.dumps({"0": base}), encoding="utf-8")
print("BASELINE (most common answer):", {k: round(base_scores[k], 4) for k in ("EM", "F1", "HasAns_F1", "NoAns_acc")})
for seed in SEEDS:
    m = run_seed(seed)
    print(f"SEED {seed} OK: best epoch {m['best_epoch']}, dev EM {m['EM']:.4f} F1 {m['F1']:.4f}, {m['train_runtime_s']} s")
'''


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
            code(SETUP),
            code(SHARED, ["shared-model"]),
            code(METRICS),
            code(TRAIN),
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
