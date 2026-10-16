"""C2.7: score the v1 extractor seeds on the v3 dev rows (documents neither version trained on).

    uv run --group ml python scripts/extractor_v2_compare.py --dev <processed>/weaklabel_v3/dev.jsonl \
        --models models/extractor --out eval_results/c/extractor_v1_on_v3dev.json

Same windowing, span search and SQuAD EM / token-F1 as ``notebooks/01_finetune_extractor.ipynb``, so the
numbers sit next to the v2 ``metrics-<seed>.json`` files (``eval_results/c/extractor_v2/``).
Runs on CPU; the v1 weights come from ``models/extractor/seed-*``.
"""

from __future__ import annotations

import argparse
import json
import re
import string
from collections import Counter
from pathlib import Path

import numpy as np

MAX_LEN, STRIDE, MAX_ANSWER_TOKENS = 384, 128, 128
_ART = re.compile(r"\b(a|an|the)\b")


def normalize_text(t: str) -> str:
    """SQuAD answer normalisation (lowercase, drop punctuation and articles)."""
    t = "".join(c for c in t.lower() if c not in set(string.punctuation))
    return " ".join(_ART.sub(" ", t).split())


def token_f1(p: str, g: str) -> float:
    """Token-level F1 between a prediction and a gold answer."""
    p_t, g_t = normalize_text(p).split(), normalize_text(g).split()
    if not p_t and not g_t:
        return 1.0
    common = sum((Counter(p_t) & Counter(g_t)).values())
    if common == 0:
        return 0.0
    pr, rc = common / len(p_t), common / len(g_t)
    return 2 * pr * rc / (pr + rc)


def predict(model, tokenizer, rows):  # type: ignore[no-untyped-def]
    """One answer string per row ("" = no answer), best span over all windows."""
    import torch

    enc = tokenizer([r["question"].lstrip() for r in rows], [r["context"] for r in rows],
                    truncation="only_second", max_length=MAX_LEN, stride=STRIDE,
                    return_overflowing_tokens=True, return_offsets_mapping=True, padding="max_length")  # fmt: skip
    owner = enc.pop("overflow_to_sample_mapping")
    keys = ["input_ids", "attention_mask"] + (["token_type_ids"] if "token_type_ids" in enc else [])
    starts, ends = [], []
    model.eval()
    with torch.no_grad():
        for lo in range(0, len(enc["input_ids"]), 16):
            batch = {k: torch.tensor(enc[k][lo : lo + 16]) for k in keys}
            out = model(**batch)
            starts.append(out.start_logits.float().numpy())
            ends.append(out.end_logits.float().numpy())
    start_l, end_l = np.concatenate(starts), np.concatenate(ends)
    by_example: dict[int, list[int]] = {}
    for fi, ei in enumerate(owner):
        by_example.setdefault(ei, []).append(fi)
    answers = []
    for ei, row in enumerate(rows):
        best, text, null = -1e9, "", 1e9
        for fi in by_example.get(ei, []):
            seq = enc.sequence_ids(fi)
            offs = [o if seq[k] == 1 else None for k, o in enumerate(enc["offset_mapping"][fi])]
            s, e = start_l[fi], end_l[fi]
            null = min(null, s[0] + e[0])
            for si in np.argsort(s)[-20:][::-1]:
                for ej in np.argsort(e)[-20:][::-1]:
                    if (
                        offs[si] is None
                        or offs[ej] is None
                        or ej < si
                        or ej - si + 1 > MAX_ANSWER_TOKENS
                    ):
                        continue
                    if s[si] + e[ej] > best:
                        best = s[si] + e[ej]
                        text = row["context"][offs[si][0] : offs[ej][1]]
        answers.append(text if null < best else "")
    return answers


def scores(rows, preds):  # type: ignore[no-untyped-def]
    """The same dev metrics the Kaggle notebook writes."""
    gold = [r["answers"]["text"][0] if r["answers"]["text"] else "" for r in rows]
    pos = [i for i, g in enumerate(gold) if g]
    neg = [i for i, g in enumerate(gold) if not g]
    em = [normalize_text(p) == normalize_text(g) for p, g in zip(preds, gold, strict=True)]
    f1 = [token_f1(p, g) for p, g in zip(preds, gold, strict=True)]
    return {
        "n_dev": len(rows),
        "EM": float(np.mean(em)),
        "F1": float(np.mean(f1)),
        "HasAns_F1": float(np.mean([f1[i] for i in pos])),
        "NoAns_acc": float(np.mean([preds[i] == "" for i in neg])),
    }


def main() -> None:
    """Score every ``seed-*`` folder under --models on the v3 dev rows."""
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer

    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", type=Path, required=True)
    ap.add_argument("--models", type=Path, default=Path("models/extractor"))
    ap.add_argument("--out", type=Path, default=Path("eval_results/c/extractor_v1_on_v3dev.json"))
    ap.add_argument("--reuse", action="store_true", help="keep the v1 scores already in --out")
    a = ap.parse_args()
    rows = [json.loads(x) for x in a.dev.read_text("utf-8").splitlines() if x]
    result: dict[str, object] = {"dev_file": a.dev.name, "n_dev": len(rows), "runs": {}}
    if a.reuse:
        result["runs"] = json.loads(a.out.read_text("utf-8"))["runs"]
    for folder in sorted(a.models.glob("seed-*")) if not a.reuse else []:
        tok = AutoTokenizer.from_pretrained(str(folder))
        model = AutoModelForQuestionAnswering.from_pretrained(str(folder))
        result["runs"][folder.name] = scores(rows, predict(model, tok, rows))  # type: ignore[index]
        print(folder.name, result["runs"][folder.name], flush=True)  # type: ignore[index]
    v2_dir = a.out.parent / "extractor_v2"
    v2 = {
        p.stem.split("-")[-1]: json.loads(p.read_text("utf-8"))
        for p in v2_dir.glob("extractor_metrics-*.json")
    }
    names = ("EM", "F1", "HasAns_F1", "NoAns_acc")
    v1_runs: dict[str, dict[str, float]] = result["runs"]  # type: ignore[assignment]
    if v1_runs and v2:
        result["summary"] = {
            tag: {
                n: {
                    "mean": float(np.mean(vals := [r[n] for r in runs])),
                    "std": float(np.std(vals)),
                }
                for n in names
            }
            for tag, runs in (
                ("v1_on_v3_dev", list(v1_runs.values())),
                ("v2_on_v3_dev", list(v2.values())),
            )
        }
    a.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
