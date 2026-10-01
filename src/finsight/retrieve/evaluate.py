"""E6: how well does each retrieval method find the evidence page? (05 section 4)

    uv run python -m finsight.retrieve.evaluate [--dense] [--rerank]

Reads ``data/gold/questions_dev.jsonl`` and ``questions_test.jsonl`` (05 section 8; written by
Akshat). A question is *hit* when one of the top-k passages covers its ``evidence_page``.
Reported per method: Recall@1, Recall@5 and MRR (how high the first right passage ranks), with a
bootstrap interval over IPOs, split by language. The abstain threshold is tuned on the dev
questions only and then applied unchanged to the test questions.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from finsight.core.config import get_settings
from finsight.evaluate import bootstrap_ci
from finsight.retrieve.dense import Embedder
from finsight.retrieve.rerank import Reranker
from finsight.retrieve.retriever import Hit, Retriever, SearchResult

METHODS = ("bm25", "dense", "hybrid", "hybrid+rerank")
KS = (1, 5)


class Question(BaseModel):
    ipo_id: str
    question: str
    language: Literal["en", "hi"]
    answer_gold: str = ""
    evidence_page: int | None = None  # PDF page; empty for unanswerable questions
    answerable: bool


def load_questions(path: Path) -> list[Question]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found: Akshat writes the question sets (05 section 8, roadmap P3.1)"
        )
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    questions = [Question.model_validate(r) for r in rows]
    for q in questions:
        if q.answerable and q.evidence_page is None:
            raise ValueError(f"answerable question without evidence_page: {q.question!r}")
    return questions


def is_hit(hit: Hit, q: Question) -> bool:
    p = hit.passage
    return (
        q.evidence_page is not None
        and p.ipo_id == q.ipo_id
        and p.page_start <= q.evidence_page <= p.page_end
    )


def reciprocal_rank(hits: list[Hit], q: Question) -> float:
    for h in hits:
        if is_hit(h, q):
            return 1.0 / h.rank
    return 0.0


def tune_threshold(scored: list[tuple[bool, float | None]]) -> float | None:
    """The score below which to abstain, maximising balanced accuracy on dev.

    ``scored`` holds ``(answerable, top_score)`` per question; ``None`` (no hits) always abstains.
    Ties go to the lower threshold (abstain less). Returns ``None`` when dev lacks answerable or
    unanswerable questions, because there is then nothing to tune on.
    """
    answerable = [s for a, s in scored if a]
    unanswerable = [s for a, s in scored if not a]
    if not answerable or not unanswerable:
        return None
    values = sorted({s for _, s in scored if s is not None})
    candidates = [values[0] - 1.0, *values] if values else [0.0]
    best_key: tuple[float, float] | None = None
    best_t = candidates[0]
    for t in candidates:
        kept = sum(s is not None and s >= t for s in answerable) / len(answerable)
        abstained = sum(s is None or s < t for s in unanswerable) / len(unanswerable)
        key = ((kept + abstained) / 2, -t)
        if best_key is None or key > best_key:
            best_key, best_t = key, t
    return best_t


def _summary(per_ipo: dict[str, list[float]]) -> dict[str, float]:
    if not per_ipo:
        return {"mean": 0.0, "low": 0.0, "high": 0.0}
    mean, low, high = bootstrap_ci(per_ipo)
    return {"mean": round(mean, 4), "low": round(low, 4), "high": round(high, 4)}


def score_method(
    ranked: list[tuple[Question, list[Hit]]], ks: tuple[int, ...] = KS
) -> dict[str, object]:
    """Recall@k and MRR over the answerable questions, by IPO bootstrap; also by language."""
    out: dict[str, object] = {}
    for label, keep in (("all", None), ("en", "en"), ("hi", "hi")):
        rows = [(q, h) for q, h in ranked if q.answerable and (keep is None or q.language == keep)]
        block: dict[str, object] = {"n": len(rows)}
        for k in ks:
            per_ipo: dict[str, list[float]] = defaultdict(list)
            for q, hits in rows:
                per_ipo[q.ipo_id].append(float(any(is_hit(h, q) for h in hits[:k])))
            block[f"recall@{k}"] = _summary(per_ipo)
        mrr: dict[str, list[float]] = defaultdict(list)
        for q, hits in rows:
            mrr[q.ipo_id].append(reciprocal_rank(hits, q))
        block["mrr"] = _summary(mrr)
        out[label] = block
    return out


Searcher = Callable[[Question], tuple[list[Hit], float | None]]


def _flat(result: SearchResult) -> tuple[list[Hit], float | None]:
    return result.hits, result.top_score


def _dense_only(retriever: Retriever, q: Question) -> tuple[list[Hit], float | None]:
    index = retriever.index(q.ipo_id)
    if retriever.embedder is None or index.dense is None:
        return [], None
    found = index.dense.search(retriever.embedder.embed([q.question])[0], k=max(KS))
    hits = [Hit(passage=index.passages[i], score=s, rank=r) for r, (i, s) in enumerate(found, 1)]
    return hits, hits[0].score if hits else None


def searchers(
    processed_dir: Path, embedder: Embedder | None, reranker: Reranker | None
) -> dict[str, Searcher]:
    """One search function per method; ``(hits, top_score)`` with scores on that method's scale."""
    bm25_only = Retriever(processed_dir, top_k=max(KS))
    out: dict[str, Searcher] = {"bm25": lambda q: _flat(bm25_only.search(q.question, q.ipo_id))}
    if embedder is not None:
        dense = Retriever(processed_dir, embedder=embedder, top_k=max(KS))
        out["dense"] = lambda q: _dense_only(dense, q)
        out["hybrid"] = lambda q: _flat(dense.search(q.question, q.ipo_id))
        if reranker is not None:
            full = Retriever(processed_dir, embedder=embedder, reranker=reranker, top_k=max(KS))
            out["hybrid+rerank"] = lambda q: _flat(full.search(q.question, q.ipo_id))
    return out


def evaluate(
    dev: list[Question], test: list[Question], search: dict[str, Searcher]
) -> dict[str, object]:
    methods: dict[str, object] = {}
    thresholds: dict[str, float | None] = {}
    for name, fn in search.items():
        dev_runs = [(q, *fn(q)) for q in dev]
        thresholds[name] = t = tune_threshold([(q.answerable, top) for q, _, top in dev_runs])
        test_runs = [(q, *fn(q)) for q in test]
        abstained = [(q, top is None or (t is not None and top < t)) for q, _, top in test_runs]
        unanswerable = [a for q, a in abstained if not q.answerable]
        answerable = [a for q, a in abstained if q.answerable]
        methods[name] = {
            "test": score_method([(q, hits) for q, hits, _ in test_runs]),
            "dev": score_method([(q, hits) for q, hits, _ in dev_runs]),
            "abstain": {
                "threshold_from_dev": t,
                "test_unanswerable_abstained": f"{sum(unanswerable)}/{len(unanswerable)}",
                "test_answerable_wrongly_abstained": f"{sum(answerable)}/{len(answerable)}",
            },
        }
    return {"methods": methods, "thresholds": thresholds}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="finsight.retrieve.evaluate")
    parser.add_argument(
        "--dense", action="store_true", help="add dense + hybrid (bge-m3, ml group)"
    )
    parser.add_argument("--rerank", action="store_true", help="add hybrid+rerank (needs --dense)")
    args = parser.parse_args(argv)
    settings = get_settings()
    gold = settings.paths.data_dir / "gold"
    dev = load_questions(gold / "questions_dev.jsonl")
    test = load_questions(gold / "questions_test.jsonl")
    embedder: Embedder | None = None
    reranker: Reranker | None = None
    if args.dense:
        from finsight.retrieve.dense import BgeM3Embedder

        embedder = BgeM3Embedder()
        if args.rerank:
            from finsight.retrieve.rerank import CrossEncoderReranker

            reranker = CrossEncoderReranker()
    report = evaluate(dev, test, searchers(settings.paths.processed_dir, embedder, reranker))
    out = settings.paths.eval_dir / "retrieval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
