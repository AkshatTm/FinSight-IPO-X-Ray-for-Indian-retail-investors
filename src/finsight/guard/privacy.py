"""Privacy guard: no personal addresses, phone numbers, e-mails or ID numbers of people.

Offer documents print business contacts (registered office, registrar, lead managers, the
compliance officer for investor complaints) and FinSight answers those. It refuses a private
person's home address, personal phone or e-mail, and identity numbers: the first Hindi bake-off
showed a 0.8b model reading a director's residential address out of the document, and a larger
one pretending to look for it. A refusal is decided on the question, before any retrieval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from finsight.guard.advice import normalize_question

Reason = Literal["privacy"]
REASON: Reason = "privacy"

_PERSON = (
    r"(?:ceo|cfo|coo|cto|founder|co-founder|promoter|director|chairman|chairperson|managing director|"
    r"md|kmp|key managerial|executive|owner|his|her|their|mr|mrs|ms|shri|smt|"
    r"सीईओ|संस्थापक|प्रमोटर|निदेशक|चेयरमैन|मालिक|श्री|श्रीमती|ceo ka|founder ka|promoter ka|director ka)"
)
_CONTACT = (
    r"(?:address|residence|residential|phone|mobile|cell|telephone|contact number|number|e-?mail|email|"
    r"whatsapp|house|home|पता|फोन|मोबाइल|नंबर|ईमेल|घर|निवास|pata|ghar)"
)
RULES: list[tuple[str, str]] = [
    (
        "home_address",
        r"\b(?:home|house|residential|residence|private|personal|current|permanent)\b.{0,15}\b(?:address|phone|mobile|number|e-?mail|contact)\b",
    ),
    (
        "home_address",
        r"\bwhere (?:does|do|is)\b.{0,40}\b(?:live|stay|reside)s?\b|\blives? (?:at|in)\b.{0,20}\?",
    ),
    (
        "home_address",
        r"घर (?:का|की|के) (?:पता|पते|फोन|नंबर|ईमेल)|निजी|व्यक्तिगत (?:पता|फोन|मोबाइल|नंबर|ईमेल)|कहां रहते|कहाँ रहते|रहता है|रहती है|ghar ka (?:pata|address|number)|kahan rehte",
    ),
    (
        "personal_contact",
        rf"\b{_PERSON}\b.{{0,30}}\b{_CONTACT}\b|\b{_CONTACT}\b.{{0,20}}\b(?:of|for) (?:the |our |its )?{_PERSON}\b",
    ),
    (
        "personal_contact",
        rf"{_PERSON}.{{0,30}}(?:पता|फोन|मोबाइल|नंबर|ईमेल)|(?:पता|फोन|मोबाइल|नंबर|ईमेल).{{0,20}}{_PERSON}",
    ),
    (
        "identity_number",
        r"\b(?:aadhaar|aadhar|passport|driving licen[cs]e|voter id|pan (?:number|card|no))\b.{0,25}\b(?:of|for|number)\b|\b(?:his|her|their|promoter'?s?|director'?s?|ceo'?s?) (?:aadhaar|aadhar|passport|pan)\b|आधार|पासपोर्ट|पैन (?:नंबर|कार्ड)",
    ),
]
_COMPILED = [(name, re.compile(pattern)) for name, pattern in RULES]
# a business contact is fine even next to the word "number" or "address"
_BUSINESS = re.compile(
    r"\b(?:registered|corporate|head|principal|branch) office\b|\bregistrar\b|\blead managers?\b|\bbrlms?\b|"
    r"\bcompliance officer\b|\binvestor grievance|\bcompany secretary\b|\bcin\b|रजिस्टर्ड ऑफिस|पंजीकृत कार्यालय|रजिस्ट्रार|"
    r"कंपनी सचिव|अनुपालन अधिकारी"
)


@dataclass(frozen=True)
class PrivacyCheck:
    """Result of the private-data rules on one question."""

    blocked: bool
    reason: Reason | None = None
    category: str | None = None
    matched: str | None = None


def check_privacy(question: str) -> PrivacyCheck:
    """Does the question ask for a private person's address, contact or identity number?"""
    q = normalize_question(question)
    if not q or _BUSINESS.search(q):
        return PrivacyCheck(False)
    for category, rx in _COMPILED:
        if m := rx.search(q):
            return PrivacyCheck(True, REASON, category, m.group().strip())
    return PrivacyCheck(False)


# ---- layer 3: the answer itself (ADR-048) ----
# The question guard above cannot see a model that volunteers an address in answer to something
# else ("who is the CEO?"). Every answer is checked before it reaches the reader; business
# contacts (registered office, registrar, compliance officer) are allowed.
_PERSON_CUE = (
    r"(?:ceo|cfo|coo|cto|founder|promoter|director|chairman|chairperson|kmp|his|her|their|him|"
    r"mr|mrs|ms|shri|smt|सीईओ|संस्थापक|प्रमोटर|निदेशक|चेयरमैन|उनका|उनके|उनकी|इनका|इनके|श्री|श्रीमती)"
)
_ADDRESS_CUE = (
    r"(?:address|residen\w*|lives?|resides?|home|house|पता|पते|निवास|रहते|रहता|रहती|ठिकाना|घर)"
)
_OUTPUT_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "personal_address",
        re.compile(
            rf"\b{_PERSON_CUE}\b.{{0,60}}{_ADDRESS_CUE}|{_ADDRESS_CUE}.{{0,60}}\b{_PERSON_CUE}\b"
            rf"|{_PERSON_CUE}.{{0,60}}(?:पता|पते|निवास|रहते|रहता|रहती|ठिकाना)"
            rf"|(?:पता|पते|निवास|रहते|रहता|रहती|ठिकाना).{{0,60}}{_PERSON_CUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "address_detail",
        re.compile(
            r"\b(?:house|flat|plot|door|villa)\s*(?:no\.?|number|#)\s*\w+|"
            r"\b(?:apartments?|residency|enclave|society)\b|\bsector[\s-]*[\d\u0966-\u096f]+|"
            r"हा[ऊउ]स\s*नंबर|फ्लैट|अपार्टमेंट|सेक्टर[\s-]*[\d\u0966-\u096f]+|मकान\s*नंबर|"
            r"\b\d{1,4}\s+[A-Z][a-z]+\s+(?:Ct|Court|St|Street|Ave|Avenue|Dr|Drive|Ln|Lane|Rd|Road)\b|"
            r"\bresidential address\b|\bhome address\b",
            re.IGNORECASE,
        ),
    ),
    ("identity_number", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b|\b\d{4}\s\d{4}\s\d{4}\b")),
    (
        "phone_or_email",
        re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b|\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ),
]


@dataclass(frozen=True)
class OutputCheck:
    """Result of checking an answer for private data before it is shown."""

    blocked: bool
    category: str | None = None
    matched: str | None = None


def check_output(answer: str, question: str = "") -> OutputCheck:
    """Does an answer give a person's home address, phone, e-mail or ID number?

    A business context (registered office, registrar, lead managers, the compliance officer) in
    the answer or its question lets address-like text through, except identity numbers.
    """
    text = answer.strip()
    if not text:
        return OutputCheck(False)
    business = bool(_BUSINESS.search(normalize_question(text) + " " + normalize_question(question)))
    for category, rx in _OUTPUT_RULES:
        if business and category != "identity_number":
            continue
        if m := rx.search(text):
            return OutputCheck(True, category, m.group().strip())
    return OutputCheck(False)
