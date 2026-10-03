"""Risk-category classifier (B03 §4): TF-IDF + logistic-regression baseline on the laptop CPU,
DeBERTa (trained on Kaggle) served as ONNX int8 on the CPU worker.

    uv run python -m finsight.risks.classify split      # train/dev by company + Kaggle folder
    uv run python -m finsight.risks.classify baseline   # fit on train, score dev (and gold)

Labels are the teacher's (``label_source`` says so); gold-150 is for the final report only and
never chooses anything.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from finsight.risks.clf_metrics import company_bucket, scores
from finsight.risks.teacher import CATEGORIES
from finsight.risks.teacher_data import original_text
from finsight.risks.teacher_run import read_jsonl

DEV_FRACTION = 0.1
SPLIT_SEED = 2026
MAX_LENGTH = 384  # tokens; the DeBERTa notebooks and the ONNX export use the same value


@dataclass(frozen=True)
class Example:
    risk_id: str
    company: str
    text: str
    label: str


class Classifier(Protocol):
    labels: Sequence[str]

    def predict_proba(self, texts: Sequence[str]) -> list[list[float]]: ...


def predict(clf: Classifier, texts: Sequence[str]) -> list[tuple[str, float]]:
    """``(category, probability)`` per text."""
    out = []
    for probs in clf.predict_proba(texts):
        best = max(range(len(probs)), key=probs.__getitem__)
        out.append((clf.labels[best], float(probs[best])))
    return out


# ----------------------------------------------------------------------------- data
def load_examples(labels_path: Path, risks_path: Path) -> list[Example]:
    """Join teacher labels to the risk text (the text the teacher saw)."""
    risks = {str(r["risk_id"]): r for r in read_jsonl(risks_path)}
    out = []
    for row in read_jsonl(labels_path):
        risk = risks.get(str(row["risk_id"]))
        if risk is None or row.get("category") not in CATEGORIES:
            continue
        company = str(row.get("company") or risk.get("company") or "")
        out.append(Example(str(row["risk_id"]), company, original_text(risk), row["category"]))
    return out


def split_by_company(
    examples: Sequence[Example], dev_fraction: float = DEV_FRACTION, seed: int = SPLIT_SEED
) -> tuple[list[Example], list[Example]]:
    """90/10 by company: every risk of one company lands on the same side."""
    train, dev = [], []
    for ex in examples:
        (dev if company_bucket(ex.company, seed) < dev_fraction else train).append(ex)
    return train, dev


def write_split(train: Sequence[Example], dev: Sequence[Example], folder: Path) -> Path:
    """``train.jsonl``, ``dev.jsonl`` and ``labels.json``: the private Kaggle dataset."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("dev", dev)):
        with (folder / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for ex in rows:
                f.write(json.dumps(ex.__dict__, ensure_ascii=False) + "\n")
    (folder / "labels.json").write_text(json.dumps(list(CATEGORIES)) + "\n", encoding="utf-8")
    return folder


# ----------------------------------------------------------------------------- baseline
class TfidfBaseline:
    """TF-IDF (word 1–2 grams, sublinear tf) + class-weighted logistic regression."""

    def __init__(self, labels: Sequence[str] = CATEGORIES, seed: int = SPLIT_SEED) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline

        self.labels = list(labels)
        self.pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=200_000
                    ),
                ),
                (
                    "lr",
                    LogisticRegression(
                        class_weight="balanced", max_iter=2000, C=4.0, random_state=seed
                    ),
                ),
            ]
        )

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> TfidfBaseline:
        self.pipeline.fit(list(texts), list(labels))
        return self

    def predict_proba(self, texts: Sequence[str]) -> list[list[float]]:
        """Probabilities in ``self.labels`` order (0 for a class unseen in training)."""
        raw = self.pipeline.predict_proba(list(texts))
        seen = [str(c) for c in self.pipeline.classes_]
        cols = {lab: seen.index(lab) for lab in self.labels if lab in seen}
        return [
            [float(row[cols[lab]]) if lab in cols else 0.0 for lab in self.labels] for row in raw
        ]

    def save(self, path: Path) -> None:
        import joblib

        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"labels": self.labels, "pipeline": self.pipeline}, path)

    @classmethod
    def load(cls, path: Path) -> TfidfBaseline:
        import joblib

        data = joblib.load(path)  # only files this project wrote (models/ is never shared)
        obj = cls.__new__(cls)
        obj.labels, obj.pipeline = data["labels"], data["pipeline"]
        return obj


def evaluate(clf: Classifier, examples: Sequence[Example]) -> dict[str, Any]:
    if not examples:
        return scores([], [], clf.labels)
    pred = [p for p, _ in predict(clf, [ex.text for ex in examples])]
    return scores([ex.label for ex in examples], pred, clf.labels)


# ----------------------------------------------------------------------------- ONNX
class OnnxClassifier:
    """A fine-tuned encoder exported by ``scripts/export_onnx_classifier.py``.

    The folder holds ``model.onnx`` (int8), ``tokenizer.json`` and ``labels.json``. Needs the
    ``onnx`` dependency group (onnxruntime + tokenizers); no torch.
    """

    def __init__(self, folder: Path, max_length: int = MAX_LENGTH, threads: int = 0) -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.labels = json.loads((folder / "labels.json").read_text(encoding="utf-8"))
        self.tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=max_length)
        pad = next(
            (t for t in ("[PAD]", "<pad>") if self.tokenizer.token_to_id(t) is not None), None
        )
        pad_id = self.tokenizer.token_to_id(pad) if pad else 0
        self.tokenizer.enable_padding(pad_id=pad_id, pad_token=pad or "[PAD]")
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        self.session = ort.InferenceSession(
            str(folder / "model.onnx"), opts, providers=["CPUExecutionProvider"]
        )
        self.inputs = {i.name for i in self.session.get_inputs()}

    def predict_proba(self, texts: Sequence[str], batch_size: int = 16) -> list[list[float]]:
        import numpy as np

        out: list[list[float]] = []
        for lo in range(0, len(texts), batch_size):
            enc = self.tokenizer.encode_batch(list(texts[lo : lo + batch_size]))
            feed = {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
            }
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.array([e.type_ids for e in enc], dtype=np.int64)
            logits = self.session.run(None, {k: v for k, v in feed.items() if k in self.inputs})[0]
            z = logits - logits.max(axis=1, keepdims=True)
            p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
            out.extend(p.astype(float).tolist())
        return out


# ----------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m finsight.risks.classify")
    p.add_argument("command", choices=["split", "baseline"])
    p.add_argument("--teacher-dir", type=Path, default=Path("data/processed/teacher"))
    p.add_argument("--split-dir", type=Path, default=Path("data/processed/kaggle/risk-classifier"))
    p.add_argument("--gold", type=Path, help="gold-150 JSONL (risk_id, company, text, label)")
    p.add_argument("--out", type=Path, default=Path("eval_results/b/classifier_tfidf.json"))
    p.add_argument("--model-out", type=Path, default=Path("models/risk_classifier/tfidf.joblib"))
    args = p.parse_args(argv)

    if args.command == "split":
        examples = load_examples(
            args.teacher_dir / "labels.jsonl", args.teacher_dir / "risks.jsonl"
        )
        train, dev = split_by_company(examples)
        write_split(train, dev, args.split_dir)
        print(f"train {len(train)} dev {len(dev)} -> {args.split_dir}")
        return

    def rows(name: str) -> list[Example]:
        return [Example(**r) for r in read_jsonl(args.split_dir / f"{name}.jsonl")]

    train, dev = rows("train"), rows("dev")
    clf = TfidfBaseline().fit([e.text for e in train], [e.label for e in train])
    clf.save(args.model_out)
    result: dict[str, Any] = {
        "model": "tfidf-logreg",
        "n_train": len(train),
        "label_source": "teacher (see docs/phase2/datasheets/teacher_outputs.md)",
        "dev": evaluate(clf, dev),
    }
    if args.gold:
        gold = [Example(**r) for r in read_jsonl(args.gold)]
        result["gold"] = evaluate(clf, gold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"dev macro-F1 {result['dev']['macro_f1']:.3f} -> {args.out}")


if __name__ == "__main__":
    main()
