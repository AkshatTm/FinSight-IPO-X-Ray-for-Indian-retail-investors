"""Check the claims that carry no number against the passages they cite (P5.5, optional).

The numeric verifier (``verdict.py``) says nothing about a sentence like "Kotak Mahindra Capital
is a book-running lead manager". An NLI model can: premise = the cited passage text, hypothesis =
the sentence. This module holds only the logic; the model is a ``Scorer`` passed in, so the module
imports no torch and the tests need no model. ``verify.nli`` is off by default and off in
``deploy_cpu``; the product does not show its marks yet (no contract change was made), it is an
evaluation tool (``evaluate/nli_eval.py``).

Three labels, mirroring the numeric marks: ``entailed`` (the passage supports the sentence),
``contradicted`` (it disagrees) and ``neutral`` (the passage does not say: unverifiable). A label
needs probability ``min_prob``; below that the claim is ``neutral``, never a guess.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from finsight.core.schemas import Passage
from finsight.verify.claims import mask_citations, split_claims

Label = Literal["entailed", "contradicted", "neutral"]
LABELS: tuple[Label, ...] = ("entailed", "contradicted", "neutral")
Scorer = Callable[[str, str], dict[str, float]]  # (premise, hypothesis) -> probability per label
MAX_PREMISE_CHARS = 1500
MIN_WORDS = 3
_SPACE_BEFORE_STOP = re.compile(r"\s+([.!?।])")
_NOT_FOUND = re.compile(r"could not find|नहीं मिली", re.IGNORECASE)


@dataclass(frozen=True)
class ClaimCheck:
    """The NLI label for one answer sentence against its cited passages."""

    sentence: str
    label: Label
    probability: float
    cited: list[int]


def decide(probabilities: dict[str, float], min_prob: float = 0.5) -> tuple[Label, float]:
    """The most probable label, or ``neutral`` when no label reaches ``min_prob``."""
    best: Label = max(LABELS, key=lambda lab: probabilities.get(lab, 0.0))
    top = probabilities.get(best, 0.0)
    return (best, top) if top >= min_prob else ("neutral", probabilities.get("neutral", 0.0))


def premise_for(cited: list[int], passages: list[Passage]) -> str:
    """Text of the cited passages (``[n]`` is ``passages[n - 1]``), or the best three if none."""
    chosen = [passages[n - 1] for n in cited if 1 <= n <= len(passages)] or passages[:3]
    return " ".join(p.text for p in chosen)[:MAX_PREMISE_CHARS]


def check_claims(
    answer: str, passages: list[Passage], scorer: Scorer, min_prob: float = 0.5
) -> list[ClaimCheck]:
    """One check per sentence that has no number, is not a "not found" reply and has real words."""
    masked = mask_citations(answer)
    out: list[ClaimCheck] = []
    for item in split_claims(answer, len(passages)):
        if item.numbers:
            continue  # the numeric verifier owns these
        lo, hi = item.claim.char_span
        sentence = _SPACE_BEFORE_STOP.sub(r"\1", " ".join(masked[lo:hi].split()))
        if len(sentence.split()) < MIN_WORDS or _NOT_FOUND.search(sentence):
            continue
        label, prob = decide(scorer(premise_for(item.claim.cited, passages), sentence), min_prob)
        out.append(ClaimCheck(sentence, label, prob, list(item.claim.cited)))
    return out
