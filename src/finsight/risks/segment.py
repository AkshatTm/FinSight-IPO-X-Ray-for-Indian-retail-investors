"""Split a Risk Factors section into single risks (B02 §6, B2.1).

Two inputs, two rules:

- **PDF pages** (uploads, showcase documents) keep fonts. A risk starts at a line that begins at
  the left margin with a bold run of at least 5 words, followed by non-bold text. The bold run is
  the title; it ends with a full stop or is at most 3 lines long. A number prefix (``12.``,
  ``(a)``) raises confidence. Words inside table boxes never start a risk (bold table headers),
  running headers / footers and printed page numbers are dropped, and a body that crosses a page
  break is merged. Short bold sub-headings such as "Internal Risks" set the ``group`` of the risks
  under them. Text before the first sub-heading or numbered title is the preamble and is skipped.
- **Corpus text** (no fonts): numbered paragraphs whose number follows the previous one; the
  title is the paragraph's first sentence, which must look like one (≥ 5 words, capital start).

Both return :class:`RiskSpan`; :func:`to_risks` turns spans into ``core.schemas.Risk`` rows.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from finsight.core.schemas import BBox, Page, Risk, Word
from finsight.parse import EDGE_BAND, boilerplate_keys, line_key, read_printed_page

MIN_TITLE_WORDS = 5
MAX_TITLE_LINES = 3
MARGIN_TOLERANCE = 15.0  # points right of the page's left margin a title may start
PARAGRAPH_GAP = 1.6  # a vertical gap above this many line heights starts a new paragraph

_FIGURE = re.compile(r"^[(₹$]?-?[\d,]*\d[\d,.]*%?\)?\*?$")
NUMBER_PREFIX = re.compile(r"^(?:\d{1,3}\.|\(\w{1,4}\))$")
_GROUP = re.compile(
    r"^(?:[A-Z]\.\s*|[IVX]{1,4}\.\s*)?(?:"
    r"(?:internal|external)\s+risks?(?:\s+factors?)?"
    r"|risks?\s+(?:relating|related|pertaining)\s+to\s+.{3,60}"
    r"|(?:other|general|industry)\s+risks?"
    r")\s*:?$",
    re.IGNORECASE,
)
_ABBREVIATIONS = (
    "Rs.",
    "M/s.",
    "No.",
    "Nos.",
    "Ltd.",
    "Pvt.",
    "Co.",
    "Inc.",
    "i.e.",
    "e.g.",
    "etc.",
    "viz.",
)


@dataclass
class RiskSpan:
    """One risk found in a section: its title, body, group and where it sits."""

    title: str
    body: str
    page_start: int
    page_end: int
    group: str | None = None
    numbered: bool = False
    confidence: float = 0.0


@dataclass
class Line:
    """One printed line: its words left to right and its box."""

    page: int
    words: list[Word]
    bbox: BBox

    @property
    def text(self) -> str:
        """The words joined by single spaces."""
        return " ".join(w.text for w in self.words)

    @property
    def height(self) -> float:
        """Line height in points."""
        return self.bbox[3] - self.bbox[1]


@dataclass
class _Open:
    span: RiskSpan
    paragraphs: list[list[str]] = field(default_factory=list)


# ------------------------------------------------------------------------- lines
def page_lines(page: Page) -> list[Line]:
    """Group a page's words into lines by vertical overlap, top to bottom, left to right."""
    rows: list[list[Word]] = []
    for word in sorted(page.words, key=lambda w: ((w.bbox[1] + w.bbox[3]) / 2, w.bbox[0])):
        mid = (word.bbox[1] + word.bbox[3]) / 2
        if rows:
            last = rows[-1]
            top, bottom = min(w.bbox[1] for w in last), max(w.bbox[3] for w in last)
            if top <= mid <= bottom:
                last.append(word)
                continue
        rows.append([word])
    lines = []
    for row in rows:
        row.sort(key=lambda w: w.bbox[0])
        box = (
            min(w.bbox[0] for w in row),
            min(w.bbox[1] for w in row),
            max(w.bbox[2] for w in row),
            max(w.bbox[3] for w in row),
        )
        lines.append(Line(page=page.number, words=row, bbox=box))
    return lines


def _inside(word: Word, boxes: Sequence[BBox]) -> bool:
    cx, cy = (word.bbox[0] + word.bbox[2]) / 2, (word.bbox[1] + word.bbox[3]) / 2
    return any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes)


def _edge(line: Line, page: Page) -> bool:
    return line.bbox[3] <= page.height * EDGE_BAND or line.bbox[1] >= page.height * (1 - EDGE_BAND)


def body_lines(
    pages: Sequence[Page],
    table_boxes: Mapping[int, Sequence[BBox]] | None = None,
    context: Sequence[Page] | None = None,
) -> list[Line]:
    """The section's lines without running headers / footers, page numbers and table words.

    Headers are lines that repeat at the page edges of ``context`` (the whole document when
    given), so a section of one or two pages still loses them."""
    by_page = [(p, page_lines(p)) for p in pages]
    edges = (
        [[ln.text for ln in page_lines(p) if _edge(ln, p)] for p in context]
        if context
        else [[ln.text for ln in lines if _edge(ln, p)] for p, lines in by_page]
    )
    repeated = boilerplate_keys(edges)
    out: list[Line] = []
    for page, lines in by_page:
        boxes = (table_boxes or {}).get(page.number, ())
        for line in lines:
            if _edge(line, page) and (
                line_key(line.text) in repeated
                or (line.bbox[1] >= page.height / 2 and read_printed_page([line.text]))
            ):
                continue
            words = [w for w in line.words if not _inside(w, boxes)]
            if words:
                out.append(Line(page=line.page, words=words, bbox=line.bbox))
    return out


# ------------------------------------------------------------------------- PDF rule
def _left_margin(lines: Sequence[Line]) -> dict[int, float]:
    margins: dict[int, float] = {}
    for line in lines:
        margins[line.page] = min(margins.get(line.page, line.bbox[0]), line.bbox[0])
    return margins


def _is_number(word: Word) -> bool:
    return bool(NUMBER_PREFIX.match(word.text))


def _bold_run(line: Line, start: int = 0) -> int:
    n = start
    while n < len(line.words) and line.words[n].bold:
        n += 1
    return n - start


def _number_prefix(line: Line) -> bool:
    return bool(line.words) and _is_number(line.words[0])


def _is_group(line: Line) -> bool:
    return all(w.bold for w in line.words) and bool(_GROUP.match(line.text.strip()))


def _title_at(lines: Sequence[Line], i: int, margin: float) -> tuple[list[str], int, int] | None:
    """If a risk title starts at ``lines[i]``, return (title words, lines it uses, how many
    regular words follow it on its last line); otherwise ``None``."""
    first = lines[i]
    if i > 0 and _continues_bold(lines[i - 1], first):
        return None  # the middle of a longer bold block, not its start
    skip = 1 if _number_prefix(first) else 0
    if first.bbox[0] > margin + MARGIN_TOLERANCE or _bold_run(first, skip) == 0:
        return None
    words: list[str] = []
    for k in range(i, min(len(lines), i + MAX_TITLE_LINES * 2)):
        line = lines[k]
        offset = skip if k == i else 0
        run = _bold_run(line, offset)
        if k > i and run == 0:  # regular text on the next line: the title ended above
            return _check(words, k - i, 0)
        words += [w.text for w in line.words[offset : offset + run]]
        if offset + run < len(line.words):  # regular text follows on the same line
            return _check(words, k - i + 1, len(line.words) - offset - run)
    return None


def _continues_bold(prev: Line, line: Line) -> bool:
    gap = line.bbox[1] - prev.bbox[3]
    return (
        prev.page == line.page
        and bool(prev.words)
        and prev.words[-1].bold
        and not _is_group(prev)
        and gap <= PARAGRAPH_GAP * max(line.height, 1.0)
    )


def _check(words: list[str], used: int, rest: int) -> tuple[list[str], int, int] | None:
    """B02 §6: ≥ 5 words, and either ≤ 3 lines or ending with a full stop."""
    if len(words) < MIN_TITLE_WORDS:
        return None
    if words[0][:1].islower():
        return None  # a bold quote or cross-reference inside a body, not the start of a risk
    if sum(bool(_FIGURE.match(w)) for w in words) * 5 >= len(words) * 2:
        return None  # a bold table row the table detector missed
    if used > MAX_TITLE_LINES and not words[-1].endswith("."):
        return None
    return words, used, rest


def segment_pages(
    pages: Sequence[Page],
    table_boxes: Mapping[int, Sequence[BBox]] | None = None,
    context: Sequence[Page] | None = None,
) -> list[RiskSpan]:
    """Split the pages of a Risk Factors section into risks (fonts available). ``context`` is the
    whole document, used to recognise running headers and footers."""
    lines = body_lines(pages, table_boxes, context)
    margins = _left_margin(lines)
    spans: list[RiskSpan] = []
    current: _Open | None = None
    group: str | None = None
    started = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_group(line):
            group, started = " ".join(line.text.split()).rstrip(":"), True
            _close(current, spans)
            current = None
            i += 1
            continue
        found = _title_at(lines, i, margins[line.page])
        numbered = _number_prefix(line)
        if found is not None and (started or numbered):
            words, used, rest = found
            _close(current, spans)
            last = lines[i + used - 1]
            current = _Open(
                RiskSpan(
                    title=" ".join(words),
                    body="",
                    page_start=line.page,
                    page_end=last.page,
                    group=group,
                    numbered=numbered,
                    confidence=0.9 if numbered else 0.7,
                ),
                paragraphs=[[w.text for w in last.words[len(last.words) - rest :]]] if rest else [],
            )
            started = True
            i += used
            continue
        if current is not None:
            prev = lines[i - 1]
            gap = line.bbox[1] - prev.bbox[3]
            new_paragraph = not current.paragraphs or (
                line.page == prev.page and gap > PARAGRAPH_GAP * max(line.height, 1.0)
            )
            if new_paragraph:
                current.paragraphs.append([])
            current.paragraphs[-1] += [w.text for w in line.words]
            current.span.page_end = line.page
        i += 1
    _close(current, spans)
    return spans


def _close(current: _Open | None, spans: list[RiskSpan]) -> None:
    if current is not None:
        current.span.body = "\n\n".join(" ".join(p) for p in current.paragraphs if p)
        spans.append(current.span)


# ------------------------------------------------------------------------- corpus rule
_NUMBERED = re.compile(r"^\s*(\d{1,3})\.\s+(\S.*)$", re.DOTALL)
_SENTENCE_END = re.compile(r"(?<=[.?!])\s+(?=[A-Z\"'“(₹])")


def first_sentence(text: str) -> tuple[str, str]:
    """Split ``text`` after its first sentence, ignoring common abbreviations ("Rs.", "Ltd.")."""
    for match in _SENTENCE_END.finditer(text):
        head = text[: match.start()]
        if not head.endswith(_ABBREVIATIONS):
            return head.strip(), text[match.end() :].strip()
    return text.strip(), ""


_BARE_NUMBER = re.compile(r"^\d{1,3}\.$")


def _starts_title(line: str) -> bool:
    """A title line starts with a capital (or quote) and is not itself a numbered line."""
    return line[:1] in "\"'“(" or (line[:1].isupper() and not _NUMBERED.match(line))


def _join_bare_numbers(lines: list[str]) -> list[str]:
    """Corpus pages often put the risk number alone on a line ("12." then the title): join them."""
    out: list[str] = []
    skip = False
    for i, ln in enumerate(lines):
        if skip:
            skip = False
            continue
        if _BARE_NUMBER.match(ln) and i + 1 < len(lines) and _starts_title(lines[i + 1]):
            out.append(f"{ln} {lines[i + 1]}")
            skip = True
        else:
            out.append(ln)
    return out


def _paragraphs(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    out: list[str] = []
    for block in blocks:
        lines = _join_bare_numbers([ln.strip() for ln in block.split("\n") if ln.strip()])
        # A numbered line inside a wrapped block still starts a new paragraph.
        current: list[str] = []
        for ln in lines:
            if (_NUMBERED.match(ln) or _GROUP.match(ln)) and current:
                out.append(" ".join(current))
                current = []
            current.append(ln)
            if _GROUP.match(ln):
                out.append(" ".join(current))
                current = []
        if current:
            out.append(" ".join(current))
    return out


def _title_shaped(title: str) -> bool:
    words = title.split()
    return len(words) >= MIN_TITLE_WORDS and title[:1].isupper()


def segment_text(text: str, page: int = 0) -> list[RiskSpan]:
    """Split Risk Factors text without fonts (corpus excerpts) into numbered, titled paragraphs."""
    spans: list[RiskSpan] = []
    expected: int | None = None
    group: str | None = None
    for para in _paragraphs(text):
        if _GROUP.match(para):
            group = para.rstrip(":")
            continue
        match = _NUMBERED.match(para)
        if match:
            number, rest = int(match.group(1)), match.group(2)
            title, body = first_sentence(rest)
            if (expected is None or number == expected) and _title_shaped(title):
                spans.append(
                    RiskSpan(
                        title=title,
                        body=body,
                        page_start=page,
                        page_end=page,
                        group=group,
                        numbered=True,
                        confidence=0.8,
                    )
                )
                expected = number + 1
                continue
        if spans:  # the preamble (before the first title) is skipped
            last = spans[-1]
            last.body = f"{last.body}\n\n{para}" if last.body else para
    return spans


# ------------------------------------------------------------------------- output
def to_risks(spans: Iterable[RiskSpan]) -> list[Risk]:
    """Number the spans as ``Risk`` rows (``rid`` = ``r1``, ``r2``…, in document order)."""
    return [
        Risk(
            rid=f"r{i}",
            order=i,
            title=s.title,
            body=s.body,
            page_start=s.page_start,
            page_end=s.page_end,
            group=s.group,
        )
        for i, s in enumerate(spans, start=1)
    ]
