"""Checks a plain-English rewrite must pass (B02 §8, B03 §3.3): numbers, length, phrases.

Shared by the teacher filters (B2.3a) and the student post-checks (B2.5a), so both sides drop
exactly the same things.
"""

from __future__ import annotations

import re

from finsight.normalize import parse_amounts
from finsight.verify import same_value

_BARE_NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")
_WORD = re.compile(r"\S+")


def word_count(text: str) -> int:
    """The number of words in ``text``."""
    return len(_WORD.findall(text))


def _bare_numbers(text: str, spans: list[tuple[int, int]]) -> set[str]:
    """Plain numbers outside money/percent spans ("3 plants", "Fiscal 2024"), commas removed."""
    out = set()
    for m in _BARE_NUMBER.finditer(text):
        if any(s <= m.start() < e for s, e in spans):
            continue
        out.add(m.group(0).replace(",", "").rstrip("."))
    return out


def unmatched_numbers(original: str, rewrite: str) -> list[str]:
    """Numbers in ``rewrite`` that are not in ``original`` (empty = every number is copied).

    Money and percentages are compared by value within the printed precision (``verify``), so
    "₹1,234.56 crore" may become "₹1,235 crore" but not "₹12.35 billion" written wrongly; plain
    numbers must appear verbatim (commas ignored).
    """
    src_spans = parse_amounts(original)
    out_spans = parse_amounts(rewrite)
    missing = [
        s.amount.raw
        for s in out_spans
        if not any(
            s.amount.kind == o.amount.kind and same_value(s.amount, o.amount) for o in src_spans
        )
    ]
    src_plain = _bare_numbers(original, [(s.start, s.end) for s in src_spans])
    src_plain |= {re.sub(r"[^\d.]", "", s.amount.raw) for s in src_spans}
    for number in _bare_numbers(rewrite, [(s.start, s.end) for s in out_spans]):
        if number not in src_plain:
            missing.append(number)
    return missing
