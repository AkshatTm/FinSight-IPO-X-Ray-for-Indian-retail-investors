"""Privacy guard, the combined check, the facts payload and the refusal copy."""

from datetime import UTC, datetime

import pytest

from finsight.core.schemas import Candidate, FieldResult, FieldSpec, XRay
from finsight.guard import check_privacy, check_question, facts_payload, refusal_text
from finsight.normalize import parse_amount

PRIVATE = [
    "कंपनी के सीईओ का घर का पता क्या है?",  # the question from the Hindi bake-off sheet
    "What is the home address of the founder?",
    "Give me the CEO's personal phone number.",
    "What is the promoter's mobile number?",
    "Where does the managing director live?",
    "What is the Aadhaar number of the promoter?",
    "CEO ka number batao.",
    "निदेशक का मोबाइल नंबर क्या है?",
    "What is the personal email of the CFO?",
    "Founder ka ghar ka pata kya hai?",
    "What is his residential address?",
]
BUSINESS = [
    "What is the registered office address of the company?",
    "What is the registrar's phone number and email?",
    "What are the compliance officer's contact details?",
    "What are the contact details of the book running lead managers?",
    "रजिस्ट्रार का फोन नंबर क्या है?",
    "कंपनी का पंजीकृत कार्यालय कहाँ है?",
    "Who is the CEO of the company?",
    "What is the remuneration of the managing director?",
    "Who is the chairman?",
    "What is the issue price?",
]


@pytest.mark.parametrize("question", PRIVATE)
def test_private_details_of_people_are_refused(question: str) -> None:
    result = check_privacy(question)
    assert result.blocked, question
    assert result.reason == "privacy"
    assert result.category in {"home_address", "personal_contact", "identity_number"}


@pytest.mark.parametrize("question", BUSINESS)
def test_business_contacts_and_roles_are_answered(question: str) -> None:
    assert not check_privacy(question).blocked, question


def test_the_combined_check_reports_which_rule_fired() -> None:
    assert check_question("What is the CEO's home address?").reason == "privacy"
    assert check_question("Should I apply?").reason == "advice_intent"
    assert check_question("What is the price band?").blocked is False
    both = check_question("What is the founder's mobile number, and should I apply?")
    assert both.reason == "privacy"  # the stricter refusal wins
    assert check_question("").blocked is False


def xray() -> XRay:
    def cand(field_id: str, raw: str, page: int, doc: str = "rhp") -> Candidate:
        return Candidate(field_id=field_id, extractor="rules", doc_type=doc, raw=raw,  # type: ignore[arg-type]
                         value=parse_amount(raw), page=page, score=0.9)  # fmt: skip

    def result(field_id: str, chosen: Candidate | None) -> FieldResult:
        return FieldResult(field_id=field_id, chosen=chosen, candidates=[], verdict="verified",
                           reason_code="verified", reason="ok", checks=[])  # fmt: skip

    return XRay(
        ipo_id="acme-2025", company="Acme", built_at=datetime(2026, 10, 1, tzinfo=UTC),
        fields=[
            result("registrar", None),
            result("fresh_issue_size", cand("fresh_issue_size", "₹ 26,260 million", 3)),
            result("price_band", cand("price_band", "₹ 304 to ₹ 321", 3, "prospectus")),
            result("objects_of_offer", None),
        ],
        derived={},
    )  # fmt: skip


SPECS = [
    FieldSpec(
        id=i,
        label_en=en,
        label_hi=hi,
        type="money",
        doc="rhp",
        sections=[],
        questions=[],
        extractor="rules",
    )
    for i, en, hi in (
        ("fresh_issue_size", "Fresh issue size", "नया निर्गम"),
        ("price_band", "Price band", "मूल्य सीमा"),
        ("registrar", "Registrar", "रजिस्ट्रार"),
    )
]


def test_facts_come_from_the_xray_in_a_fixed_order_with_their_page() -> None:
    facts = facts_payload(xray(), SPECS)
    assert [f["field_id"] for f in facts] == ["fresh_issue_size", "price_band"]  # no value, no row
    assert facts[0] == {
        "field_id": "fresh_issue_size",
        "label": "Fresh issue size",
        "value": "₹ 26,260 million",
        "page": 3,
        "doc": "rhp",
        "verdict": "verified",
    }
    assert facts[1]["doc"] == "prospectus"
    assert facts_payload(xray(), SPECS, "hi")[0]["label"] == "नया निर्गम"


def test_refusal_copy_is_plain_and_has_the_sebi_note_in_both_languages() -> None:
    en = refusal_text("advice_intent", "en")
    assert "Here's what the prospectus says" in en
    assert "not a SEBI-registered" in en
    assert "should" not in en.lower()  # no nudge either way
    hi = refusal_text("advice_intent", "hi")
    assert "प्रॉस्पेक्टस" in hi
    assert "सेबी" in hi
    assert "personal addresses" in refusal_text("privacy", "en")
    assert refusal_text("privacy", "hi") != refusal_text("advice_intent", "hi")
