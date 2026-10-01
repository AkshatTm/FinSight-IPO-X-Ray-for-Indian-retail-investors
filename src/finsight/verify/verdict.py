"""Verify a whole answer: one verdict per number, and the answer score (02 section 10.3, step 5).

    verdict = verify_answer(answer_text, passages)   # passages as numbered in the prompt

The score is ``verified numbers / all numbers``; an answer without numbers has no score
(``None``), which is not the same as zero. English and Hindi answers take the same path.
"""

from __future__ import annotations

from dataclasses import dataclass

from finsight.core.schemas import CheckResult, Passage
from finsight.verify.claims import mask_citations, split_claims
from finsight.verify.metrics import find_metrics, metric_at
from finsight.verify.numeric_check import check_number, evidence_amounts

MARKS = {"verified": "✅", "unverifiable": "⚠️", "contradicted": "❌"}


@dataclass(frozen=True)
class NumberVerdict:
    index: int  # order of the number in the answer, 0-based (06: verdict event)
    answer_char_span: tuple[int, int]
    metric: str | None
    check: CheckResult


@dataclass(frozen=True)
class AnswerVerdict:
    verdicts: list[NumberVerdict]
    score: float | None

    @property
    def n_numbers(self) -> int:
        return len(self.verdicts)

    @property
    def checks(self) -> list[CheckResult]:
        return [v.check for v in self.verdicts]


def answer_score(checks: list[CheckResult]) -> float | None:
    if not checks:
        return None
    return sum(c.status == "verified" for c in checks) / len(checks)


def verify_answer(answer: str, passages: list[Passage]) -> AnswerVerdict:
    """Check every number in ``answer`` against ``passages`` (``[n]`` is ``passages[n - 1]``)."""
    evidence = evidence_amounts(passages)
    masked = mask_citations(answer)
    verdicts: list[NumberVerdict] = []
    for item in split_claims(answer, len(passages)):
        lo, hi = item.claim.char_span
        sentence = masked[lo:hi]
        hits = find_metrics(sentence)
        where = [(n.start - lo, n.end - lo) for n in item.numbers]
        for number in item.numbers:
            metric = metric_at(sentence, number.start - lo, number.end - lo, hits, where)
            check = check_number(number.amount, metric, evidence, item.claim.cited)
            verdicts.append(NumberVerdict(len(verdicts), (number.start, number.end), metric, check))
    return AnswerVerdict(verdicts, answer_score([v.check for v in verdicts]))


def format_verdicts(verdict: AnswerVerdict) -> str:
    """Plain lines for the CLI: mark, number, reason code, reason."""
    if not verdict.verdicts:
        return "No numbers to verify."
    lines = [
        f"  {MARKS[v.check.status]} {v.check.answer_value.raw if v.check.answer_value else '?'}"
        f"  [{v.check.reason_code}]  {v.check.reason}"
        for v in verdict.verdicts
    ]
    verified = sum(v.check.status == "verified" for v in verdict.verdicts)
    return "\n".join([*lines, f"  score: {verified}/{verdict.n_numbers} numbers verified"])
