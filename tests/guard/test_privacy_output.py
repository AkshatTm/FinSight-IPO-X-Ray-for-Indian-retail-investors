"""Layer 3 of the privacy fix (ADR-048): an answer never gives a person's address or contact."""

import pytest

from finsight.guard import check_output

LEAKS = [
    # the three shapes the rated bake-off sheet showed (addresses here are invented)
    (
        "कंपनी के सीईओ का पता गुड़गांव में स्थित हैं। उनका निवास 'हाऊस नंबर 8ए, जीपी-2' है [1]।",
        "address_detail",
    ),
    ("उनके पता 12 मेपल कोर्ट, स्प्रिंगफील्ड, न्यू जर्सी है [1]।", "personal_address"),
    ("The CEO lives at 12 Maple Court, Springfield [1].", "personal_address"),
    ("His residential address is Flat 12, Maple Heights, Pune [1].", "address_detail"),
    ("The director's address: House No. 8A, Sector 22, Gurugram [2].", "address_detail"),
    ("You can reach the promoter at 9876543210 [1].", "phone_or_email"),
    ("Contact the founder at rao.founder@example.com [1].", "phone_or_email"),
    ("The promoter's PAN is ABCDE1234F [1].", "identity_number"),
    ("सेक्टर -२२ में उनका फ्लैट है [1]।", "address_detail"),
]
FINE = [
    "The registrar is KFin Technologies Limited [1].",
    "The registered office is at Tower B, Plot 5, Sector 62, Noida [1].",
    "For grievances, e-mail the Compliance Officer at investor@example.com [2].",
    "इस ऑफ़र का रजिस्ट्रार KFin Technologies Limited है [1]।",
    "The fresh issue is up to ₹ 26,260 million [1].",
    "I could not find this in the document.",
    "",
]


@pytest.mark.parametrize(("answer", "category"), LEAKS)
def test_personal_address_and_contacts_are_blocked(answer: str, category: str) -> None:
    check = check_output(answer)
    assert check.blocked, answer
    assert check.category == category or check.category is not None


@pytest.mark.parametrize("answer", FINE)
def test_business_contacts_and_facts_pass(answer: str) -> None:
    assert not check_output(answer).blocked


def test_identity_numbers_are_blocked_even_in_a_business_answer() -> None:
    check = check_output(
        "The registrar's contact is on file; the promoter's PAN is ABCDE1234F [1]."
    )
    assert check.blocked
    assert check.category == "identity_number"


def test_question_context_can_mark_an_answer_as_business() -> None:
    answer = "Plot 5, Sector 62, Noida [1]."
    assert check_output(answer, "What is the registered office address?").blocked is False
    assert check_output(answer, "Where does the CEO live?").blocked is True
