from pathlib import Path

import numpy as np
import pytest

from finsight.core.schemas import Passage
from finsight.retrieve.dense import DenseIndex, Vectors, normalise
from finsight.retrieve.fuse import rrf
from finsight.retrieve.retriever import IpoIndex, Retriever, index_dir

VOCAB = [
    "registrar",
    "kfin",
    "fresh",
    "issue",
    "million",
    "brlm",
    "axis",
    "risk",
    "business",
    "fee",
]


class BagEmbedder:
    """Counts vocabulary words; 'cost' is a synonym of 'fee' to mimic meaning-based matching."""

    def embed(self, texts: list[str]) -> Vectors:
        rows = []
        for t in texts:
            words = t.lower().replace("cost", "fee").split()
            rows.append([words.count(w) for w in VOCAB])
        return normalise(np.array(rows, dtype=np.float32) + 1e-6)


class FixedReranker:
    def __init__(self, preferred: str) -> None:
        self.preferred = preferred

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [5.0 if self.preferred in t else -3.0 for t in texts]


class BrokenReranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        raise RuntimeError("out of memory")


def passage(k: int, text: str, doc_type: str = "rhp", page: int = 1) -> Passage:
    return Passage(
        id=f"acme-2025:p{page}:c{k}", ipo_id="acme-2025", doc_type=doc_type,  # type: ignore[arg-type]
        section_id="s", page_start=page, page_end=page, text=text, char_to_bbox=[],
    )  # fmt: skip


PASSAGES = [
    passage(0, "KFin Technologies is the registrar to the offer"),
    passage(1, "The fresh issue is 4,720 million"),
    passage(2, "Axis Capital is the BRLM", page=2),
    passage(3, "Risk factors of our business", page=3),
    passage(4, "The fee payable to the registrar is disclosed", page=4),
]


def test_rrf_rewards_agreement_and_keeps_ties_stable() -> None:
    fused = rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert [i for i, _ in fused][:2] == ["a", "b"]  # a and b tie; first list's order wins
    assert fused[0][1] == pytest.approx(1 / 61 + 1 / 62)
    assert [i for i, _ in rrf([["x"], ["y"]])] == ["x", "y"]
    assert rrf([]) == []


def test_bm25_only_search_when_no_embedder() -> None:
    r = Retriever()
    r.add("acme-2025", IpoIndex(PASSAGES))
    res = r.search("who is the registrar kfin", "acme-2025")
    assert res.method == "bm25"
    assert res.hits[0].passage.id == "acme-2025:p1:c0"
    assert res.hits[0].rank == 1


def test_hybrid_uses_dense_for_synonyms() -> None:
    r = Retriever(embedder=BagEmbedder())
    r.add("acme-2025", IpoIndex.build(PASSAGES, BagEmbedder()))
    res = r.search(
        "what is the cost", "acme-2025"
    )  # no shared word with the passage except meaning
    assert res.method == "hybrid"
    assert res.hits[0].passage.id == "acme-2025:p4:c4"


def test_rerank_reorders_the_pool_and_fallback_survives_a_crash() -> None:
    index = IpoIndex.build(PASSAGES, BagEmbedder())
    r = Retriever(embedder=BagEmbedder(), reranker=FixedReranker("Axis"))
    r.add("acme-2025", index)
    res = r.search("registrar fresh issue axis", "acme-2025")
    assert res.method == "hybrid+rerank"
    assert res.hits[0].passage.text.startswith("Axis")
    assert res.hits[0].score == 5.0

    broken = Retriever(embedder=BagEmbedder(), reranker=BrokenReranker())
    broken.add("acme-2025", index)
    res = broken.search("registrar", "acme-2025")
    assert res.method == "hybrid"  # fell back to the fused order
    assert any("rerank skipped" in n for n in res.notes)
    assert res.hits


def test_abstain_uses_the_threshold_of_the_method_that_ran() -> None:
    index = IpoIndex(PASSAGES)
    r = Retriever(thresholds={"bm25": 1000.0})
    r.add("acme-2025", index)
    assert r.search("registrar", "acme-2025").abstain is True
    r2 = Retriever(thresholds={"hybrid": 1000.0})  # a threshold for another method is not used
    r2.add("acme-2025", index)
    assert r2.search("registrar", "acme-2025").abstain is False


def test_no_match_abstains_with_no_hits() -> None:
    r = Retriever()
    r.add("acme-2025", IpoIndex(PASSAGES))
    res = r.search("zebra", "acme-2025")
    assert res.hits == []
    assert res.abstain is True
    assert res.top_score is None


def test_dense_failure_falls_back_to_bm25() -> None:
    class Down:
        def embed(self, texts: list[str]) -> Vectors:
            raise RuntimeError("model not loaded")

    r = Retriever(embedder=Down())
    r.add("acme-2025", IpoIndex.build(PASSAGES, BagEmbedder()))
    res = r.search("registrar", "acme-2025")
    assert res.method == "bm25"
    assert any("dense skipped" in n for n in res.notes)


def test_index_round_trip_keeps_passages_and_vectors(tmp_path: Path) -> None:
    index = IpoIndex.build(PASSAGES, BagEmbedder())
    index.save(index_dir(tmp_path, "acme-2025"))
    loaded = IpoIndex.load(index_dir(tmp_path, "acme-2025"))
    assert [p.id for p in loaded.passages] == [p.id for p in PASSAGES]
    assert loaded.dense is not None
    assert loaded.dense.vectors.shape == (5, len(VOCAB))
    q = BagEmbedder().embed(["registrar kfin"])[0]
    assert [i for i, _ in loaded.dense.search(q, 2)] == [i for i, _ in index.dense.search(q, 2)]  # type: ignore[union-attr]


def test_retriever_loads_lazily_from_disk_and_reports_missing(tmp_path: Path) -> None:
    IpoIndex(PASSAGES).save(index_dir(tmp_path, "acme-2025"))
    r = Retriever(tmp_path)
    assert r.search("registrar", "acme-2025").hits
    with pytest.raises(FileNotFoundError, match="--stage index"):
        r.search("registrar", "other-2025")


def test_dense_vector_count_must_match_passages() -> None:
    with pytest.raises(ValueError, match="vectors"):
        IpoIndex(PASSAGES, DenseIndex(np.zeros((2, 3), dtype=np.float32)))
