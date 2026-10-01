"""Character and word error rate for Hindi transcripts (05 section 5, E12).

CER is the primary metric for Hindi: word boundaries in Devanagari are a matter of taste
("आईपीओ" or "आई पी ओ"), the characters are not. Both texts are normalised first so that spelling
variants that a reader treats as one word do not count as errors: Unicode NFC, the dot under a
letter dropped (ऑफ़र = ऑफर), chandrabindu written as anusvara, Devanagari digits as 0-9, punctuation
and the danda removed, case folded. ``cer`` ignores spaces (the primary figure); ``cer_with_spaces``
and ``wer`` keep them.
"""

from __future__ import annotations

import unicodedata

_NUKTA = "़"
_CHANDRABINDU, _ANUSVARA = "ँ", "ं"
_DIGITS = str.maketrans({chr(0x0966 + d): str(d) for d in range(10)})


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).casefold()
    text = text.replace(_NUKTA, "").replace(_CHANDRABINDU, _ANUSVARA).translate(_DIGITS)
    text = unicodedata.normalize("NFC", text)
    # Punctuation and symbols only: Devanagari vowel signs are not "word" characters to ``\w``
    text = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in text)
    return " ".join(text.split())


def edit_distance(a: list[str] | str, b: list[str] | str) -> int:
    """Levenshtein distance between two sequences (insert, delete, substitute = 1)."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        current = [i]
        for j, y in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate with spaces ignored; 0.0 is perfect, can exceed 1.0."""
    ref = normalize(reference).replace(" ", "")
    hyp = normalize(hypothesis).replace(" ", "")
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


def cer_with_spaces(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference).split(), normalize(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)
