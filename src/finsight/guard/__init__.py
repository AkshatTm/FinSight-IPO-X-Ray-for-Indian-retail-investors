"""Advice, forecast and privacy guard (no model call; decided on the question alone), and the
forbidden-phrase filter for UI copy and model rewrites (B01 §6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from finsight.core.config import get_settings
from finsight.guard.advice import AdviceCheck, check_advice, normalize_question
from finsight.guard.clf import Scorer, load_scorer
from finsight.guard.facts import Fact, facts_payload, refusal_text
from finsight.guard.phrases import PhraseHit, find_forbidden, is_clean, load_phrases
from finsight.guard.privacy import OutputCheck, PrivacyCheck, check_output, check_privacy


@dataclass(frozen=True)
class GuardResult:
    """Whether a question is blocked, why, and the text that matched."""

    blocked: bool
    reason: Literal["advice_intent", "privacy"] | None = None
    category: str | None = None
    matched: str | None = None


_scorer: Scorer | None = None


def _classifier_score(question: str) -> float:
    """The MuRIL classifier, loaded on first use (only when ``guard.backend`` is ``muril``)."""
    global _scorer
    if _scorer is None:
        _scorer = load_scorer()
    return _scorer(question)


def check_question(question: str, scorer: Scorer | None = None) -> GuardResult:
    """Privacy first (it is the stricter refusal), then advice, forecasts and ratings.

    Advice is decided by the keyword rules, or, with ``guard.backend: muril``, by the classifier;
    the rule category (``forecast``, ``decision`` ...) is still reported when a rule matches, so the
    refusal can be worded for what was asked.
    """
    privacy = check_privacy(question)
    if privacy.blocked:
        return GuardResult(True, privacy.reason, privacy.category, privacy.matched)
    advice = check_advice(question)
    settings = get_settings().guard
    if scorer is not None or settings.backend == "muril":
        p = (scorer or _classifier_score)(question)
        if p >= settings.threshold:
            category = advice.category if advice.blocked else "classifier"
            return GuardResult(True, "advice_intent", category, advice.matched)
        return GuardResult(False)
    if advice.blocked:
        return GuardResult(True, advice.reason, advice.category, advice.matched)
    return GuardResult(False)


__all__ = [
    "AdviceCheck",
    "Fact",
    "GuardResult",
    "OutputCheck",
    "PhraseHit",
    "PrivacyCheck",
    "check_advice",
    "check_output",
    "check_privacy",
    "check_question",
    "facts_payload",
    "find_forbidden",
    "is_clean",
    "load_phrases",
    "normalize_question",
    "refusal_text",
]
