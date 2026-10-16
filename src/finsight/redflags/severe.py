"""Severe overrides: wording that puts the risk level in the high band whatever the model says.

C3.2: five deterministic checks on the offer document's own sentences (going concern, default or
loan recall, a regulator's order, fraud, a qualified audit opinion). A sentence counts only when it
states a fact: sentences with a negation ("no", "not", "neither") or a hedge ("may", "could",
"if") are skipped, which drops the boilerplate "none of our Promoters has been debarred".
Boilerplate
sections (definitions, general information, offer procedure) are not scanned. Each hit carries its
page and the sentence it came from; the report names what the document says and nothing about what
to do (B-ADR-13). Thresholds-free on purpose: the rules are the same for every IPO.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finsight.core.schemas import PageEvidence, ParsedDoc, Section, SevereOverride

# Sections of boilerplate that mention these words as definitions or eligibility declarations.
SKIP_SECTIONS = frozenset(
    {
        "definitions",
        "general_information",
        "terms_of_the_offer",
        "offer_structure",
        "offer_procedure",
        "main_provisions_of_the_articles_of_association",
        "material_contracts_and_documents_for_inspection",
        "declaration",
    }
)
_SKIP_BEFORE = "summary"  # nothing before the Summary (cover, definitions, forward-looking) counts

# A sentence with one of these states no fact: negations and hedges.
_SOFT = re.compile(
    r"\b(?:no|not|nor|neither|never|none|nil|without|unless|whether|cannot|may|might|could|would|"
    r"if|should|in\s+the\s+event|risk\s+of|assurance|potential(?:ly)?|likely|unqualified|"
    r"such\s+as|for\s+example|means|defined|refers?\s+to|prescribe[sd]?|penal|vulnerable|"
    r"right\s+to|entitled|take\s+possession|events?\s+of\s+default|"
    r"reversed|waived|withdrawn|set\s+aside|quashed|stayed|policy|policies)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"(?<=[.;])\s+(?=[A-Z(“\"])")

_PATTERNS: dict[str, re.Pattern[str]] = {
    "going_concern": re.compile(
        r"(?:material|significant|substantial)\s+(?:uncertaint\w+|doubt)[^.]{0,140}going\s+concern"
        r"|going\s+concern[^.]{0,140}(?:material|significant|substantial)\s+(?:uncertaint|doubt)",
        re.IGNORECASE,
    ),
    "default_or_recall": re.compile(
        r"\b(?:has|have|had)\s+(?:\w+\s+){0,2}?(?:defaulted|been\s+in\s+default)\b"
        r"|\b(?:defaults?|delays?)\s+in\s+(?:the\s+)?(?:repayment|servicing)\b"
        r"|\b(?:has|have|had)\s+(?:\w+\s+){0,2}?(?:recalled|called\s+back)\b"
        r"|\blenders?\s+(?:has\s+|have\s+)?(?:recalled|called\s+back)\b"
        r"|\binvoked\s+(?:the\s+)?(?:recall|acceleration)\b"
        r"|\brecall\s+notice\b",
        re.IGNORECASE,
    ),
    "regulator_order": re.compile(
        r"\bwilful\s+defaulter\b|\bwillful\s+defaulter\b"
        r"|\b(?:debarred|barred)\s+from\s+(?:accessing|dealing\s+in|buying|selling)\b"
        r"|\b(?:SEBI|RBI|Reserve\s+Bank\s+of\s+India|Securities\s+and\s+Exchange\s+Board\s+of\s+"
        r"India|Enforcement\s+Directorate|Special\s+Director|Adjudicating\s+Officer)"
        r"[^.]{0,100}?\b(?:(?:passed|issued)\s+(?:an?\s+|the\s+)?(?:interim\s+|final\s+|"
        r"adjudicat\w+\s+|ex[\s-]parte\s+)?order\b|imposed\s+(?:an?\s+)?(?:monetary\s+)?"
        r"(?:penalty|fine)\b)",
        re.IGNORECASE,
    ),
    "fraud": re.compile(
        r"\b(?:classified|declared|reported|categori[sz]ed)\s+(?:as\s+)?(?:an?\s+)?fraud\b"
        r"|\bfraud(?:ulent)?\s+(?:account|case|FIR)\b"
        r"|\bFIR\b[^.]{0,100}\b(?:cheating|fraud|forgery|misappropriation)\b"
        r"|\b(?:charged|convicted)\b[^.]{0,60}\b(?:fraud|cheating)\b",
        re.IGNORECASE,
    ),
    "qualified_audit": re.compile(
        r"\b(?:qualified|adverse)\s+(?:audit\s+)?(?:opinion|conclusion)\b"
        r"|\bdisclaimer\s+of\s+opinion\b",
        re.IGNORECASE,
    ),
}

TITLES = {
    "going_concern": "Doubt about continuing as a going concern",
    "default_or_recall": "Loan default or recall",
    "regulator_order": "Regulator order or wilful-defaulter listing",
    "fraud": "Fraud classification or fraud case",
    "qualified_audit": "Qualified or adverse audit opinion",
}
SENTENCES = {
    "going_concern": "The document raises doubt about the company's ability to continue as a "
    "going concern.",
    "default_or_recall": "The document says a borrower in the group defaulted on, or had a loan "
    "recalled by, a lender.",
    "regulator_order": "The document mentions an order, debarment, penalty or wilful-defaulter "
    "classification from a regulator or lender.",
    "fraud": "The document mentions an account classified as fraud or a fraud-related case.",
    "qualified_audit": "The auditor gave a qualified or adverse opinion.",
}
RULES = {
    "going_concern": "A sentence that states a material uncertainty about going concern.",
    "default_or_recall": "A sentence that states a default, a delay in repayment, a recall or an "
    "NPA classification as having happened.",
    "regulator_order": "A sentence that states a debarment, an order by SEBI / RBI / ED, a "
    "penalty or a wilful-defaulter classification as having happened.",
    "fraud": "A sentence that states a fraud classification, a fraud FIR or a charge of fraud.",
    "qualified_audit": "A sentence that states a qualified or adverse opinion, or the summary's "
    "auditor remark is a qualification.",
}


@dataclass(frozen=True)
class _Hit:
    page: int
    sentence: str


def _scan_pages(doc: ParsedDoc, sections: list[Section]) -> list[int]:
    """Pages from the Summary onwards, minus the boilerplate sections."""
    first = next((s.start_page for s in sections if s.id == _SKIP_BEFORE), 1)
    skip: set[int] = set()
    for s in sections:
        if s.id in SKIP_SECTIONS:
            skip.update(range(s.start_page, s.end_page + 1))
    return [p.number for p in doc.pages if p.number >= first and p.number not in skip]


def sentences_of(text: str) -> list[str]:
    """Sentences of a page's text (whitespace collapsed)."""
    return [s.strip() for s in _SENTENCE.split(" ".join(text.split())) if s.strip()]


# A default or delay only counts when the sentence is about borrowed money (not statutory dues).
_DEBT = re.compile(
    r"\b(?:loans?|borrowings?|debt|debentures?|lenders?|banks?|facilit\w+|credit|instal?lments?|"
    r"EMIs?|NPA|principal|interest)\b",
    re.IGNORECASE,
)


def classify(sentence: str) -> list[str]:
    """Which override ids a stand-alone sentence triggers (none for a negated or hedged one)."""
    if _SOFT.search(sentence):
        return []
    kinds = [k for k, rx in _PATTERNS.items() if rx.search(sentence)]
    if "default_or_recall" in kinds and not _DEBT.search(sentence):
        kinds.remove("default_or_recall")
    return kinds


def detect(
    doc: ParsedDoc, sections: list[Section], doc_id: str | None = None
) -> list[SevereOverride]:
    """The severe overrides one document triggers, one per kind (its first mention).

    Args:
        doc: The parsed offer document.
        sections: Its detected sections (boilerplate ones are skipped).
        doc_id: The id written into the evidence; defaults to ``doc.ipo_id``.
    """
    did = doc_id or doc.ipo_id
    wanted = set(_scan_pages(doc, sections))
    first: dict[str, _Hit] = {}
    count: dict[str, int] = {}
    for page in doc.pages:
        if page.number not in wanted:
            continue
        for sentence in sentences_of(page.text):
            for kind in classify(sentence):
                count[kind] = count.get(kind, 0) + 1
                first.setdefault(kind, _Hit(page.number, sentence))
    out: list[SevereOverride] = []
    for kind in _PATTERNS:
        hit = first.get(kind)
        if hit is None:
            continue
        out.append(
            SevereOverride(
                id=kind,
                title=TITLES[kind],
                sentence=SENTENCES[kind],
                evidence=PageEvidence(doc_id=did, page=hit.page, sentence=hit.sentence[:400]),
                rule=RULES[kind],
                mentions=count[kind],
            )
        )
    return out


def with_auditor(
    qualified: bool, existing: list[SevereOverride], evidence: PageEvidence | None
) -> list[SevereOverride]:
    """Add ``qualified_audit`` when the summary's remark is a qualification and no sentence hit."""
    if not qualified or evidence is None or any(o.id == "qualified_audit" for o in existing):
        return existing
    return [
        *existing,
        SevereOverride(
            id="qualified_audit",
            title=TITLES["qualified_audit"],
            sentence=SENTENCES["qualified_audit"],
            evidence=evidence,
            rule=RULES["qualified_audit"],
            mentions=1,
        ),
    ]
