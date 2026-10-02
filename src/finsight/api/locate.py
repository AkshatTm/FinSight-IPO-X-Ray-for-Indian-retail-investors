"""Find where an extracted value sits on its page, from the page's word boxes.

The extractors record the page of a value but not its box, and "show it on the page" needs the
box. The match is by text: the words of the page, normalised (case and punctuation ignored), are
scanned for a run that spells the extracted ``raw`` string. A value that wraps onto a second line
is boxed on its first line only, so the box stays a readable size. The result is a position for
the highlight, not a new fact: when nothing matches, the box is simply left out.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from finsight.core.schemas import BBox, Word

_STRIP = re.compile(r"[^0-9a-zऀ-ॿ]")
_NUMBER = re.compile(r"\d[\d,\.]*")
MIN_CHARS = 3
_LINE_TOLERANCE = 3.0  # points: words whose top edges are this close share a line


def _norm(text: str) -> str:
    return _STRIP.sub("", text.casefold())


def _find(words: Sequence[Word], target: str) -> list[Word] | None:
    if len(target) < MIN_CHARS:  # "1" or "10" would match the first such digit on the page
        return None
    for start in range(len(words)):
        acc = ""
        for end in range(start, min(len(words), start + 40)):
            acc += _norm(words[end].text)
            if not target.startswith(acc):
                break
            if acc == target:
                return list(words[start : end + 1])
    return None


def _union(words: Sequence[Word]) -> BBox:
    first_top = words[0].bbox[1]
    line = [w for w in words if abs(w.bbox[1] - first_top) <= _LINE_TOLERANCE] or list(words)
    x0 = min(w.bbox[0] for w in line)
    y0 = min(w.bbox[1] for w in line)
    x1 = max(w.bbox[2] for w in line)
    y1 = max(w.bbox[3] for w in line)
    return (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))


def locate_bbox(words: Sequence[Word], raw: str) -> BBox | None:
    """Box of the first run of ``words`` that spells ``raw``; the number alone as a fallback."""
    run = _find(words, _norm(raw))
    if run is None:
        number = max(_NUMBER.findall(raw), key=len, default="")
        run = _find(words, _norm(number))
    return _union(run) if run else None
