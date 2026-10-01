"""Rung 3 of the ladder: the QA model fine-tuned on our weak labels (P2.5, ADR-043).

Same reading code as the pretrained rung (``qa_pretrained.default_answerer``), different
weights: ``models/extractor/seed-<n>`` holds the best epoch of each of the three Kaggle runs. Spans
may be up to 128 tokens, as in training, because promoters and managers are whole-list spans.
Weights are never committed; a missing folder is an error that says how to get it.
"""

from __future__ import annotations

from pathlib import Path

from finsight.core.config import get_settings
from finsight.extract.qa_pretrained import (
    MAX_ANSWER_TOKENS,
    Answerer,
    QAExtractor,
    default_answerer,
)

SEEDS = (13, 42, 2026)
DEFAULT_SEED = 2026  # best dev NVM of the three seeds; the pipeline runs with it (ADR-018)
__all__ = ["DEFAULT_SEED", "MAX_ANSWER_TOKENS", "SEEDS", "FineTunedExtractor", "weights_dir"]


def weights_dir(seed: int, models_dir: Path | None = None) -> Path:
    return (models_dir or Path(get_settings().paths.models_dir)) / "extractor" / f"seed-{seed}"


class FineTunedExtractor(QAExtractor):
    """Implements ``core.interfaces.Extractor``; one instance per seed."""

    name = "qa_finetuned"

    def __init__(
        self,
        seed: int,
        answerer: Answerer | None = None,
        top_k: int = 3,
        models_dir: Path | None = None,
    ) -> None:
        super().__init__(answerer, top_k)
        self.seed = seed
        self.weights = weights_dir(seed, models_dir)

    def _answer(self, question: str, contexts: list[str]):  # type: ignore[no-untyped-def]
        if self._answerer is None:
            if not (self.weights / "config.json").exists():
                raise FileNotFoundError(
                    f"{self.weights} not found; fetch the weights with "
                    f"`python -m finsight.weaklabel.kaggle fetch {self.seed}`"
                )
            self._answerer = default_answerer(
                str(self.weights), max_answer_tokens=MAX_ANSWER_TOKENS
            )
        return self._answerer(question, contexts)
