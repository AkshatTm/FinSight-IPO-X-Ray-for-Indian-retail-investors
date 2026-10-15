"""Strict number checks on a teacher rewrite (C2.3b), beyond ``checks.unmatched_numbers``.

``unmatched_numbers`` only asks "is every number in the rewrite also in the source?". Quality-100
found two errors that pass it: a number whose currency/scale was dropped ("285.97" for
"₹285.97 million"), and numbers called negative that the source printed as positive. This
module adds those two as hard failures and a third, softer check as a flag:

- ``unit_dropped`` (drop): a bare number whose source form carries a currency or scale word.
- ``sign_flip`` (drop): a number the rewrite calls negative that the source does not show as
  negative (brackets, a minus sign, or "loss"/"negative"/"deficit" next to it).
- ``inclusion_polarity`` (flag only): the rewrite says "included" in a sentence that shares a
  number with a source sentence saying "not included" / "excluding".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsight.normalize import parse_amounts

DROP_REASONS = ("unit_dropped", "sign_flip")
FLAG_REASONS = ("inclusion_polarity",)

_BARE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
_NEGATIVE_WORD = re.compile(r"\bnegative\b", re.I)
_NEG_WORD_NEAR = re.compile(
    r"negative|loss(?:es)?|deficit|decline|decrease|outflow|shortfall", re.I
)
_NOT_INCLUDED = re.compile(
    r"\b(?:not|nor|never)\s+(?:been\s+)?(?:included|includ\w+|part)\b|\bexclud\w+|\bexclusive of\b"
    r"|\bdoes not include\b|\bdo not include\b|\bother than\b",
    re.I,
)
_INCLUDED = re.compile(r"\b(?:includ(?:ed|es|ing|e)|part of|within)\b", re.I)


@dataclass(frozen=True)
class Finding:
    """One strict-check result: a reason from ``DROP_REASONS`` / ``FLAG_REASONS`` and detail."""

    reason: str
    detail: str

    @property
    def drops(self) -> bool:
        """True when the row must be removed from the training data."""
        return self.reason in DROP_REASONS


def _plain(number: str) -> str:
    return number.replace(",", "")


def _sentences(text: str) -> list[str]:
    return [s for s in _SENT.split(text) if s.strip()]


def _has_unit(raw: str, scale_word: str | None) -> bool:
    return bool(scale_word) or bool(re.search(r"₹|\bRs\b|\bINR\b|\bUS\$|\$", raw))


def _unit_dropped(original: str, simple: str) -> list[Finding]:
    unit_numbers: dict[str, str] = {}
    for span in parse_amounts(original):
        money = span.amount
        if money.kind != "money":
            continue
        digits = _plain(re.sub(r"[^\d.,]", "", money.raw)).strip(".")
        if digits and _has_unit(money.raw, getattr(money, "scale_word", None)):
            unit_numbers.setdefault(digits, money.raw)
    covered = [(s.start, s.end) for s in parse_amounts(simple)]
    out: list[Finding] = []
    for m in _BARE.finditer(simple):
        if any(a <= m.start() < b for a, b in covered):
            continue
        digits = _plain(m.group(0)).rstrip(".")
        if "." not in digits and len(digits) < 3:  # "2 plants" is not a figure
            continue
        if digits in unit_numbers:
            out.append(Finding("unit_dropped", f"{m.group(0)} (source: {unit_numbers[digits]})"))
    return out


def _is_figure(number: str) -> bool:
    """A money-like figure: has a decimal point or is a 3+ digit number that is not a year."""
    digits = _plain(number).rstrip(".")
    if "." in digits:
        return True
    return len(digits) >= 3 and not (len(digits) == 4 and 1900 <= int(digits) <= 2100)


def _source_negative(original: str, digits: str) -> bool:
    """True if ``digits`` appears in the source bracketed, signed or next to a loss word."""
    num = re.escape(digits)
    bracket = re.compile(rf"\(\s*[₹`]?\s*(?:Rs\.?|INR)?\s*{num}\s*\)")
    minus = re.compile(rf"[-−–]\s*[₹`]?\s*(?:Rs\.?|INR)?\s*{num}(?![\d])")
    plain = re.compile(rf"(?<![\d.]){num}(?![\d])")
    for body in {original, original.replace(",", "")}:
        if bracket.search(body) or minus.search(body):
            return True
        for m in plain.finditer(body):
            if _NEG_WORD_NEAR.search(body[max(0, m.start() - 140) : m.end() + 2]):
                return True
    return False


def _sign_flip(original: str, simple: str) -> list[Finding]:
    out: list[Finding] = []
    for sentence in _sentences(simple):
        if not _NEGATIVE_WORD.search(sentence):
            continue
        for m in _BARE.finditer(sentence):
            digits = _plain(m.group(0)).rstrip(".")
            if not _is_figure(digits):
                continue
            if not _source_negative(original, digits):
                out.append(Finding("sign_flip", f"{m.group(0)} called negative: {sentence[:90]}"))
    return out


def _inclusion_polarity(original: str, simple: str) -> list[Finding]:
    out: list[Finding] = []
    source = _sentences(original)
    for sentence in _sentences(simple):
        if not _INCLUDED.search(sentence) or _NOT_INCLUDED.search(sentence):
            continue
        numbers = {_plain(m.group(0)).rstrip(".") for m in _BARE.finditer(sentence)}
        for src in source:
            if _NOT_INCLUDED.search(src) and numbers & {
                _plain(m.group(0)).rstrip(".") for m in _BARE.finditer(src)
            }:
                out.append(Finding("inclusion_polarity", sentence[:90]))
                break
    return out


def strict_check(original: str, simple: str) -> list[Finding]:
    """All strict findings for one (source text, rewrite) pair; empty list = clean."""
    return (
        _unit_dropped(original, simple)
        + _sign_flip(original, simple)
        + _inclusion_polarity(original, simple)
    )
