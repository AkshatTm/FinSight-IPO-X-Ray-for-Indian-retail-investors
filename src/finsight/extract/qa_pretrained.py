"""Rung 2 of the ladder: a pretrained extractive question-answering model, no fine-tuning.

The model (``deepset/deberta-v3-base-squad2``) is given a field's question and one passage at a
time and points at the span of the passage that answers it. It was trained on general English
(SQuAD 2.0), not on IPO documents, so it is the "what do you get for free?" baseline between
the rules (Rung 1) and our fine-tuned model (Rung 3). It runs on the GPU in fp16 and is only
ever used offline; weights are downloaded to the Hugging Face cache, never into the repo.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from finsight.core.schemas import (
    Candidate,
    FieldSpec,
    ListValue,
    Money,
    ParsedDoc,
    Placeholder,
    Range,
    Section,
    Table,
    TextValue,
    Value,
)
from finsight.extract.passages import build_passages
from finsight.normalize import parse_amount

MODEL = "deepset/deberta-v3-base-squad2"
MIN_SCORE = 0.05  # below this the model is guessing
_UNIT_AFTER = re.compile(r"^\s*(million|crore|lakh|billion|mn|cr)\b", re.IGNORECASE)
_SPLIT_LIST = re.compile(r",|;|\band\b|\n", re.IGNORECASE)
_DIGITS = re.compile(r"^\d[\d,]*(?:\.\d+)?$")
_MARKS = re.compile(r"[\^*†‡]")  # footnote marks printed after numbers ("19,000^ million")


@dataclass(frozen=True)
class RawAnswer:
    text: str
    score: float
    start: int  # character offsets inside the passage text
    end: int


# (question, passages) -> one answer (or None = "no answer") per passage
Answerer = Callable[[str, list[str]], list[RawAnswer | None]]


def default_answerer(model: str = MODEL, batch_size: int = 16) -> Answerer:
    """The real model on the GPU in fp16 (CPU fp32 otherwise).

    transformers 5 no longer ships the ``question-answering`` pipeline, so the span is found
    here: the model scores every token as a possible start and end; the answer is the span with
    the highest start x end probability, compared with the "no answer" score (the first token),
    exactly as SQuAD 2.0 models are trained to be read.
    """
    import torch
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer

    cuda = torch.cuda.is_available()
    device = torch.device("cuda" if cuda else "cpu")
    tok = AutoTokenizer.from_pretrained(model)
    net = AutoModelForQuestionAnswering.from_pretrained(
        model, torch_dtype=torch.float16 if cuda else torch.float32
    )
    net = net.to(device).eval()  # type: ignore[arg-type]
    max_answer_tokens, top_n = 40, 20

    def answer(question: str, contexts: list[str]) -> list[RawAnswer | None]:
        best: list[RawAnswer | None] = [None] * len(contexts)
        best_score = [0.0] * len(contexts)
        null_score = [1.0] * len(contexts)
        for lo in range(0, len(contexts), batch_size):
            batch = contexts[lo : lo + batch_size]
            enc = tok(
                [question] * len(batch),
                batch,
                truncation="only_second",
                max_length=384,
                stride=128,
                return_overflowing_tokens=True,
                return_offsets_mapping=True,
                padding=True,
                return_tensors="pt",
            )
            owner = enc.pop("overflow_to_sample_mapping").tolist()
            offsets = enc.pop("offset_mapping").tolist()
            with torch.no_grad():
                out = net(**{k: v.to(device) for k, v in enc.items()})
            start_p = out.start_logits.float().softmax(-1).cpu()
            end_p = out.end_logits.float().softmax(-1).cpu()
            for i, sample in enumerate(owner):
                seq = enc.sequence_ids(i)
                ctx = [t for t, s in enumerate(seq) if s == 1]
                idx = lo + sample
                null_score[idx] = min(null_score[idx], float(start_p[i, 0] * end_p[i, 0]))
                starts = sorted(ctx, key=lambda t: -float(start_p[i, t]))[:top_n]
                ends = sorted(ctx, key=lambda t: -float(end_p[i, t]))[:top_n]
                for s in starts:
                    for e in ends:
                        if s <= e < s + max_answer_tokens:
                            score = float(start_p[i, s] * end_p[i, e])
                            if score > best_score[idx]:
                                a, b = offsets[i][s][0], offsets[i][e][1]
                                best_score[idx] = score
                                best[idx] = RawAnswer(contexts[idx][a:b], score, a, b)
        return [
            ans if ans is not None and best_score[n] > null_score[n] and ans.text.strip() else None
            for n, ans in enumerate(best)
        ]

    return answer


def _to_value(kind: str, answer: RawAnswer, context: str) -> Value | None:
    text = _MARKS.sub("", answer.text).strip()
    if kind == "money":
        if _DIGITS.match(text):  # a bare number: the unit and the rupee sign sit around the span
            unit = _UNIT_AFTER.match(context[answer.end :])
            rupee = context[: answer.start].rstrip().endswith(("₹", "Rs.", "Rs", "INR"))
            if not (unit or rupee):
                return None
            value = parse_amount(f"₹ {text} {unit.group(1)}" if unit else f"₹ {text}")
        else:
            value = parse_amount(text)
        return value if isinstance(value, Money | Placeholder) else None
    if kind == "count":
        value = parse_amount(f"{text} equity shares" if _DIGITS.match(text) else text)
        return value if value is not None and value.kind in ("count", "placeholder") else None
    if kind == "range":
        value = parse_amount(text)
        return value if isinstance(value, Range) else None
    if kind == "text":
        return TextValue(text=text) if 0 < len(text) <= 120 else None
    if kind == "list":
        items = [i.strip(" ,.;") for i in _SPLIT_LIST.split(text)]
        items = [i for i in items if i]
        return ListValue(items=items) if items and all(len(i) <= 120 for i in items) else None
    return None


class QAExtractor:
    """Implements ``core.interfaces.Extractor``; fields opt in with ``fallback: qa_pretrained``."""

    name = "qa_pretrained"

    def __init__(self, answerer: Answerer | None = None, top_k: int = 3) -> None:
        self._answerer = answerer
        self.top_k = top_k

    def _answer(self, question: str, contexts: list[str]) -> list[RawAnswer | None]:
        if self._answerer is None:
            self._answerer = default_answerer()
        return self._answerer(question, contexts)

    def extract(
        self,
        doc: ParsedDoc,
        sections: list[Section],
        tables: list[Table],
        field: FieldSpec,
    ) -> list[Candidate]:
        if field.fallback != self.name or not field.questions:
            return []
        passages = build_passages(doc, sections, field)
        answers = self._answer(field.questions[0], [p.text for p in passages])
        found: list[Candidate] = []
        seen: set[str] = set()
        for passage, answer in zip(passages, answers, strict=True):
            if answer is None or answer.score < MIN_SCORE:
                continue
            value = _to_value(field.type, answer, passage.text)
            if value is None or (key := value.model_dump_json()) in seen:
                continue
            seen.add(key)
            found.append(
                Candidate(
                    field_id=field.id,
                    extractor=self.name,
                    doc_type=doc.doc_type,
                    raw=answer.text.strip(),
                    value=value,
                    page=passage.page,
                    printed_page=passage.printed_page,
                    score=round(answer.score, 4),
                    passage_id=passage.id,
                )
            )
        return sorted(found, key=lambda c: (-c.score, c.page))[: self.top_k]
