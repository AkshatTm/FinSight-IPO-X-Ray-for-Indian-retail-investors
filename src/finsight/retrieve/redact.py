"""Take the residential addresses of individuals out of the search index (ADR-048).

The Our Management and Promoters chapters print each director's and KMP's residential address
next to the DIN and date of birth. A search index that holds them lets any model read them back
(it did: a Hindi bake-off answer gave a CEO's home address). So the chunker blanks them:

* **Tables**: in a table whose headers look like director particulars (DIN, date of birth,
  nationality, occupation) every cell under an "Address" / "Residential address" column becomes
  ``[withheld for privacy]``. The registrar and lead-manager tables have no such headers and keep
  their (business) addresses.
* **Prose**: after an explicit "residential / permanent / current / correspondence address" cue,
  or after a bare "Address:" in a passage that also holds director particulars, the text up to the
  next field label is replaced. A registered-office or registrar address is never touched.

The page itself (PDF, word boxes) is not changed: it is the document, and the reader can open it.
What changes is what FinSight's models can retrieve and repeat. Spans of ``char_to_bbox`` that
overlap a redaction are dropped; later spans are shifted so highlights stay aligned.
"""

from __future__ import annotations

import re

from finsight.core.schemas import BBox, Table, TableCell, Word

PLACEHOLDER = "[withheld for privacy]"
MAX_ADDRESS_CHARS = 220
MIN_ADDRESS_ALNUM = 8  # ", " between two field labels is not an address

Spans = list[tuple[int, int, int, BBox]]

_DIRECTOR = re.compile(
    r"\bDIN\b|date of birth|\bnationality\b|\boccupation\b|period of directorship", re.IGNORECASE
)
_PARTICULARS = re.compile(r"\bDIN\b|date of birth|\bnationality\b|\boccupation\b", re.IGNORECASE)
_EXPLICIT = re.compile(
    r"\b(?:residential|permanent|current|present|correspondence|home|private|personal)\s+"
    r"(?:address(?:es)?|residence)\s*[:\-–]?",
    re.IGNORECASE,
)
_BARE = re.compile(r"\baddress\b\s*[:\-–]?", re.IGNORECASE)
_RESIDING = re.compile(r"\b(?:is\s+)?(?:residing|resides|resident)\s+(?:at|in)\b", re.IGNORECASE)
_BUSINESS_BEFORE = re.compile(
    r"\b(?:registered|corporate|head|principal|branch) offices?\b|\bregistrar|\blead managers?\b|"
    r"\bbrlm|\bcompany secretary\b|\bcompliance officer\b|\bescrow\b|\bbank\b|\bauditors?\b",
    re.IGNORECASE,
)
_STOP = re.compile(
    r"\b(?:occupation|date of birth|DIN|nationality|designation|current term|"
    r"period of directorship|experience|qualifications?)\b|"
    r"\b(?:age|term|tenure|other directorships?|contact|tel|e-?mail|phone|mobile)\b\s*[:\-–]|"
    r"\.\s+(?=[A-Z])|\n",
    re.IGNORECASE,
)
_ADDRESS_HEADER = re.compile(
    r"^\W*(?:(?:residential|permanent|current|present|correspondence)\s+)?(?:address(?:es)?|residence)"
    r"(?:\s*\(.*\))?\W*$",
    re.IGNORECASE,
)


def find_personal_addresses(text: str) -> list[tuple[int, int]]:
    """``(start, end)`` of every residential address in prose, the cue itself excluded."""
    found: list[tuple[int, int]] = []
    cues = [m for m in _EXPLICIT.finditer(text)]
    if _PARTICULARS.search(text):
        for m in _BARE.finditer(text):
            before = text[max(0, m.start() - 60) : m.start()]
            colon = m.group().strip().endswith((":", "-", "–"))
            # without a colon "address" is only a label when a field label follows it closely
            labelled = colon or _STOP.search(text, m.end(), m.end() + MAX_ADDRESS_CHARS)
            if (
                labelled
                and not _BUSINESS_BEFORE.search(before)
                and not any(c.start() <= m.start() < c.end() for c in cues)
            ):
                cues.append(m)
    cues += list(_RESIDING.finditer(text))
    for cue in sorted(cues, key=lambda m: m.start()):
        start = cue.end()
        stop = _STOP.search(text, start)
        end = min(stop.start() if stop else len(text), start + MAX_ADDRESS_CHARS)
        region = text[start:end]
        start += len(region) - len(region.lstrip())  # keep the space after the cue
        if text.startswith(PLACEHOLDER, start):
            continue  # already redacted
        if sum(c.isalnum() for c in text[start:end]) >= MIN_ADDRESS_ALNUM and not (
            found and start < found[-1][1]
        ):
            found.append((start, end))
    return found


def redact_prose(text: str, spans: Spans) -> tuple[str, Spans]:
    """The text with every personal address replaced; ``spans`` kept aligned."""
    regions = find_personal_addresses(text)
    if not regions:
        return text, spans
    out: list[str] = []
    new_spans: Spans = []
    pos = 0
    shift = 0
    for start, end in regions:
        out.append(text[pos:start])
        out.append(PLACEHOLDER)
        for s in spans:
            if s[1] <= start and s[0] >= pos:
                new_spans.append((s[0] + shift, s[1] + shift, s[2], s[3]))
        shift += len(PLACEHOLDER) - (end - start)
        pos = end
    out.append(text[pos:])
    for s in spans:
        if s[0] >= pos:
            new_spans.append((s[0] + shift, s[1] + shift, s[2], s[3]))
    return "".join(out), new_spans


def redact_table(table: Table) -> Table:
    """The table with the cells of a personal-address column blanked; others unchanged."""
    if not table.cells:
        return table
    first = min(c.row for c in table.cells)
    header = [c for c in table.cells if c.row <= first + 1]
    if not any(_DIRECTOR.search(c.text) for c in header):
        return table
    columns = {c.col for c in header if _ADDRESS_HEADER.match(" ".join(c.text.split()))}
    if not columns:
        return table
    header_row = max(c.row for c in header if c.col in columns and _ADDRESS_HEADER.match(c.text))
    cells: list[TableCell] = [
        c.model_copy(update={"text": PLACEHOLDER})
        if c.col in columns and c.row > header_row and c.text.strip()
        else c
        for c in table.cells
    ]
    return table.model_copy(update={"cells": cells})


# ---- board tables that the table stage did not detect ----
# "Name, Designation and DIN | Address": the rows reach the chunker as flowing prose, so no text
# rule can tell where one address ends and the next name begins. The words' boxes can: everything
# at or right of the "Address" header, from the header down to the first line below the last
# "DIN:" row that has text in the left column again, is the address column.
_DIN_NUMBER = re.compile(r"^\d{7,8}$")
_LINE_TOL = 3.0  # points: words whose centres differ by less than this share a line
_COLUMN_TOL = 5.0


def _yc(word: Word) -> float:
    return (word.bbox[1] + word.bbox[3]) / 2


def address_column_words(words: list[Word]) -> set[int]:
    """Indices of the words that sit in the address column of a director table."""
    headers: list[tuple[int, float, float]] = []  # (word index, address x0, header bottom)
    for i, w in enumerate(words):
        if w.text.strip(" :|").casefold() != "address":
            continue
        line = [v for v in words if abs(_yc(v) - _yc(w)) < _LINE_TOL and v.bbox[2] <= w.bbox[0] + 1]
        if any(v.text.strip(" :|,").upper() == "DIN" for v in line):
            headers.append((i, w.bbox[0], max(v.bbox[3] for v in [*line, w])))
    if not headers:
        return _headerless_address_column(words)
    drop: set[int] = set()
    headers.sort(key=lambda h: h[2])
    for k, (_, x_addr, top) in enumerate(headers):
        limit = headers[k + 1][2] if k + 1 < len(headers) else float("inf")
        left = x_addr - _COLUMN_TOL
        in_table = [w for w in words if top < w.bbox[1] < limit and w.bbox[2] <= x_addr + 1]
        labels = [w for w in in_table if w.text.strip(" :").upper() == "DIN"]
        numbers = [w for w in in_table if _DIN_NUMBER.match(w.text.strip())]
        dins = [w.bbox[3] for w in labels + numbers]
        if not labels and numbers:  # DIN has a column of its own: the address column follows it
            left = min(left, max(w.bbox[2] for w in numbers) + _COLUMN_TOL)
        elif labels:  # "DIN: 0123" in the left cell: the cells start where the line goes on
            for n in numbers:
                right = [
                    v.bbox[0]
                    for v in words
                    if abs(_yc(v) - _yc(n)) < _LINE_TOL and v.bbox[0] > n.bbox[2] + _MIN_GAP
                ]
                if right:
                    left = min(left, min(right) - _COLUMN_TOL)
        if not dins:
            continue
        last_din = max(dins)
        below = [
            w.bbox[1]
            for w in words
            if last_din + 1 < w.bbox[1] < limit and w.bbox[0] < left and w.text.strip()
        ]
        end = min(below) if below else limit
        for j, w in enumerate(words):
            if top <= w.bbox[1] < end and (w.bbox[0] + w.bbox[2]) / 2 >= left and j not in drop:
                drop.add(j)
    return drop


# A board table that continues on the next page has no header there. Its rows still read
# "DIN: 01234567" in the left cell with the address to the right on the same line.
_ROW_TOP = 70.0  # points above the first DIN line where that row's address can start
_MIN_GAP = 12.0  # an address column starts at least this far right of the DIN number


def _headerless_address_column(words: list[Word]) -> set[int]:
    starts: list[float] = []
    din_lines: list[Word] = []
    for i, w in enumerate(words):
        if not _DIN_NUMBER.match(w.text.strip()) or i == 0:
            continue
        if words[i - 1].text.strip(" :").upper() != "DIN":
            continue
        din_lines.append(w)
        right = [
            v.bbox[0]
            for v in words
            if abs(_yc(v) - _yc(w)) < _LINE_TOL and v.bbox[0] > w.bbox[2] + _MIN_GAP
        ]
        if right:
            starts.append(min(right))
    if not starts:
        return set()
    left = min(starts) - _COLUMN_TOL
    top = min(w.bbox[1] for w in din_lines) - _ROW_TOP
    last_din = max(w.bbox[3] for w in din_lines)
    below = [
        w.bbox[1] for w in words if w.bbox[1] > last_din + 1 and w.bbox[0] < left and w.text.strip()
    ]
    end = min(below) if below else float("inf")
    return {
        j
        for j, w in enumerate(words)
        if top <= w.bbox[1] < end and (w.bbox[0] + w.bbox[2]) / 2 >= left
    }
