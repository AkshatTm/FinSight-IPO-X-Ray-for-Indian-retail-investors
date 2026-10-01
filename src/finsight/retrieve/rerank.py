"""Second-look ranking: a cross-encoder reads the question and one passage *together*.

First-stage search (BM25, dense) scores the question and each passage separately, which is fast
but coarse. A cross-encoder (bge-reranker-v2-m3) reads both at once and is much better at telling
"the registrar is KFin" from a passage that merely mentions registrars. It is too slow for every
passage, so it re-orders only the top ``pool`` candidates. If the model is missing or fails, the
retriever keeps the fused order (BM25-only fallback) instead of failing.
"""

from __future__ import annotations

from typing import Protocol

BGE_RERANKER = "BAAI/bge-reranker-v2-m3"


class Reranker(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]:
        """Higher is more relevant; the scale is the model's (bge: a raw logit)."""
        ...


class CrossEncoderReranker:
    """bge-reranker-v2-m3 through ``transformers``. Needs the ml group."""

    def __init__(
        self,
        model: str = BGE_RERANKER,
        device: str | None = None,
        max_len: int = 512,
        batch: int = 8,
    ) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_len, self.batch = max_len, batch
        self._tok = AutoTokenizer.from_pretrained(model)
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self._model = (
            AutoModelForSequenceClassification.from_pretrained(model, torch_dtype=dtype)
            .to(self.device)
            .eval()
        )

    def score(self, query: str, texts: list[str]) -> list[float]:
        scores: list[float] = []
        with self._torch.no_grad():
            for start in range(0, len(texts), self.batch):
                chunk = texts[start : start + self.batch]
                enc = self._tok(
                    [query] * len(chunk), chunk, padding=True, truncation="only_second",
                    max_length=self.max_len, return_tensors="pt",
                ).to(self.device)  # fmt: skip
                logits = self._model(**enc).logits.view(-1).float().cpu().tolist()
                scores.extend(logits)
        return scores
