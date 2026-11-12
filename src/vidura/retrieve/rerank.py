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
    """A cross-encoder that scores query-passage pairs."""

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
        precision: str = "auto",
        swap_inputs: bool = False,
    ) -> None:
        """``precision``: "fp16", "fp32" or "auto" (fp16 on CUDA, fp32 on CPU).
        ``swap_inputs`` puts the passage first; only the reranker experiment uses it."""
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_len, self.batch, self.swap_inputs = max_len, batch, swap_inputs
        self._tok = AutoTokenizer.from_pretrained(model)
        half = precision == "fp16" or (precision == "auto" and self.device == "cuda")
        dtype = torch.float16 if half else torch.float32
        self._model = (
            AutoModelForSequenceClassification.from_pretrained(model, dtype=dtype)
            .to(self.device)
            .eval()
        )

    def score(self, query: str, texts: list[str]) -> list[float]:
        """Score the pairs in batches with the PyTorch model."""
        scores: list[float] = []
        with self._torch.no_grad():
            for start in range(0, len(texts), self.batch):
                chunk = texts[start : start + self.batch]
                first, second = ([query] * len(chunk), chunk)
                if self.swap_inputs:
                    first, second = second, first
                enc = self._tok(
                    first, second, padding=True,
                    truncation="only_second" if not self.swap_inputs else "only_first",
                    max_length=self.max_len, return_tensors="pt",
                ).to(self.device)  # fmt: skip
                logits = self._model(**enc).logits.view(-1).float().cpu().tolist()
                scores.extend(logits)
        return scores


class OnnxReranker:
    """The same cross-encoder as an ONNX graph on CPU (fp32 or int8-quantised). Needs ``onnx``."""

    def __init__(self, path: str, model: str = BGE_RERANKER, max_len: int = 512, batch: int = 4):
        import onnxruntime as ort
        from transformers import AutoTokenizer

        self.max_len, self.batch = max_len, batch
        self._tok = AutoTokenizer.from_pretrained(model)
        self._session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        self._inputs = {i.name for i in self._session.get_inputs()}

    def score(self, query: str, texts: list[str]) -> list[float]:
        """Score the pairs in batches with the ONNX model."""
        scores: list[float] = []
        for start in range(0, len(texts), self.batch):
            chunk = texts[start : start + self.batch]
            enc = self._tok(
                [query] * len(chunk), chunk, padding=True, truncation="only_second",
                max_length=self.max_len, return_tensors="np",
            )  # fmt: skip
            feed = {k: v for k, v in enc.items() if k in self._inputs}
            logits = self._session.run(None, feed)[0]
            scores.extend(float(x) for x in logits.reshape(-1))
        return scores
