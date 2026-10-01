"""Is a model's answer right? Scored with the P3.3 verifier against the gold value (ADR-020).

The first bake-off said "yes" whenever the gold digits appeared anywhere in the answer, so
"₹26.260 करोड़" (a hundred times too small) and "₹3,548 million" (another metric) were marked
correct. Here the *gold value is the evidence*: a one-line passage "<field label>: <gold value>"
goes through ``verify_answer`` and an answer is right only when its numbers are ✅ against it,
which compares value, **unit** (a crore is not a million) and **metric** (the total is not the
fresh issue) exactly as the live verifier does. A gold value that is a name (the registrar) has no
amount to verify; there the name must appear in the answer.

* ``yes``: every gold amount is matched by a verified answer number, none is contradicted.
* ``partial``: matched, but another number of the answer contradicts the gold (unit or metric).
* ``no``: the gold value is missing, wrong, in another unit, or under another metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from finsight.core.schemas import Passage
from finsight.normalize import parse_amounts
from finsight.verify import verify_answer

Judgement = Literal["yes", "partial", "no"]
_NOISE = ("₹", "MILLION", "EQUITY SHARES", "CRORE")


@dataclass(frozen=True)
class Score:
    correct: Judgement
    why: str  # reason code of the deciding check, or "name_found" / "name_missing"


def compact(text: str) -> str:
    """Letters and digits only, lower case: "₹ 4,720.00 million" -> "472000million"."""
    return "".join(ch for ch in text.casefold() if ch.isalnum())


def _gold_text(value_raw: object) -> str:
    while isinstance(value_raw, list):
        value_raw = value_raw[0]
    return str(value_raw)


def gold_passage(label: str, value_raw: object) -> Passage:
    """The gold value as a passage the verifier can use as evidence."""
    return Passage(
        id="gold:p1:c0", ipo_id="gold", doc_type="rhp", section_id="gold", page_start=1,
        page_end=1, text=f"{label}: {_gold_text(value_raw)}", char_to_bbox=[],
    )  # fmt: skip


def score_answer(answer: str, label: str, value_raw: object) -> Score:
    """Judge ``answer`` against the gold value of the field ``label``."""
    gold = _gold_text(value_raw)
    n_gold = len(parse_amounts(gold))
    if n_gold == 0:
        needle = compact(gold)
        found = bool(needle) and needle in compact(answer)
        return Score("yes" if found else "no", "name_found" if found else "name_missing")
    verdict = verify_answer(answer, [gold_passage(label, gold)])
    verified = {
        v.check.evidence_char_span for v in verdict.verdicts if v.check.status == "verified"
    }
    contradicted = [
        v.check.reason_code for v in verdict.verdicts if v.check.status == "contradicted"
    ]
    if len(verified) >= n_gold:
        return Score(
            "partial" if contradicted else "yes", contradicted[0] if contradicted else "verified"
        )
    if contradicted:
        return Score("no", contradicted[0])
    unverified = [v.check.reason_code for v in verdict.verdicts]
    return Score("no", unverified[0] if unverified else "no_number")
