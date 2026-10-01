"""One IPO's search index and the ``Retriever`` that answers questions with it.

Search path (02 section 11): BM25 and dense lists -> reciprocal rank fusion -> rerank the top
``pool`` -> top ``top_k``. Each stage is optional and the result says which ones ran (``method``),
because the abstain threshold means different things on different score scales: a reranker logit,
a fused RRF score or a raw BM25 score. Thresholds are therefore kept per method and tuned on the
dev questions only (``retrieve.evaluate``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from finsight.core.schemas import Passage
from finsight.retrieve.bm25 import BM25Index
from finsight.retrieve.boost import inject, prospectus_first
from finsight.retrieve.dense import DenseIndex, Embedder
from finsight.retrieve.fuse import rrf
from finsight.retrieve.rerank import Reranker

POOL = 20  # candidates sent to the reranker
TOP_K = 5
CHUNKS_FILE = "chunks.jsonl"
DENSE_FILE = "dense.npy"


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float  # on the scale of ``SearchResult.method``
    rank: int  # 1-based


@dataclass(frozen=True)
class SearchResult:
    hits: list[Hit]
    method: str  # "bm25", "hybrid" or "hybrid+rerank"
    abstain: bool
    top_score: float | None
    notes: list[str] = field(default_factory=list)  # e.g. why a stage was skipped


def index_dir(processed_dir: Path, ipo_id: str) -> Path:
    return processed_dir / ipo_id / "index"


class IpoIndex:
    """Passages of one IPO (both documents) with their BM25 and optional dense index."""

    def __init__(self, passages: list[Passage], dense: DenseIndex | None = None) -> None:
        if dense is not None and len(dense.vectors) != len(passages):
            raise ValueError(f"{len(dense.vectors)} vectors for {len(passages)} passages")
        self.passages = passages
        self.bm25 = BM25Index([p.text for p in passages])
        self.dense = dense

    @classmethod
    def build(cls, passages: list[Passage], embedder: Embedder | None = None) -> IpoIndex:
        dense = DenseIndex.build([p.text for p in passages], embedder) if embedder else None
        return cls(passages, dense)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        lines = (p.model_dump_json() for p in self.passages)
        (directory / CHUNKS_FILE).write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )
        if self.dense is not None:
            self.dense.save(directory / DENSE_FILE)

    @classmethod
    def load(cls, directory: Path) -> IpoIndex:
        path = directory / CHUNKS_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"{path} missing; run `python -m finsight.pipeline build --stage index`"
            )
        rows = path.read_text(encoding="utf-8").splitlines()
        passages = [Passage.model_validate(json.loads(line)) for line in rows if line]
        dense_path = directory / DENSE_FILE
        return cls(passages, DenseIndex.load(dense_path) if dense_path.exists() else None)


class Retriever:
    def __init__(
        self,
        processed_dir: Path | None = None,
        *,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
        thresholds: dict[str, float] | None = None,
        pool: int = POOL,
        top_k: int = TOP_K,
    ) -> None:
        self.processed_dir = processed_dir
        self.embedder, self.reranker = embedder, reranker
        self.thresholds = thresholds or {}
        self.pool, self.top_k = pool, top_k
        self._indexes: dict[str, IpoIndex] = {}

    def add(self, ipo_id: str, index: IpoIndex) -> None:
        self._indexes[ipo_id] = index

    def index(self, ipo_id: str) -> IpoIndex:
        if ipo_id not in self._indexes:
            if self.processed_dir is None:
                raise KeyError(f"no index for {ipo_id!r}")
            self._indexes[ipo_id] = IpoIndex.load(index_dir(self.processed_dir, ipo_id))
        return self._indexes[ipo_id]

    def search(self, question: str, ipo_id: str, top_k: int | None = None) -> SearchResult:
        index = self.index(ipo_id)
        k = top_k or self.top_k
        notes: list[str] = []
        bm25_hits = index.bm25.search(question, k=self.pool)
        dense_hits: list[tuple[int, float]] = []
        if self.embedder is not None and index.dense is not None:
            try:
                dense_hits = index.dense.search(self.embedder.embed([question])[0], k=self.pool)
            except Exception as exc:  # dense is an upgrade, never a single point of failure
                notes.append(f"dense skipped: {exc}")
        elif self.embedder is not None:
            notes.append("dense skipped: this IPO has no dense index")

        if dense_hits:
            fused = rrf([[str(i) for i, _ in bm25_hits], [str(i) for i, _ in dense_hits]])
            order = [(int(i), s) for i, s in fused]
            method = "hybrid"
        else:
            order = bm25_hits
            method = "bm25"
        order = inject(question, index.passages, order, self.pool)
        if self.reranker is None:
            # No reranker to judge them: cover passages lead (at most two) instead of trailing.
            extra = order[self.pool :]
            order = extra[:2] + order[: self.pool]

        if self.reranker is not None and order:
            try:
                scores = self.reranker.score(question, [index.passages[i].text for i, _ in order])
                order = sorted(
                    ((i, s) for (i, _), s in zip(order, scores, strict=True)), key=lambda t: -t[1]
                )
                method += "+rerank"
            except Exception as exc:
                notes.append(f"rerank skipped: {exc}")

        order = prospectus_first(question, index.passages, order)
        hits = [
            Hit(passage=index.passages[i], score=s, rank=r)
            for r, (i, s) in enumerate(order[:k], start=1)
        ]
        top = hits[0].score if hits else None
        threshold = self.thresholds.get(method)
        abstain = not hits or (threshold is not None and top is not None and top < threshold)
        return SearchResult(hits=hits, method=method, abstain=abstain, top_score=top, notes=notes)
