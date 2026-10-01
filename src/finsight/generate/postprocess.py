"""Guards on what a small model streams back (ADR-047).

The 2B-4B models seen in the bake-off fail in three recognisable ways, and each has a rule:

* **Loops**: "[1][1][1]..." or one sentence repeated until ``num_predict``. ``LoopDetector``
  watches the stream and says stop; ``trim_loops`` cuts the repeat from the finished text.
* **Nothing said**: only citation markers, punctuation or whitespace. Not an answer.
* **A passage pasted back**: most of the answer is a verbatim run from one passage. The prompt
  asks for a short answer in the model's own words, and a dump is a retrieval result, not an
  answer (and in Hindi it is usually English text under a Hindi question).

``clean_answer`` returns the trimmed text, or the "not found" sentence with a reason when the
output is not usable. It never edits numbers or words inside a usable answer.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from finsight.core.schemas import Passage
from finsight.generate.prompts import NOT_FOUND, Language

_CITE = re.compile(r"\[\d+\]")
_WORD = re.compile(r"\w+", re.UNICODE)
_SENTENCE = re.compile(r"(?<=[.!?।])\s+")

MIN_WORDS = 2  # fewer content words than this is "nothing said"
SHINGLE = 8  # words in a verbatim run
DUMP_SHARE = 0.6  # share of the answer's shingles found verbatim in one passage
DUMP_MIN_WORDS = 20  # shorter answers may legitimately quote a name or a clause
MAX_REPEATS = 3  # a unit may appear this many times in a row; the next one is a loop


@dataclass(frozen=True)
class Cleaned:
    text: str
    reason: str | None  # None when the answer is usable; else "empty", "citation_only", "dump"
    trimmed: bool = False


def content_words(text: str) -> list[str]:
    return _WORD.findall(_CITE.sub(" ", text))


def trim_loops(text: str) -> tuple[str, bool]:
    """Cut a sentence or citation run that repeats more than ``MAX_REPEATS`` times in a row."""
    parts = _SENTENCE.split(text.strip())
    out: list[str] = []
    run = 0
    for part in parts:
        norm = _CITE.sub("", part).strip().casefold()
        prev = _CITE.sub("", out[-1]).strip().casefold() if out else None
        run = run + 1 if norm == prev else 1
        if run > MAX_REPEATS - 1:
            break
        out.append(part)
    cut = " ".join(out)
    cut = re.sub(r"(\[\d+\])(?:\s*\1){2,}", r"\1", cut)  # "[1][1][1]" -> "[1]"
    return cut, cut != text.strip()


def _shingles(words: list[str]) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + SHINGLE]) for i in range(max(0, len(words) - SHINGLE + 1))}


def is_dump(answer: str, passages: Sequence[Passage]) -> bool:
    words = [w.casefold() for w in content_words(answer)]
    if len(words) < DUMP_MIN_WORDS:
        return False
    mine = _shingles(words)
    if not mine:
        return False
    best = 0.0
    for p in passages:
        theirs = _shingles([w.casefold() for w in content_words(p.text)])
        best = max(best, len(mine & theirs) / len(mine))
    return best >= DUMP_SHARE


def clean_answer(text: str, passages: Sequence[Passage], language: Language = "en") -> Cleaned:
    trimmed_text, trimmed = trim_loops(text)
    if not trimmed_text.strip():
        return Cleaned(NOT_FOUND[language], "empty")
    if len(content_words(trimmed_text)) < MIN_WORDS:
        reason = "citation_only" if _CITE.search(trimmed_text) else "empty"
        return Cleaned(NOT_FOUND[language], reason)
    if is_dump(trimmed_text, passages):
        return Cleaned(NOT_FOUND[language], "dump")
    return Cleaned(trimmed_text, None, trimmed)


class LoopDetector:
    """Feed streamed pieces; ``feed`` returns True once the text so far is clearly looping."""

    def __init__(self, window: int = 40, repeats: int = 4) -> None:
        self.window, self.repeats = window, repeats
        self._text = ""

    def feed(self, piece: str) -> bool:
        self._text += piece
        tail = self._text[-self.window * self.repeats * 2 :]
        for size in range(3, self.window + 1):
            unit = tail[-size:]
            if not unit.strip():
                continue
            if tail.endswith(unit * self.repeats):
                return True
        return False
