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
