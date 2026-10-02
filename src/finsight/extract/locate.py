"""Find where an extracted value sits on its page, from the page's word boxes.

The extractors record the page of a value but not its box, and "show it on the page" needs the
box. The extract stage runs this once per candidate and stores the box (``fill_boxes``); the API
only falls back to it for X-Rays built before boxes were stored. The match is by text: the words
of the page, normalised (case and punctuation ignored), are scanned for a run that spells the
extracted ``raw`` string. A value that wraps onto a second line
is boxed on its first line only, so the box stays a readable size. The result is a position for
the highlight, not a new fact: when nothing matches, the box is simply left out.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from finsight.core.schemas import BBox, Candidate, ParsedDoc, Word

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


SENTENCE_WORDS_EACH_SIDE = 10  # a full-width line stays a short quote


def sentence_around(words: Sequence[Word], bbox: BBox) -> tuple[str, tuple[int, int]] | None:
    """The line the value sits on as ``(text, (hit_start, hit_end))``: its words in reading order,
    at most 10 either side, with the character span of the words inside the box.

    A tight band (a third of the box height) keeps neighbouring lines out: dense pages set lines
    about one box-height apart. ``None`` when the box catches no word.
    """
    x0, y0, x1, y1 = bbox
    mid, tol = (y0 + y1) / 2, (y1 - y0) * 0.35
    line = sorted(
        (w for w in words if abs((w.bbox[1] + w.bbox[3]) / 2 - mid) <= tol),
        key=lambda w: w.bbox[0],
    )
    hits = [x0 - 1 <= (w.bbox[0] + w.bbox[2]) / 2 <= x1 + 1 for w in line]
    if not line or not any(hits):
        return None
    first = hits.index(True)
    last = len(hits) - 1 - hits[::-1].index(True)
    lo, hi = max(0, first - SENTENCE_WORDS_EACH_SIDE), last + SENTENCE_WORDS_EACH_SIDE + 1
    texts = [w.text for w in line[lo:hi]]
    start = len(" ".join(texts[: first - lo])) + (1 if first > lo else 0)
    end = start + len(" ".join(texts[first - lo : last - lo + 1]))
    return " ".join(texts), (start, end)


def fill_boxes(candidates: Sequence[Candidate], doc: ParsedDoc) -> list[Candidate]:
    """Candidates with the box of their value stored: kept when set, else found on the page by
    text (``locate_bbox``). A value that cannot be matched keeps ``bbox = None``."""
    out: list[Candidate] = []
    for c in candidates:
        if c.bbox is None and 1 <= c.page <= len(doc.pages) and c.doc_type == doc.doc_type:
            box = locate_bbox(doc.pages[c.page - 1].words, c.raw)
            if box is not None:
                c = c.model_copy(update={"bbox": box})
        out.append(c)
    return out
