"""Keyword search with BM25 (``bm25s``).

BM25 scores a passage by how many of the question's words it contains, weighting rare words more.
It is the always-on rung of retrieval: it needs no model, and it is excellent for exact tokens
such as "KFin" or "4,720". Numbers are tokenised without thousands commas, so "4,720" in a
passage matches "4720" in a question. The index is rebuilt from ``chunks.jsonl`` at load time
(a few thousand passages take well under a second), so there is no index file to keep in sync.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import bm25s

_COMMAS_IN_NUMBER = re.compile(r"(?<=\d),(?=\d)")
_TOKEN = re.compile(r"\d+(?:\.\d+)?|\w+")
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "be",
        "by",
        "with",
        "as",
        "at",
        "from",
        "this",
        "that",
        "it",
        "its",
        "what",
        "which",
        "who",
        "whom",
        "how",
        "much",
        "many",
        "does",
        "do",
        "did",
    ]
)


def tokenize(text: str) -> list[str]:
    """Lower-case words and numbers; commas inside numbers dropped; stop words removed."""
    flat = _COMMAS_IN_NUMBER.sub("", text.lower())
    return [t for t in _TOKEN.findall(flat) if t not in _STOPWORDS]


class BM25Index:
    """BM25 word-match index over passage texts."""

    def __init__(self, texts: Sequence[str]) -> None:
        self.size = len(texts)
        self._index = bm25s.BM25()
        if self.size:
            self._index.index([tokenize(t) or ["∅"] for t in texts], show_progress=False)

    def search(self, query: str, k: int = 20) -> list[tuple[int, float]]:
        """``(position, score)`` best first; passages sharing no query word are left out."""
        tokens = tokenize(query)
        if not tokens or not self.size:
            return []
        ids, scores = self._index.retrieve([tokens], k=min(k, self.size), show_progress=False)
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0], strict=True) if s > 0]
