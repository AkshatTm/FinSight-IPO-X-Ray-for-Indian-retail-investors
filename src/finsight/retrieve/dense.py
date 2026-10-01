"""Meaning-based search: embed passages and questions, compare by cosine similarity.

An *embedding* turns text into a vector so that texts with similar meaning point the same way
(bge-m3 also works across English and Hindi, which is why a Hindi question can find an English
passage). Vectors are L2-normalised, so the inner product is the cosine. A single IPO has a few
thousand passages, so exact search with one matrix product is faster than building an ANN index
and has no recall loss (ADR-040).

The model is behind the ``Embedder`` protocol: offline builds use ``BgeM3Embedder`` on the GPU;
tests use a tiny fake.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

Vectors = npt.NDArray[np.float32]
BGE_M3 = "BAAI/bge-m3"


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> Vectors:
        """One L2-normalised float32 row per text."""
        ...


def normalise(vectors: npt.NDArray[Any]) -> Vectors:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.maximum(norms, 1e-12)).astype(np.float32)


class BgeM3Embedder:
    """bge-m3 through ``transformers`` (CLS pooling, as the model card says). Needs the ml group."""

    def __init__(
        self, model: str = BGE_M3, device: str | None = None, max_len: int = 512, batch: int = 16
    ) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_len, self.batch = max_len, batch
        self._tok = AutoTokenizer.from_pretrained(model)
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self._model = AutoModel.from_pretrained(model, torch_dtype=dtype).to(self.device).eval()

    def embed(self, texts: list[str]) -> Vectors:
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))  # similar lengths per batch
        out = np.zeros((len(texts), self._model.config.hidden_size), dtype=np.float32)
        with self._torch.no_grad():
            for start in range(0, len(order), self.batch):
                idx = order[start : start + self.batch]
                enc = self._tok(
                    [texts[i] for i in idx], padding=True, truncation=True,
                    max_length=self.max_len, return_tensors="pt",
                ).to(self.device)  # fmt: skip
                cls = self._model(**enc).last_hidden_state[:, 0].float().cpu().numpy()
                out[idx] = cls
        return normalise(out)


class DenseIndex:
    """All passage vectors of one IPO; row ``i`` belongs to passage ``i`` of its chunk list."""

    def __init__(self, vectors: Vectors) -> None:
        self.vectors = vectors

    @classmethod
    def build(cls, texts: list[str], embedder: Embedder, batch: int = 256) -> DenseIndex:
        if not texts:
            return cls(np.zeros((0, 1), dtype=np.float32))
        parts = [embedder.embed(texts[i : i + batch]) for i in range(0, len(texts), batch)]
        return cls(np.vstack(parts).astype(np.float32))

    def search(self, query_vector: Vectors, k: int = 20) -> list[tuple[int, float]]:
        """``(position, cosine)`` best first."""
        if not len(self.vectors):
            return []
        scores = self.vectors @ query_vector.reshape(-1)
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]

    def save(self, path: Path) -> None:
        np.save(path, self.vectors.astype(np.float16))  # half the disk; cosine order is unchanged

    @classmethod
    def load(cls, path: Path) -> DenseIndex:
        return cls(np.load(path).astype(np.float32))


def write_meta(path: Path, model: str, n: int) -> None:
    path.write_text(json.dumps({"model": model, "n": n}) + "\n", encoding="utf-8")
