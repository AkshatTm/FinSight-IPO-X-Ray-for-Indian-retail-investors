"""Criminal cases counted from the Outstanding Litigation chapter's sections (RF08, CC-05b).

Used only when there is no litigation summary table (an RHP without a Summary of the Offer
Document, e.g. Jio). The chapter is organised by party, then by kind of case::

    I. Outstanding litigation involving the Company
       Criminal proceedings against the Company      -> "Nil"
       Criminal proceedings by the Company           -> (i) ... (ii) ...
    II. Outstanding litigation involving the Subsidiaries
    ...

Under every "Criminal proceedings ..." heading the numbered items ("(i)", "1.", "(a)") are
counted in sequence, and "Nil" counts as zero. Party groups: the company, subsidiaries,
promoters, directors, group companies, key managerial personnel and senior management.

**Approximate, and never guessed.** An item can describe several cases ("has filed 14
complaints"), so the count is labelled "counted from sections". A criminal section with text but
no numbered items cannot be counted: then no total is given, only "there are criminal cases"
when another section counted at least one. With no criminal heading at all, nothing is returned
(Not available beats a wrong number).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from finsight.core.schemas import Count, PageEvidence, ParsedDoc, Section, SummaryValue

METHOD = "counted from sections (approximate)"
MAX_HEADING = 110  # a heading is a short line; longer lines starting "Criminal ..." are prose

_PARTY = (
    r"(?P<party>group\s+compan(?:y|ies)|subsidiar(?:y|ies)|promoters?|directors?|"
    r"key\s+managerial|senior\s+management|compan(?:y|ies)|issuer)"
)
_ENUM = r"(?:(?:[IVXL]{1,5}|[A-Z]|\d{1,2})[.)]\s+)?"  # often on its own line ("I." / "a)")
# "II. Outstanding litigation involving the Subsidiaries", "IV. ... involving RIL, the Promoter"
_PARTY_HEADING = re.compile(
    rf"^{_ENUM}(?:outstanding\s+)?(?:litigations?|proceedings|cases|matters)[^.]{{0,40}}?"
    rf"\b(?:involving|against|by|of)\b[^.]{{0,40}}?\b{_PARTY}\b",
    re.IGNORECASE,
)
_LONE_ENUM = re.compile(r"^(?:[IVXL]{1,5}|[A-Za-z]|\d{1,2})[.)]$")  # "I." / "a)" alone
_ANY_ROMAN_HEADING = re.compile(r"^[IVXL]{1,5}\.\s+\S")  # a new part of the chapter
_CRIMINAL = re.compile(
    rf"^(?:\(?[a-z0-9]{{1,4}}[.)]\s*)?criminal\s+(?:proceedings|cases|complaints|matters)\b"
    rf"(?:[^,.]{{0,60}}?\b{_PARTY}\b)?",
    re.IGNORECASE,
)
_OTHER_KIND = re.compile(
    r"^(?=.*\b(?:proceedings|litigations?|actions?|authorities|claims?|matters|cases)\b)"
    r"(?:\(?[a-z0-9]{1,4}[.)]\s*)?(?:outstanding\s+)?(?:actions?\s+(?:taken\s+)?by|civil|"
    r"material\s+(?:civil\s+)?(?:litigation|proceedings)|tax|disciplinary|other\s+(?:pending|"
    r"material|outstanding)|statutory|regulatory|pending\s+actions|claims?\s+(?:against|by))\b",
    re.IGNORECASE,
)  # a heading names a kind of case; a wrapped line such as "civil in nature." does not
_NIL = re.compile(r"^(?:nil|none|not\s+applicable)\.?$|^there\s+(?:are|is)\s+no\b", re.IGNORECASE)
_ITEM = re.compile(r"^(?:\((?P<a>[ivxl]{1,6}|\d{1,3}|[a-z])\)|(?P<b>\d{1,3})\.)(?:\s+\S|$)")
_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50}


def _roman(s: str) -> int | None:
    total, prev = 0, 0
    for ch in reversed(s.lower()):
        v = _ROMAN.get(ch)
        if v is None:
            return None
        total, prev = (total - v, prev) if v < prev else (total + v, v)
    return total


def _index(m: re.Match[str], style: str | None) -> tuple[str, int] | None:
    """(style, number) of an item label: roman "(ii)", arabic "(2)" / "2." or letter "(b)"."""
    raw = m["a"] or m["b"] or ""
    if m["b"] or raw.isdigit():
        return "arabic", int(raw)
    if style in (None, "roman") and (n := _roman(raw)) is not None:
        return "roman", n
    if len(raw) == 1:
        return "alpha", ord(raw.lower()) - ord("a") + 1
    return None


@dataclass
class _Block:
    party: str
    page: int
    items: int = 0  # length of the current numbered list
    done: int = 0  # items of earlier lists in this block (one list per named subsidiary)
    nil: bool = False
    text: bool = False  # lines that are neither items nor "Nil"
    style: str | None = None

    def add(self, line: str) -> None:
        if _LONE_ENUM.match(line):
            return  # the "a)" of the next heading, printed on its own line
        if _NIL.match(line):
            self.nil = True
            return
        if m := _ITEM.match(line):
            got = _index(m, self.style)
            if got is not None and self.style in (None, got[0]):
                if got[1] == self.items + 1:
                    self.style, self.items = got[0], got[1]
                    return
                if got[1] == 1 and self.items:  # a new list under the next named party
                    self.done, self.items = self.done + self.items, 1
                    return
        self.text = True

    @property
    def count(self) -> int | None:
        if self.items or self.done:
            return self.done + self.items
        if self.nil and not self.text:
            return 0
        return None  # text with no numbered items: not countable


@dataclass
class _Scan:
    blocks: list[_Block] = field(default_factory=list)


_PARTY_NAMES = (
    ("group compan", "group companies"), ("subsidiar", "subsidiaries"), ("promoter", "promoters"),
    ("director", "directors"), ("key managerial", "key managerial personnel"),
    ("senior management", "senior management"),
)  # fmt: skip


def _party(text: str) -> str:
    p = text.lower()
    return next((name for key, name in _PARTY_NAMES if key in p), "company")


def criminal_from_sections(
    doc: ParsedDoc, sections: list[Section], doc_id: str
) -> SummaryValue | None:
    """Criminal cases in the litigation chapter, counted per party from its sub-headings.

    Returns ``None`` when the chapter has no "Criminal proceedings" headings under a party.
    """
    sec = next((s for s in sections if s.id == "outstanding_litigation"), None)
    if sec is None:
        return None
    by_number = {p.number: p for p in doc.pages}
    party: str | None = None
    block: _Block | None = None
    blocks: list[_Block] = []
    for n in range(sec.start_page, sec.end_page + 1):
        page = by_number.get(n)
        if page is None:
            continue
        for raw in page.text.splitlines():
            line = " ".join(raw.split())
            if not line:
                continue
            short = len(line) <= MAX_HEADING
            if short and (m := _PARTY_HEADING.match(line)):
                party, block = _party(m["party"]), None
                continue
            if short and _ANY_ROMAN_HEADING.match(line):
                party, block = None, None  # tax claims, creditors, material developments
                continue
            if short and (c := _CRIMINAL.match(line)):
                named = _party(c["party"]) if c["party"] else party
                block = _Block(party=named, page=n) if named else None
                if block is not None:
                    blocks.append(block)
                continue
            if short and _OTHER_KIND.match(line):
                block = None
                continue
            if block is not None:
                block.add(line)
    if not blocks:
        return None
    counts: dict[str, int] = {}
    unknown: list[str] = []
    for b in blocks:
        if b.count is None:
            unknown.append(b.party)
        else:
            counts[b.party] = counts.get(b.party, 0) + b.count
    known = sum(counts.values())
    parts = [f"{p}: {n}" for p, n in counts.items()] + [f"{p}: not countable" for p in unknown]
    sentence = f"[criminal proceedings, {METHOD}] " + "; ".join(parts)
    ev = PageEvidence(doc_id=doc_id, page=blocks[0].page, sentence=sentence[:600])
    if unknown:
        if known > 0:  # at least this many, in sections that could be counted
            value = f"Yes — at least {known} ({METHOD}; some sections not countable)"
            return SummaryValue(
                key="criminal_cases", value=value, period="latest", evidence=ev, status="found"
            )
        return SummaryValue(key="criminal_cases", evidence=ev, status="not_found")
    status = "found" if known > 0 else "stated_zero"
    value_count = Count(value=known, raw=str(known), unit="cases")
    return SummaryValue(
        key="criminal_cases", value=value_count, period="latest", evidence=ev, status=status
    )
