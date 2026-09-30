from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from finsight.core.schemas import (
    Amount,
    Candidate,
    CheckResult,
    Claim,
    Count,
    FieldResult,
    ListValue,
    Money,
    Page,
    ParsedDoc,
    Passage,
    Percent,
    Placeholder,
    Range,
    TableValue,
    TextValue,
    Value,
    Word,
    XRay,
)

CRORE_800 = Money(
    kind="money",
    value_inr=Decimal("8000000000.00"),
    currency="INR",
    raw="₹ 800.00 crore",
    scale_word="crore",
    precision=2,
)

VALUES: list[Value] = [
    CRORE_800,
    Count(kind="count", value=12345678, raw="1,23,45,678", unit="equity shares"),
    Percent(kind="percent", value=Decimal("64.00"), raw="64.00%", is_bps=False),
    Placeholder(kind="placeholder", raw="[●]"),
    Range(
        kind="range",
        low=CRORE_800.model_copy(update={"raw": "₹ 440"}),
        high=CRORE_800.model_copy(update={"raw": "₹ 463"}),
        raw="₹ 440 to ₹ 463",
    ),
    TextValue(kind="text", text="KFin Technologies Limited"),
    ListValue(kind="list", items=["ICICI Securities Limited", "Axis Capital Limited"]),
    TableValue(kind="table", columns=["Purpose", "Amount"], rows=[["Repay debt", "₹ 200 crore"]]),
]


@pytest.mark.parametrize("value", VALUES, ids=lambda v: v.kind)
def test_every_value_kind_round_trips_through_json(value: Value) -> None:
    adapter = TypeAdapter(Value)
    restored = adapter.validate_json(adapter.dump_json(value))
    assert restored == value
    assert type(restored) is type(value)


def test_money_serialises_decimals_as_strings() -> None:
    dumped = CRORE_800.model_dump(mode="json")
    assert dumped["value_inr"] == "8000000000.00"
    assert dumped["kind"] == "money"


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Value).validate_python({"kind": "bogus", "raw": "x"})


def test_amount_excludes_text_values() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Amount).validate_python({"kind": "text", "text": "x"})


def test_placeholder_is_never_a_zero_money() -> None:
    restored = TypeAdapter(Value).validate_python({"kind": "placeholder", "raw": "[●]"})
    assert isinstance(restored, Placeholder)


def _candidate(doc_type: str = "rhp") -> Candidate:
    return Candidate(
        field_id="fresh_issue_size",
        extractor="rules",
        doc_type=doc_type,  # type: ignore[arg-type]
        raw="₹ 800.00 crore",
        value=CRORE_800,
        page=12,
        printed_page="8",
        bbox=(72.0, 410.2, 301.5, 422.8),
        score=0.93,
        passage_id="acme-2025:p12:c0",
    )


def test_xray_round_trips_with_both_documents() -> None:
    result = FieldResult(
        field_id="fresh_issue_size",
        chosen=_candidate(),
        candidates=[_candidate(), _candidate("prospectus")],
        verdict="verified",
        reason_code="verified",
        reason="Matches The Offer (p. 67).",
        checks=[],
    )
    xray = XRay(
        ipo_id="acme-2025",
        company="Acme Limited",
        built_at=datetime(2026, 10, 1, tzinfo=UTC),
        fields=[result],
        derived={"fresh_share_pct": "64.00", "ofs_share_pct": "36.00"},
    )
    assert XRay.model_validate_json(xray.model_dump_json()) == xray


def test_field_result_needs_a_known_reason_code() -> None:
    with pytest.raises(ValidationError):
        FieldResult(
            field_id="x", chosen=None, candidates=[], verdict="verified",
            reason_code="made_up", reason="", checks=[],
        )  # fmt: skip


def test_parsed_doc_carries_doc_type_and_printed_page() -> None:
    page = Page(
        number=12, printed_page="8", width=612, height=792,
        words=[Word(text="Fresh", bbox=(72, 410, 98, 422), font_size=9.0, bold=False)],
        text="Fresh", is_scanned=False,
    )  # fmt: skip
    doc = ParsedDoc(
        ipo_id="acme-2025", doc_type="prospectus", source_path="data/raw/prospectus/acme-2025.pdf",
        n_pages=1, pages=[page], sha256="0" * 64,
    )  # fmt: skip
    assert ParsedDoc.model_validate_json(doc.model_dump_json()).pages[0].printed_page == "8"


def test_passage_requires_char_to_bbox() -> None:
    with pytest.raises(ValidationError):
        Passage.model_validate(
            {"id": "a:p1:c0", "ipo_id": "a", "doc_type": "rhp", "section_id": "s",
             "page_start": 1, "page_end": 1, "text": "t"}
        )  # fmt: skip


def test_check_result_and_claim_round_trip() -> None:
    check = CheckResult(
        check="numeric", status="contradicted", reason_code="scale_mismatch",
        reason="differs by exactly 100x", answer_value=CRORE_800, evidence_value=CRORE_800,
        evidence_passage_id="a:p12:c0", evidence_char_span=(120, 134),
    )  # fmt: skip
    claim = Claim(sentence="The fresh issue is ₹800 lakh [1].", char_span=(0, 33),
                  amounts=[CRORE_800], cited=[1])  # fmt: skip
    assert CheckResult.model_validate_json(check.model_dump_json()) == check
    assert Claim.model_validate_json(claim.model_dump_json()) == claim
