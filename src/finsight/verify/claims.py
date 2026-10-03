"""Split an answer into claims: one sentence, the amounts in it, the passages it cites.

A claim is what the verifier checks (02 section 10.3, step 1). The same code reads English
and Hindi answers: sentences end at ``.``, ``?``, ``!`` or the danda ``।``. Citation markers
``[2]`` belong to the sentence they follow, even when they sit after its full stop, and are
never read as numbers. Years, page numbers and other bare numbers are not amounts
(``normalize.parse_amounts`` skips anything without a currency, scale word, % or share unit).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsight.core.schemas import Amount, Claim
from finsight.normalize import parse_amounts

_CITATION = re.compile(r"\[(\d{1,3})\]")
# a sentence end, with any citation markers that trail it: "... crore. [1] The offer ..."
_END = re.compile(r"[.!?।](?:\s*\[\d{1,3}\])*(?=\s|$)|\n+")
_ABBREVIATION = re.compile(
    r"(?:\b(?:Rs|Re|No|Nos|Ltd|Pvt|Mr|Mrs|Ms|Dr|Co|Inc|vs|approx|i\.e|e\.g|viz|p|pp)|रु|\b[A-Za-z])$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AnswerNumber:
    """One amount in the answer and where it sits (``answer[start:end]``)."""

    amount: Amount
    start: int
    end: int


@dataclass(frozen=True)
class AnswerClaim:
    """A sentence of the answer and the numbers in it."""

    claim: Claim
    numbers: list[AnswerNumber]


def mask_citations(text: str) -> str:
    """Same length as ``text`` with every ``[n]`` blanked: spans stay valid."""
    return _CITATION.sub(lambda m: " " * len(m.group()), text)


def sentence_spans(answer: str) -> list[tuple[int, int]]:
    """``(start, end)`` of every sentence; trailing citation markers stay with their sentence."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _END.finditer(answer):
        if m.group()[0] == "." and _ABBREVIATION.search(answer[start : m.start()]):
            continue  # "Rs. 300 crore", "M. Kumar"
        spans.append((start, m.end()))
        start = m.end()
    spans.append((start, len(answer)))
    out = []
    for lo, hi in spans:
        text = answer[lo:hi]
        if stripped := text.strip():
            lead = len(text) - len(text.lstrip())
            out.append((lo + lead, lo + lead + len(stripped)))
    return out


def split_claims(answer: str, n_passages: int | None = None) -> list[AnswerClaim]:
    """Every sentence of the answer as a claim; sentences without an amount have no numbers."""
    masked = mask_citations(answer)
    claims = []
    for lo, hi in sentence_spans(answer):
        cited: list[int] = []
        for m in _CITATION.finditer(answer, lo, hi):
            n = int(m.group(1))
            if n >= 1 and (n_passages is None or n <= n_passages) and n not in cited:
                cited.append(n)
        numbers = [
            AnswerNumber(span.amount, lo + span.start, lo + span.end)
            for span in parse_amounts(masked[lo:hi])
        ]
        claim = Claim(
            sentence=answer[lo:hi],
            char_span=(lo, hi),
            amounts=[n.amount for n in numbers],
            cited=cited,
        )
        claims.append(AnswerClaim(claim, numbers))
    return claims
