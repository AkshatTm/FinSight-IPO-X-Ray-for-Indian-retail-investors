"""Auditor remarks (RF12) and whether the issuer is a financial company (RF03 routing).

* ``auditor_remarks``: the Summary's "Qualifications of the Auditors which have not been given
  effect to" statement, as printed (usually "There are no qualifications ..."); then any
  "Emphasis of Matter" paragraph and any CARO qualification or adverse remark the examination
  report pages state without negating it. ``redflags.auditor_kind`` classifies the text.
* ``is_financial_company``: the document says the company is an NBFC / housing finance company
  registered with the RBI, a bank, or an insurer registered with IRDAI. Such issuers print other
  statement layouts (interest income, premium earned), so the financial tables are read with
  their rows too, and the debt checks do not apply to lenders.
"""

from __future__ import annotations

import re

from finsight.core.schemas import Page, PageEvidence, ParsedDoc, Section, SummaryValue
from finsight.summary.financials import _pages, _section_pages, summary_pages

_HEADING = re.compile(
    r"qualifications?\s+(?:of|by)\s+(?:the\s+|our\s+)?(?:joint\s+)?(?:statutory\s+)?auditors?"
    r"(?:\s+which\s+have\s+not\s+been\s+given\s+effect\s+to\s+in\s+the\s+restated\s+"
    r"(?:consolidated\s+|standalone\s+)?financial\s+(?:information|statements))?"
    r"|auditor(?:s|’s|'s)?\s+qualifications?(?:\s+which\s+have\s+not\s+been\s+given\s+effect\s+to"
    r"\s+in\s+the\s+restated\s+(?:consolidated\s+|standalone\s+)?financial\s+(?:information|statements))?",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"(.{20,600}?\.)(?=\s+[A-Z“\"]|\s*$)", re.DOTALL)
_EMPHASIS = re.compile(r"\bEmphasis of Matters?\b", re.IGNORECASE)
_CARO = re.compile(
    r"[^.]{0,200}\b(?:qualifications?|adverse remarks?)\b[^.]{0,200}?"
    r"(?:\bCARO\b|Companies\s+\(Auditor[’']?s?\s+Report\)\s+Order)[^.]{0,200}\.",
    re.IGNORECASE,
)
_HEADING_TAIL = re.compile(
    r"^\W*which\s+have\s+not\s+been\s+given\s+effect\s+to\s+in\s+the\s+[^.]{0,90}?"
    r"(?:information|statements)\b",
    re.IGNORECASE,
)
_NO_EMPHASIS = re.compile(
    r"there\s+(?:are|is|were)\s+no\s+emphasis|no\s+emphasis\s+of\s+matter|"
    r"(?:does|do)\s+not\s+(?:contain|include)\s+any\s+emphasis",
    re.IGNORECASE,
)
_NEGATED = re.compile(r"\b(?:no|not|nil|none|neither|nor|without)\b", re.IGNORECASE)

_FINANCIAL = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:our company|the company|we)\b[^.]{0,160}?\b(?:is|are)\s+"
        r"(?:registered\s+with\s+the\s+(?:RBI|Reserve Bank of India)\s+as\s+)?"
        r"an?\s+(?:[\w-]+\s+){0,6}?(?:non[\s-]*banking\s+"
        r"financ\w+\s+compan|NBFC|housing\s+finance\s+compan|core\s+investment\s+compan)",
        r"\b(?:our company|the company|we)\b[^.]{0,160}?\b(?:life|general|health|non-life)\s+insur"
        r"(?:ance\s+compan|er\b)",
        r"\b(?:our company|the company|we)\b[^.]{0,120}?\bregistered\s+with\s+(?:the\s+)?(?:IRDAI|"
        r"Insurance Regulatory and Development Authority)",
        r"\b(?:our bank|we are an?\s+(?:[\w-]+\s+){0,3}bank\b|small\s+finance\s+bank\s+licen)",
    )
]


def _text(page: Page) -> str:
    return " ".join(page.text.split())


def summary_statement(doc: ParsedDoc, sections: list[Section], doc_id: str) -> SummaryValue | None:
    """The Summary's statement on auditor qualifications not given effect to, as printed."""
    for page in _pages(doc, summary_pages(sections)):
        text = _text(page)
        m = _HEADING.search(text)
        if m is None:
            continue
        rest = text[m.end() :]
        if tail := _HEADING_TAIL.match(rest):
            rest = rest[tail.end() :]
        s = _SENTENCE.match(rest.lstrip(" :.-–"))
        if s is None:
            continue
        sentence = " ".join(s.group(1).split())
        ev = PageEvidence(doc_id=doc_id, page=page.number, sentence=sentence)
        return SummaryValue(
            key="auditor_remarks", value=sentence, period="latest", evidence=ev, status="found"
        )
    return None


def report_remarks(doc: ParsedDoc, pages: list[int], doc_id: str) -> list[SummaryValue]:
    """Emphasis of Matter paragraphs and CARO qualifications stated in the examination report."""
    out: list[SummaryValue] = []
    emphasis = False
    for page in _pages(doc, pages):
        text = _text(page)
        for m in _EMPHASIS.finditer(text):
            if emphasis:
                break
            window = text[max(0, m.start() - 60) : m.end() + 200]
            if _NO_EMPHASIS.search(window) or _NEGATED.search(
                text[max(0, m.start() - 40) : m.start()]
            ):
                continue
            body = text[m.end() : m.end() + 300].lstrip(" :.-–")
            sentence = f"Emphasis of Matter: {body.rsplit('.', 1)[0] if '.' in body else body}."
            out.append(_remark(doc_id, page.number, sentence))
            emphasis = True
        for c in _CARO.finditer(text):
            sentence = " ".join(c.group(0).split())
            if not _NEGATED.search(sentence):
                out.append(_remark(doc_id, page.number, sentence))
    return out


def _remark(doc_id: str, page: int, sentence: str) -> SummaryValue:
    ev = PageEvidence(doc_id=doc_id, page=page, sentence=sentence[:600])
    return SummaryValue(
        key="auditor_remarks", value=sentence[:600], period="latest", evidence=ev, status="found"
    )


def extract_auditor_remarks(
    doc: ParsedDoc, sections: list[Section], doc_id: str, report_pages: list[int] | None = None
) -> list[SummaryValue]:
    """The Summary statement first, then remarks from the examination report pages."""
    remarks = []
    if (first := summary_statement(doc, sections, doc_id)) is not None:
        remarks.append(first)
    remarks.extend(report_remarks(doc, report_pages or [], doc_id))
    return remarks


def is_financial_company(doc: ParsedDoc, sections: list[Section]) -> bool:
    """The cover, Summary or Our Business says the issuer is an NBFC, bank or insurer."""
    numbers = [*range(1, 6), *summary_pages(sections), *_section_pages(sections, "our_business", 8)]
    for page in _pages(doc, dict.fromkeys(numbers)):
        text = _text(page)
        if any(p.search(text) for p in _FINANCIAL):
            return True
    return False
