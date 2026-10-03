"""What the guard says instead of an answer: a refusal and the key facts of the X-Ray.

"Here's what the prospectus says" is the whole reply to an advice question: no model is called,
nothing is predicted, and the facts shown are the X-Ray's chosen values with their pages, so the
reader can check them. The note about SEBI is plain: FinSight is not a registered adviser.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from finsight.core.schemas import FieldSpec, XRay

Language = Literal["en", "hi"]
KEY_FIELDS = (
    "fresh_issue_size",
    "ofs_amount",
    "total_issue_size",
    "price_band",
    "offer_price",
    "face_value",
    "promoters",
    "registrar",
)

REFUSALS: dict[str, dict[Language, str]] = {
    "advice_intent": {
        "en": (
            "I can't tell you whether to apply, compare IPOs, rate this one or predict prices, "
            "listing gains or profits. Here's what the prospectus says:"
        ),
        "hi": (
            "आवेदन करना चाहिए या नहीं, IPO की तुलना, रेटिंग या भाव, लिस्टिंग लाभ और मुनाफ़े का "
            "अनुमान बताना संभव नहीं है। प्रॉस्पेक्टस में यह लिखा है:"
        ),
    },
    "privacy": {
        "en": (
            "I don't give personal addresses, phone numbers, e-mails or ID numbers of people. "
            "The offer document lists the company's registered office and investor contacts; "
            "here's what it says:"
        ),
        "hi": (
            "किसी व्यक्ति का निजी पता, फ़ोन नंबर, ईमेल या पहचान संख्या बताना संभव नहीं है। "
            "ऑफ़र दस्तावेज़ में कंपनी का पंजीकृत कार्यालय और निवेशक संपर्क दिए गए हैं। यह लिखा है:"
        ),
    },
}
SEBI_NOTE: dict[Language, str] = {
    "en": (
        "FinSight is not a SEBI-registered investment adviser or research analyst. It shows what "
        "the offer document says; it is information, not advice."
    ),
    "hi": (
        "FinSight सेबी-पंजीकृत निवेश सलाहकार या रिसर्च एनालिस्ट नहीं है। यह ऑफ़र दस्तावेज़ की "
        "जानकारी दिखाता है; यह सलाह नहीं है।"
    ),
}


class Fact(TypedDict):
    """One X-Ray fact shown on the refusal card instead of advice."""

    field_id: str
    label: str
    value: str
    page: int
    doc: str
    verdict: str


def facts_payload(xray: XRay, fields: list[FieldSpec], language: Language = "en") -> list[Fact]:
    """The key X-Ray fields that have a value, in a fixed order, with their evidence page.

    ``fields`` is the registry (``extract.load_fields()``); the guard depends on core only.
    """
    labels = {f.id: f.label_hi if language == "hi" else f.label_en for f in fields}
    by_id = {f.field_id: f for f in xray.fields}
    out: list[Fact] = []
    for field_id in KEY_FIELDS:
        result = by_id.get(field_id)
        if result is None or result.chosen is None:
            continue
        out.append(
            Fact(
                field_id=field_id,
                label=labels[field_id],
                value=result.chosen.raw,
                page=result.chosen.page,
                doc=result.chosen.doc_type,
                verdict=result.verdict,
            )
        )
    return out


def refusal_text(reason: str, language: Language = "en") -> str:
    """The refusal message for ``reason`` with the SEBI note, in one language."""
    return f"{REFUSALS[reason][language]}\n\n{SEBI_NOTE[language]}"
