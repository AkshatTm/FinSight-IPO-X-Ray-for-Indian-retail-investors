"""Guards on what a small model streams back (ADR-047).

The 2B-4B models seen in the bake-off fail in three recognisable ways, and each has a rule:

* **Loops**: "[1][1][1]..." or one sentence repeated until ``num_predict``. ``LoopDetector``
  watches the stream and says stop; ``trim_loops`` cuts the repeat from the finished text.
* **Nothing said**: only citation markers, punctuation or whitespace. Not an answer.
* **A passage pasted back**: most of the answer is a verbatim run from one passage. The prompt
  asks for a short answer in the model's own words, and a dump is a retrieval result, not an
  answer (and in Hindi it is usually English text under a Hindi question).

Three more rules came from the rated Hindi sheet (ADR-020):

* **Devanagari digits** ("४,७२०") are turned into 0-9: the same number, in the script the
  verifier and the document use. The answer is flagged ``digits_converted``; nothing else changes.
* **A converted unit** (the passage says "₹ 26,260 million", the answer "₹ 2,626 crore") is
  rejected: the unit must be copied as written, even when the conversion is arithmetically right.
* **Investor opinions and cautions** ("investors should be careful", "सावधान रहें") are rejected:
  FinSight states what the document says and nothing else.

``clean_answer`` returns the trimmed text, or the "not found" sentence with a reason when the
output is not usable. It never edits numbers or words inside a usable answer.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from finsight.core.schemas import Money, Passage
from finsight.generate.prompts import NOT_FOUND, Language
from finsight.normalize import parse_amounts
from finsight.verify import evidence_amounts, same_value

_DEVANAGARI_DIGITS = str.maketrans({chr(0x0966 + d): str(d) for d in range(10)})
_OPINION = re.compile(
    r"\b(?:investors?|readers?|you|users?)\s+(?:should|must|need to|ought to|may want to|are advised|"
    r"are encouraged|are cautioned)\b|"
    r"\b(?:recommend(?:ed|ation)?|advisable|i advise|we advise|be careful|be cautious|exercise caution|"
    r"worth (?:investing|considering|applying)|good (?:investment|ipo|opportunity)|bad (?:investment|ipo)|"
    r"attractive|overvalued|undervalued|risky|consult (?:a |an |your )?(?:financial|investment|advis[eo]r))\b|"
    r"सावधान|सतर्क|सलाह|अनुशंसा|सिफ़ारिश|सिफारिश|जोखिम भरा|अच्छा निवेश|बेहतर विकल्प|"
    r"ध्यान (?:रखें|रखना|दें)|निवेशकों को [^।]{0,60}चाहिए",
    re.IGNORECASE,
)
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
    """A cleaned answer and, if unusable, why (empty, dump, opinion, ...)."""

    text: str
    # None when the answer is usable; else "empty", "citation_only", "dump", "unit_converted",
    # "opinion"
    reason: str | None
    trimmed: bool = False
    digits_converted: bool = False


def ascii_digits(text: str) -> tuple[str, bool]:
    """Devanagari digits to 0-9; the second value says whether any were found."""
    out = text.translate(_DEVANAGARI_DIGITS)
    return out, out != text


def converted_units(answer: str, passages: Sequence[Passage]) -> list[str]:
    """Answer amounts written in another unit than the passage prints them in.

    An amount counts when no passage amount has the same value *and* the same scale word, yet one
    passage amount has the same value in a different unit ("₹ 2,626 crore" for "₹ 26,260 million").
    """
    evidence = [e for e in evidence_amounts(list(passages)) if isinstance(e.amount, Money)]
    masked = _CITE.sub(lambda m: " " * len(m.group()), answer)
    found: list[str] = []
    for span in parse_amounts(masked):
        a = span.amount
        if not isinstance(a, Money) or a.scale_word is None:
            continue
        equal = [e for e in evidence if same_value(a, e.amount)]
        if equal and all(getattr(e.amount, "scale_word", None) != a.scale_word for e in equal):
            found.append(a.raw)
    return found


def has_opinion(answer: str) -> bool:
    """Whether the answer gives an opinion (citations ignored)."""
    return _OPINION.search(_CITE.sub(" ", answer)) is not None


def content_words(text: str) -> list[str]:
    """The words of a text with ``[n]`` citations removed."""
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
    """Whether the answer mostly copies the passages instead of answering."""
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
    """Trim loops and reject empty, copied, unit-converted or opinion answers."""
    trimmed_text, trimmed = trim_loops(text)
    if not trimmed_text.strip():
        return Cleaned(NOT_FOUND[language], "empty")
    if len(content_words(trimmed_text)) < MIN_WORDS:
        reason = "citation_only" if _CITE.search(trimmed_text) else "empty"
        return Cleaned(NOT_FOUND[language], reason)
    if is_dump(trimmed_text, passages):
        return Cleaned(NOT_FOUND[language], "dump")
    digits_text, digits_converted = ascii_digits(trimmed_text)
    if converted_units(digits_text, passages):
        return Cleaned(NOT_FOUND[language], "unit_converted", trimmed, digits_converted)
    if has_opinion(digits_text):
        return Cleaned(NOT_FOUND[language], "opinion", trimmed, digits_converted)
    return Cleaned(digits_text, None, trimmed, digits_converted)


class LoopDetector:
    """Feed streamed pieces; ``feed`` returns True once the text so far is clearly looping."""

    def __init__(self, window: int = 40, repeats: int = 4) -> None:
        self.window, self.repeats = window, repeats
        self._text = ""

    def feed(self, piece: str) -> bool:
        """Add streamed text; True once the tail repeats too often."""
        self._text += piece
        tail = self._text[-self.window * self.repeats * 2 :]
        for size in range(3, self.window + 1):
            unit = tail[-size:]
            if not unit.strip():
                continue
            if tail.endswith(unit * self.repeats):
                return True
        return False
