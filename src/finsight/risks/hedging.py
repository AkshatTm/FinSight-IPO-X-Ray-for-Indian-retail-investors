"""Hedging and hard facts (B02 §7.2).

``hedge_count`` counts hedge words and phrases (``configs/hedges.yaml``). A risk is a *hard fact*
when one sentence states something that already happened, with a number: a past-tense verb or a
"in Fiscal 2024"-style period, an amount that is not just a year, and no modal hedge. Many hedges
plus a hard fact raise the B05 note "Written cautiously, but this describes something that has
already happened."
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from finsight.core.config import project_root
from finsight.core.schemas import Hedging
from finsight.normalize import parse_amounts

FLAG_MIN_HEDGES = 3
_SENTENCE = re.compile(r"(?<=[.;!?])\s+(?=[A-Z(\"“])")
_MODAL = re.compile(r"\b(?:may|might|could|would|can|should|if|potential(?:ly)?)\b", re.I)
_PAST = re.compile(
    r"\b(?:incurred|recorded|reported|recognised|recognized|suffered|experienced|contributed|"
    r"accounted|derived|received|filed|paid|defaulted|delayed|were|was|had|has been|have been|"
    r"has|have|lost|declined|decreased|increased|fell|rose|issued|imposed|levied)\b",
    re.I,
)
_PERIOD = re.compile(
    r"\b(?:in|during|for)\s+(?:the\s+)?"
    r"(?:fiscal|financial year|fy|six months|three months|nine months)\b|"
    r"\bas (?:of|at|on)\s+\w+",
    re.I,
)


@lru_cache(maxsize=4)
def load_hedges(path: Path | None = None) -> tuple[re.Pattern[str], ...]:
    data: dict[str, Any] = yaml.safe_load(
        (path or project_root() / "configs" / "hedges.yaml").read_text(encoding="utf-8")
    )
    phrases = [*data.get("lm_uncertainty", []), *data.get("own", [])]
    # longest first, so "there can be no assurance" is one hit, not also "no assurance"
    phrases = sorted({p.lower().strip() for p in phrases if p.strip()}, key=len, reverse=True)
    return tuple(
        re.compile(r"\b" + r"\s+".join(map(re.escape, p.split())) + r"\b", re.I) for p in phrases
    )


def hedge_count(text: str, patterns: tuple[re.Pattern[str], ...] | None = None) -> int:
    """Hedge hits; a span counted by a longer phrase is not counted again by a shorter one."""
    taken: list[tuple[int, int]] = []
    for pat in patterns or load_hedges():
        for m in pat.finditer(text):
            if not any(s < m.end() and m.start() < e for s, e in taken):
                taken.append((m.start(), m.end()))
    return len(taken)


def _has_real_number(sentence: str) -> bool:
    """An amount, percentage or count that is not just a year like 2024."""
    for span in parse_amounts(sentence):
        if span.amount.kind in ("money", "percent"):
            return True
        if span.amount.kind == "count" and not re.fullmatch(
            r"(19|20)\d{2}", span.amount.raw.strip()
        ):
            return True
    return False


def fact_sentence(text: str) -> str | None:
    """The first sentence that states a past fact with a number, if any."""
    for sentence in _SENTENCE.split(text):
        if _MODAL.search(sentence):
            continue
        if not (_PAST.search(sentence) or _PERIOD.search(sentence)):
            continue
        if _has_real_number(sentence):
            return sentence.strip()
    return None


def hedging(text: str, min_hedges: int = FLAG_MIN_HEDGES) -> Hedging:
    count = hedge_count(text)
    fact = fact_sentence(text)
    return Hedging(
        hedge_count=count,
        hard_fact=fact is not None,
        flag=count >= min_hedges and fact is not None,
        fact_sentence=fact,
    )
