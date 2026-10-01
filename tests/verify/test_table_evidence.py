"""Table cells under a unit header are evidence (ADR-044).

The two passages in ``data/samples/table_passages.jsonl`` are the real Objects-of-the-Offer
tables of Ather Energy (RHP p. 172) and Urban Company (RHP p. 164), as the index stores them.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from finsight.core.schemas import Money, Passage, Placeholder
from finsight.verify import evidence_amounts, verify_answer
from finsight.verify.table_evidence import table_amounts, table_scale

SAMPLES = Path(__file__).parents[2] / "data" / "samples" / "table_passages.jsonl"
TABLES = {
    row["ipo_id"]: Passage.model_validate(row)
    for row in map(json.loads, SAMPLES.read_text(encoding="utf-8").splitlines())
}
ATHER = TABLES["ather-energy-2025"]
URBAN = TABLES["urban-company-2025"]


def table(text: str) -> Passage:
    return Passage(
        id="acme-2025:rhp:p90:c0", ipo_id="acme-2025", doc_type="rhp", section_id="the_offer",
        page_start=90, page_end=90, text=text, char_to_bbox=[],
    )  # fmt: skip


def checks(answer: str, passage: Passage) -> list[str]:
    return [v.check.reason_code for v in verify_answer(answer, [passage]).verdicts]


def test_the_real_tables_carry_their_unit_header() -> None:
    assert table_scale(ATHER.text) == "₹ in million"
    assert table_scale(URBAN.text) == "₹ in million"
    assert table_scale("The Fresh Issue aggregates up to ₹ 26,260 million.") is None
    assert table_amounts("Revenue was ₹ 22,550 million.") is None


def test_every_number_cell_of_the_ather_table_is_read_in_million() -> None:
    evidence = evidence_amounts([ATHER])
    money = [e for e in evidence if isinstance(e.amount, Money)]
    assert [e.amount.raw for e in money] == [
        "9,272", "7,055", "2,217", "400", "400", "7,500", "2,700", "2,650", "2,150",
        "3,000", "1,500", "1,500",
    ]  # fmt: skip
    assert all(e.amount.scale_word == "million" and e.unit == "₹ in million" for e in money)  # type: ignore[union-attr]
    assert money[0].amount.value_inr == Decimal("9272000000")  # type: ignore[union-attr]
    assert len([e for e in evidence if isinstance(e.amount, Placeholder)]) == 8
    for e in evidence:  # serial numbers "1." and "Fiscal 2026" are not amounts
        assert ATHER.text[e.start : e.end] == e.amount.raw


def test_the_metric_of_a_cell_comes_from_its_own_row() -> None:
    by_raw = {e.amount.raw: e.metrics for e in evidence_amounts([ATHER])}
    assert by_raw["400"] == ("borrowings",)
    assert by_raw["9,272"] == ()
    assert by_raw["7,500"] == ()  # the row above names borrowings; this row does not


ATHER_VERIFIED = [
    "Ather will spend ₹ 9,272 million on capital expenditure for an E2W factory [1].",
    "Ather will spend ₹ 927.2 crore on a new factory in Maharashtra [1].",
    "एथर नई फैक्ट्री पर ₹ 927.2 करोड़ खर्च करेगी [1]।",
    "₹ 7,500 million goes to research, of which ₹ 2,700 million in Fiscal 2026 [1].",
    "The company will repay borrowings of ₹ 400 million [1].",
    "Marketing initiatives get ₹ 300 crore [1].",
]


@pytest.mark.parametrize("answer", ATHER_VERIFIED)
def test_ather_objects_answers_are_verified(answer: str) -> None:
    result = verify_answer(answer, [ATHER])
    assert result.n_numbers >= 1
    assert [v.check.reason_code for v in result.verdicts] == ["verified"] * result.n_numbers
    for v in result.verdicts:
        assert v.check.evidence_passage_id == ATHER.id
        lo, hi = v.check.evidence_char_span  # type: ignore[misc]
        assert ATHER.text[lo:hi] == v.check.evidence_value.raw  # type: ignore[union-attr]
        assert "(₹ in million)" in v.check.reason


ATHER_SLIPS = [
    "Ather will spend ₹ 9,272 crore on capital expenditure [1].",
    "Ather will spend ₹ 9,272 lakh on capital expenditure [1].",
    "Ather will spend ₹ 9,272 on capital expenditure [1].",  # the unit was dropped
    "एथर नई फैक्ट्री पर ₹ 9,272 करोड़ खर्च करेगी [1]।",
    "The company will repay borrowings of ₹ 400 crore [1].",
]


@pytest.mark.parametrize("answer", ATHER_SLIPS)
def test_a_unit_slip_against_a_table_cell_is_a_scale_mismatch(answer: str) -> None:
    result = verify_answer(answer, [ATHER])
    assert [v.check.reason_code for v in result.verdicts] == ["scale_mismatch"]
    assert "(₹ in million)" in result.verdicts[0].check.reason


def test_other_verdicts_on_the_ather_table() -> None:
    assert checks("The company will repay borrowings of ₹ 450 million [1].", ATHER) == [
        "wrong_value"
    ]
    assert checks("General corporate purposes get ₹ [●] million [1].", ATHER) == ["placeholder"]
    assert checks("Ather will spend ₹ 9,300 million on the factory [1].", ATHER) == ["not_found"]
    # a price is never "in million": the 400 in the borrowings row says nothing about it
    assert checks("The offer price is ₹ 400 per share [1].", ATHER) == ["not_found"]


URBAN_CASES = [
    ("₹ 1,900 million goes to technology and cloud infrastructure [1].", "verified"),
    ("₹ 190 crore goes to technology and cloud infrastructure [1].", "verified"),
    ("Lease payments for offices take ₹ 750.00 million [1].", "verified"),
    ("मार्केटिंग पर ₹ 90 करोड़ खर्च होंगे [1]।", "verified"),
    ("₹ 1,900 crore goes to technology and cloud infrastructure [1].", "scale_mismatch"),
    ("Lease payments for offices take ₹ 750 lakh [1].", "scale_mismatch"),
    ("Marketing activities get ₹ 800 million [1].", "not_found"),
]


@pytest.mark.parametrize(("answer", "code"), URBAN_CASES)
def test_urban_company_objects_table(answer: str, code: str) -> None:
    assert checks(answer, URBAN) == [code]


def test_urban_company_cells_keep_their_two_decimals() -> None:
    money = [e.amount for e in evidence_amounts([URBAN]) if isinstance(e.amount, Money)]
    assert [m.raw for m in money][:4] == ["1,900.00", "420.00", "740.00", "740.00"]
    assert len(money) == 12
    assert {m.precision for m in money} == {2}


def test_a_plain_rupee_header_does_not_scale_bare_cells() -> None:
    # capital structure tables mix rupees and share counts under "(in ₹, except share data)"
    capital = table(
        "[Table, ₹]\nParticulars | Aggregate value at face value\n"
        "Authorised share capital | 5,000,000,000\n"
        "Securities premium | ₹ 320 per Equity Share"
    )
    assert [e.amount.raw for e in evidence_amounts([capital])] == ["₹ 320"]
    assert evidence_amounts([capital])[0].metrics == ("premium",)


def test_years_and_rows_with_their_own_unit_are_not_in_the_header_unit() -> None:
    financials = table(
        "[Table, ₹ in million]\nParticulars | 2025 | 2024\n"
        "Revenue from operations | 22,550.10 | 17,890.20\n"
        "Earnings per share (in ₹) | (36.50) | (47.00)\n"
        "EBITDA margin (%) | (25.8) | (36.1)\n"
        "Loss for the year | (8,123.00) | (10,597.00)"
    )
    evidence = evidence_amounts([financials])
    assert [(e.amount.raw, e.metrics) for e in evidence] == [
        ("22,550.10", ("revenue",)),
        ("17,890.20", ("revenue",)),
        ("(8,123.00)", ("profit",)),
        ("(10,597.00)", ("profit",)),
    ]
    assert checks("Revenue from operations was ₹ 2,255.01 crore [1].", financials) == ["verified"]
    assert checks("Revenue from operations was ₹ 22,550.10 crore [1].", financials) == [
        "scale_mismatch"
    ]
    assert checks("Revenue from operations was ₹ 23,550.10 million [1].", financials) == [
        "wrong_value"
    ]
