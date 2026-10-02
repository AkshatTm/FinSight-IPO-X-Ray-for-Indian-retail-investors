"""Rung 4 of the ladder: a BiLSTM-CRF tagger trained on our weak labels (P5.3, E11).

It reads a passage and tags every token ``B-<field>`` / ``I-<field>`` / ``O`` for all eight ladder
fields at once, so a passage is tagged once and each field takes its own span. No question, no
pretrained knowledge: word vectors were learned from our own text. Weights come from Kaggle
(``python -m finsight.weaklabel.kaggle fetch bilstm-<seed>``) into ``models/bilstm_crf/seed-<n>``
and are never committed. Runs on the CPU: the network has about a million parameters.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from finsight.core.config import get_settings
from finsight.core.schemas import FieldSpec
from finsight.extract.passages import QAPassage
from finsight.extract.qa_pretrained import MAX_ANSWER_TOKENS, QAExtractor, RawAnswer
from finsight.extract.tokens import tokenize

SEEDS = (13, 42, 2026)
BATCH = 16
MAX_TOKENS = 450  # a passage is at most 1,500 characters; longer ones are cut, never skipped


@dataclass(frozen=True)
class TaggedSpan:
    field: str
    start: int  # characters inside the passage
    end: int
    score: float
    tokens: int


# passage texts -> the spans tagged in each (all fields)
Tagger = Callable[[list[str]], list[list[TaggedSpan]]]


def weights_dir(seed: int, models_dir: Path | None = None) -> Path:
    return (models_dir or Path(get_settings().paths.models_dir)) / "bilstm_crf" / f"seed-{seed}"


def load_tagger(directory: Path) -> Tagger:
    """The trained network as a function from passages to tagged spans (CPU)."""
    import torch

    from finsight.extract.bilstm_crf_model import (
        BiLSTMCRF,
        Vocab,
        pad_batch,
        predict_with_confidence,
        spans_from_tags,
    )

    vocab = Vocab.from_json(json.loads((directory / "vocab.json").read_text(encoding="utf-8")))
    hp = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    net = BiLSTMCRF(len(vocab.words), len(vocab.chars), len(vocab.tags), **hp)
    net.load_state_dict(torch.load(directory / "model.pt", map_location="cpu", weights_only=True))
    net.eval()

    def tag(texts: list[str]) -> list[list[TaggedSpan]]:
        out: list[list[TaggedSpan]] = []
        for lo in range(0, len(texts), BATCH):
            batch = [tokenize(t)[:MAX_TOKENS] for t in texts[lo : lo + BATCH]]
            words, chars, mask = pad_batch(vocab, [[tok for tok, _, _ in b] for b in batch])
            paths, probs = predict_with_confidence(net, words, chars, mask)
            for tokens, path, prob in zip(batch, paths, probs, strict=True):
                spans = []
                for field, first, last in spans_from_tags([vocab.tags[i] for i in path]):
                    conf = sum(prob[first : last + 1]) / (last - first + 1)
                    spans.append(
                        TaggedSpan(field, tokens[first][1], tokens[last][2], conf, last - first + 1)
                    )
                out.append(spans)
        return out

    return tag


class BiLSTMCRFExtractor(QAExtractor):
    """Implements ``core.interfaces.Extractor``; one instance per seed."""

    name = "bilstm_crf"

    def __init__(
        self,
        seed: int,
        tagger: Tagger | None = None,
        top_k: int = 3,
        models_dir: Path | None = None,
    ) -> None:
        super().__init__(None, top_k)
        self.seed = seed
        self.weights = weights_dir(seed, models_dir)
        self._tagger = tagger
        self._memo: dict[str, list[TaggedSpan]] = {}  # tagging does not depend on the field

    def _spans(self, texts: list[str]) -> list[list[TaggedSpan]]:
        if self._tagger is None:
            if not (self.weights / "model.pt").exists():
                raise FileNotFoundError(
                    f"{self.weights} not found; fetch the weights with "
                    f"`python -m finsight.weaklabel.kaggle fetch bilstm-{self.seed}`"
                )
            self._tagger = load_tagger(self.weights)
        todo = [t for t in dict.fromkeys(texts) if t not in self._memo]
        for text, spans in zip(todo, self._tagger(todo) if todo else [], strict=True):
            self._memo[text] = spans
        return [self._memo[t] for t in texts]

    def _answers(self, field: FieldSpec, passages: list[QAPassage]) -> list[RawAnswer | None]:
        answers: list[RawAnswer | None] = []
        for passage, spans in zip(passages, self._spans([p.text for p in passages]), strict=True):
            mine = [s for s in spans if s.field == field.id and s.tokens <= MAX_ANSWER_TOKENS]
            best = max(mine, key=lambda s: s.score, default=None)
            answers.append(
                RawAnswer(passage.text[best.start : best.end], best.score, best.start, best.end)
                if best
                else None
            )
        return answers
