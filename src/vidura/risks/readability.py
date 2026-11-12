"""Readability scores for E19: Flesch-Kincaid grade level and Flesch Reading Ease (English).

A vowel-group syllable heuristic is enough for a mean over many rewrites; it is not exact per word.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_VOWELS = re.compile(r"[aeiouy]+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def syllables(word: str) -> int:
    """Syllables in an English word by counting vowel groups (a silent final ``e`` is dropped)."""
    w = word.lower().strip("'’-")
    count = len(_VOWELS.findall(w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(1, count)


def _counts(text: str) -> tuple[int, int, int]:
    words = _WORD.findall(text)
    sentences = [s for s in _SENTENCE_END.split(text.strip()) if _WORD.search(s)]
    return len(words), max(1, len(sentences)), sum(syllables(w) for w in words)


def fkgl(text: str) -> float:
    """Flesch-Kincaid grade level: 0.39 words/sentence + 11.8 syllables/word - 15.59."""
    words, sentences, syl = _counts(text)
    if not words:
        return 0.0
    return 0.39 * words / sentences + 11.8 * syl / words - 15.59


def flesch_reading_ease(text: str) -> float:
    """Flesch Reading Ease: 206.835 - 1.015 words/sentence - 84.6 syllables/word."""
    words, sentences, syl = _counts(text)
    if not words:
        return 0.0
    return 206.835 - 1.015 * words / sentences - 84.6 * syl / words
