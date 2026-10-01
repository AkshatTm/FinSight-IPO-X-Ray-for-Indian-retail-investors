"""Why does the reranker lose Recall@5 to hybrid search? (P3.2c item 6; ADR-049)

    uv run --group ml --group onnx python scripts/rerank_experiment.py [--skip-onnx]

Dev questions only (``questions_dev.jsonl``, 3 dev IPOs): the test file is never opened. The
same hybrid candidate pool (BM25 + bge-m3 + cover injection) is re-ranked by:

- ``fp16_512``      the shipped reranker (torch, CUDA half precision, 512 tokens)
- ``fp32_512``      torch float32 (is half precision the problem?)
- ``fp32_1024``     float32 with 1024 tokens (is truncation the problem?)
- ``swapped_512``   passage first, question second (is the input order the problem? it should hurt)
- ``onnx_fp32_512`` and ``onnx_int8_512``  the ONNX graph on CPU, as the deploy profile would run it

and reports Recall@1, Recall@5, MRR, how many pool passages the 512-token limit cuts, and the
dev-tuned abstain threshold for each variant. Query vectors are computed once and the embedder is
freed before a reranker is loaded, because both do not fit in 4 GB of VRAM together.
"""

from __future__ import annotations

import argparse
import gc
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from finsight.core.config import get_settings
from finsight.retrieve import BgeM3Embedder, CrossEncoderReranker, Retriever
from finsight.retrieve.evaluate import (
    Question,
    is_hit,
    load_questions,
    score_method,
    tune_threshold,
)
from finsight.retrieve.rerank import BGE_RERANKER, OnnxReranker, Reranker


class CachedEmbedder:
    def __init__(self, vectors: dict[str, np.ndarray]) -> None:
        self.vectors = vectors

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.stack([self.vectors[t] for t in texts])


class Recording:
    """Wraps a reranker; keeps the pool and how long scoring took."""

    def __init__(self, inner: Reranker | None) -> None:
        self.inner, self.seconds, self.pools = inner, 0.0, []

    def score(self, query: str, texts: list[str]) -> list[float]:
        self.pools.append(texts)
        if self.inner is None:
            return [0.0] * len(texts)
        started = time.perf_counter()
        scores = self.inner.score(query, texts)
        self.seconds += time.perf_counter() - started
        return scores


def export_onnx(out_dir: Path, int8: bool) -> Path:
    """Export bge-reranker-v2-m3 to ONNX (fp32), and quantise it to int8 when asked."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    out_dir.mkdir(parents=True, exist_ok=True)
    fp32 = out_dir / "reranker_fp32.onnx"
    if not fp32.exists():
        tok = AutoTokenizer.from_pretrained(BGE_RERANKER)
        model = AutoModelForSequenceClassification.from_pretrained(BGE_RERANKER).eval()
        sample = tok(["q"], ["p"], return_tensors="pt", padding="max_length", max_length=32)
        names = [n for n in ("input_ids", "attention_mask") if n in sample]
        with torch.no_grad():
            torch.onnx.export(
                model, tuple(sample[n] for n in names), str(fp32), input_names=names,
                output_names=["logits"], opset_version=17, dynamo=False,
                dynamic_axes={**{n: {0: "batch", 1: "seq"} for n in names}, "logits": {0: "batch"}},
            )  # fmt: skip
        del model
        gc.collect()
    if not int8:
        return fp32
    quantised = out_dir / "reranker_int8.onnx"
    if not quantised.exists():
        from onnxruntime.quantization import QuantType, quantize_dynamic

        quantize_dynamic(str(fp32), str(quantised), weight_type=QuantType.QInt8)
    return quantised


def truncation_stats(pools: list[list[str]], max_len: int) -> dict[str, Any]:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(BGE_RERANKER)
    lengths = [len(tok(t, add_special_tokens=False)["input_ids"]) for pool in pools for t in pool]
    over = sum(n > max_len - 40 for n in lengths)  # ~40 tokens go to the question
    return {"passages_in_pools": len(lengths), "cut_at_512": over,
            "share_cut": round(over / max(1, len(lengths)), 3),
            "median_tokens": int(np.median(lengths)), "max_tokens": max(lengths)}  # fmt: skip


def evaluate(retriever: Retriever, questions: list[Question], rec: Recording) -> dict[str, Any]:
    runs = []
    for q in questions:
        result = retriever.search(q.question, q.ipo_id, top_k=5)
        runs.append((q, result.hits, result.top_score))
    scored = score_method([(q, h) for q, h, _ in runs])["all"]
    hit_ranks = defaultdict(int)
    for q, hits, _ in runs:
        if q.answerable:
            rank = next((h.rank for h in hits if is_hit(h, q)), 0)
            hit_ranks[rank] += 1
    return {
        "recall@1": scored["recall@1"]["mean"], "recall@5": scored["recall@5"]["mean"],
        "mrr": scored["mrr"]["mean"], "n": scored["n"],
        "hit_rank_counts": {str(k): v for k, v in sorted(hit_ranks.items())},
        "abstain_threshold_dev": tune_threshold([(q.answerable, top) for q, _, top in runs]),
        "rerank_seconds_per_question": round(rec.seconds / max(1, len(questions)), 2),
    }  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-onnx", action="store_true")
    parser.add_argument("--only", help="comma-separated variant names")
    args = parser.parse_args()
    settings = get_settings()
    questions = load_questions(settings.paths.data_dir / "gold" / "questions_dev.jsonl")
    embedder = BgeM3Embedder()
    texts = sorted({q.question for q in questions})
    cache = dict(zip(texts, embedder.embed(texts), strict=True))
    del embedder
    gc.collect()
    import torch

    torch.cuda.empty_cache()
    cached = CachedEmbedder(cache)

    def run(name: str, make: Any) -> dict[str, Any]:
        inner = make()
        rec = Recording(inner)
        # no reranker at all for the baseline: the retriever then leads with the cover passages
        reranker = rec if inner is not None else None
        retriever = Retriever(
            settings.paths.processed_dir, embedder=cached, reranker=reranker, top_k=5
        )  # type: ignore[arg-type]
        out = evaluate(retriever, questions, rec)
        out["truncation"] = truncation_stats(rec.pools[:10], 512) if name == "fp16_512" else None
        print(name, json.dumps({k: v for k, v in out.items() if k != "truncation"}), flush=True)
        return out

    variants: dict[str, Any] = {
        "hybrid_no_rerank": lambda: None,
        "fp16_512": lambda: CrossEncoderReranker(precision="fp16", max_len=512),
        "fp32_512": lambda: CrossEncoderReranker(precision="fp32", max_len=512, batch=4),
        "fp32_1024": lambda: CrossEncoderReranker(precision="fp32", max_len=1024, batch=2),
        "swapped_512": lambda: CrossEncoderReranker(
            precision="fp16", max_len=512, swap_inputs=True
        ),
    }
    if not args.skip_onnx:
        out_dir = settings.paths.models_dir / "reranker_onnx"
        variants["onnx_fp32_512"] = lambda: OnnxReranker(str(export_onnx(out_dir, False)))
        variants["onnx_int8_512"] = lambda: OnnxReranker(str(export_onnx(out_dir, True)))
    wanted = set(args.only.split(",")) if args.only else set(variants)
    path = settings.paths.eval_dir / "rerank_dev.json"
    previous = json.loads(path.read_text(encoding="utf-8"))["variants"] if path.exists() else {}
    results = dict(previous)  # runs are one variant at a time (RAM); keep the earlier ones
    for name, make in variants.items():
        if name in wanted:
            results[name] = run(name, make)
            gc.collect()
            torch.cuda.empty_cache()
    path.write_text(json.dumps({"set": "dev", "n_questions": len(questions), "variants": results},
                               indent=1) + "\n", encoding="utf-8")  # fmt: skip
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
