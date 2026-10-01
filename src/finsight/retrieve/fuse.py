"""Reciprocal rank fusion: merge several ranked lists without comparing their scores.

BM25 scores and cosine similarities live on different scales, so adding them is meaningless.
RRF only uses *positions*: an item at rank r in a list earns ``1 / (k + r)``; the scores from every
list are summed. An item that both lists like rises to the top. ``k = 60`` is the standard value.
"""

from __future__ import annotations

from collections.abc import Sequence

RRF_K = 60


def rrf(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """``(id, fused score)`` best first. Ties keep the order of the first list that had them."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: -kv[1])  # sorted() is stable
