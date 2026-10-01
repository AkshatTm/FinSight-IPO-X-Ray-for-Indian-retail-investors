"""Advice, forecast and privacy guard (no model call; decided on the question alone)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from finsight.guard.advice import AdviceCheck, check_advice, normalize_question
from finsight.guard.facts import Fact, facts_payload, refusal_text
from finsight.guard.privacy import OutputCheck, PrivacyCheck, check_output, check_privacy


@dataclass(frozen=True)
class GuardResult:
    blocked: bool
    reason: Literal["advice_intent", "privacy"] | None = None
    category: str | None = None
    matched: str | None = None


def check_question(question: str) -> GuardResult:
    """Privacy first (it is the stricter refusal), then advice, forecasts and ratings."""
    privacy = check_privacy(question)
    if privacy.blocked:
        return GuardResult(True, privacy.reason, privacy.category, privacy.matched)
    advice = check_advice(question)
    if advice.blocked:
        return GuardResult(True, advice.reason, advice.category, advice.matched)
    return GuardResult(False)


__all__ = [
    "AdviceCheck",
    "Fact",
    "GuardResult",
    "OutputCheck",
    "PrivacyCheck",
    "check_advice",
    "check_output",
    "check_privacy",
    "check_question",
    "facts_payload",
    "normalize_question",
    "refusal_text",
]
