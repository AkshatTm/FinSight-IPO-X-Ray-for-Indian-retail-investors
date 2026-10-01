"""One table per reason code (02 section 10.3, ADR-027, ADR-044)."""

import pytest

from finsight.core.schemas import Claim, Passage
from finsight.normalize import parse_amount
from finsight.verify import NumericCheck, is_scale_mismatch, same_value, verify_answer


def passage(n: int, text: str, page: int = 3) -> Passage:
    return Passage(
        id=f"acme-2025:rhp:p{page}:c{n}", ipo_id="acme-2025", doc_type="rhp", section_id="cover",
        page_start=page, page_end=page, text=text, char_to_bbox=[],
    )  # fmt: skip


OFFER = passage(
    0,
    "INITIAL PUBLIC OFFERING AGGREGATING UP TO ₹ 29,808 MILLION COMPRISING A FRESH ISSUE OF UP "
    "TO 81,816,199 EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH AGGREGATING UP TO ₹ 26,260 MILLION "
    "AND AN OFFER FOR SALE OF UP TO 11,051,746 EQUITY SHARES AGGREGATING UP TO ₹ 3,548 MILLION.",
)
BLANK = passage(
    1,
    "THE OFFER FOR SALE OF UP TO 11,051,746 EQUITY SHARES AGGREGATES UP TO ₹[●] MILLION. "
    "THE PRICE BAND IS ₹[●] TO ₹[●] PER EQUITY SHARE.",
    page=5,
)
OTHER = passage(2, "Revenue from operations was ₹ 22,550 million in Fiscal 2025, up 28.5%.", 210)
EVIDENCE = [OFFER, OTHER]


def codes(answer: str, evidence: list[Passage] | None = None) -> list[str]:
    return [v.check.reason_code for v in verify_answer(answer, evidence or EVIDENCE).verdicts]


VERIFIED = [
    "The fresh issue is ₹ 26,260 million [1].",
    "The fresh issue is ₹ 2,626 crore [1].",  # same money, other unit
    "The fresh issue is about ₹ 26.26 billion [1].",
    "फ्रेश इश्यू ₹ 26,260 मिलियन का है [1]।",
    "फ्रेश इश्यू ₹ 2,626 करोड़ का है [1]।",
    "The offer for sale is of 11,051,746 equity shares [1].",
    "The offer for sale is of 1.11 crore equity shares [1].",  # rounded as printed
    "The total issue size is ₹ 29,808 million [1].",
    "The face value is ₹ 1 per share [1].",
    "Revenue grew 28.5% to ₹ 22,550 million [2].",
    "The company raised ₹ 26,260 million [1].",  # no metric named: the value is in the evidence
]


@pytest.mark.parametrize("answer", VERIFIED)
def test_verified(answer: str) -> None:
    result = verify_answer(answer, EVIDENCE)
    assert [v.check.reason_code for v in result.verdicts] == ["verified"] * result.n_numbers
    assert result.n_numbers >= 1
    assert result.score == 1.0
    for v in result.verdicts:
        lo, hi = v.check.evidence_char_span  # type: ignore[misc]
        source = next(p for p in EVIDENCE if p.id == v.check.evidence_passage_id)
        assert source.text[lo:hi] == v.check.evidence_value.raw  # type: ignore[union-attr]


SCALE_MISMATCH = [
    "The fresh issue is ₹ 26,260 crore [1].",  # same digits, million read as crore
    "The fresh issue is ₹ 26,260 lakh [1].",
    "The fresh issue is ₹ 26,260 [1].",  # the unit was dropped
    "The fresh issue is ₹ 262.6 crore [1].",  # 10x with a unit swap
    "फ्रेश इश्यू ₹ 26,260 करोड़ का है [1]।",
    "The offer for sale is of 11,051,746 crore equity shares [1].",
]


@pytest.mark.parametrize("answer", SCALE_MISMATCH)
def test_scale_mismatch(answer: str) -> None:
    result = verify_answer(answer, EVIDENCE)
    assert [v.check.reason_code for v in result.verdicts] == ["scale_mismatch"]
    assert result.verdicts[0].check.status == "contradicted"
    assert result.score == 0.0


def test_the_same_money_in_lakh_is_not_a_mismatch() -> None:
    assert codes("The fresh issue is ₹ 2,62,600 lakh [1].") == ["verified"]


WRONG_VALUE = [
    "The fresh issue is ₹ 26,360 million [1].",  # one digit changed
    "The fresh issue is ₹ 2,726 crore [1].",
    "The offer for sale is of 11,051,764 equity shares [1].",
    "The total issue size is ₹ 30,000 million [1].",
    "फ्रेश इश्यू ₹ 26,360 मिलियन का है [1]।",
]


@pytest.mark.parametrize("answer", WRONG_VALUE)
def test_wrong_value(answer: str) -> None:
    result = verify_answer(answer, EVIDENCE)
    assert [v.check.reason_code for v in result.verdicts] == ["wrong_value"]
    assert result.verdicts[0].check.status == "contradicted"


def test_ten_times_with_other_digits_and_the_same_unit_is_a_wrong_value() -> None:
    # ADR-027: face value ₹ 10 vs ₹ 1 is a different number, not a unit slip
    assert codes("The face value is ₹ 10 per share [1].") == ["wrong_value"]
    assert not is_scale_mismatch(parse_amount("₹ 10"), parse_amount("₹ 1"))  # type: ignore[arg-type]
    assert is_scale_mismatch(parse_amount("₹ 800 crore"), parse_amount("₹ 800 million"))  # type: ignore[arg-type]
    assert is_scale_mismatch(parse_amount("₹ 80 crore"), parse_amount("₹ 8,000 million"))  # type: ignore[arg-type]
    assert not is_scale_mismatch(parse_amount("₹ 81 crore"), parse_amount("₹ 8,000 million"))  # type: ignore[arg-type]


WRONG_METRIC = [
    "The fresh issue is ₹ 3,548 million [1].",  # that is the offer for sale
    "The offer for sale is ₹ 26,260 million [1].",
    "फ्रेश इश्यू ₹ 3,548 मिलियन का है [1]।",
    "The total issue size is ₹ 26,260 million [1].",
]


@pytest.mark.parametrize("answer", WRONG_METRIC)
def test_wrong_metric(answer: str) -> None:
    result = verify_answer(answer, EVIDENCE)
    assert [v.check.reason_code for v in result.verdicts] == ["wrong_metric"]
    assert result.verdicts[0].check.status == "contradicted"


NOT_FOUND = [
    "The company will spend ₹ 4,125 million on marketing [1].",
    "EBITDA margin was 14.2% [2].",
    "ईबीआईटीडीए ₹ 4,125 मिलियन रहा [2]।",
]


@pytest.mark.parametrize("answer", NOT_FOUND)
def test_not_found(answer: str) -> None:
    result = verify_answer(answer, EVIDENCE)
    assert [v.check.reason_code for v in result.verdicts] == ["not_found"]
    assert result.verdicts[0].check.status == "unverifiable"
    assert result.verdicts[0].check.evidence_passage_id is None


PLACEHOLDER = [
    "The offer for sale is ₹ 3,548 million [1].",  # the passage leaves it blank
    "The price band is ₹ 304 to ₹ 321 [1].",
    "The offer for sale is ₹ [●] million [1].",  # the answer repeats the blank
]


@pytest.mark.parametrize("answer", PLACEHOLDER)
def test_placeholder(answer: str) -> None:
    result = verify_answer(answer, [BLANK])
    assert [v.check.reason_code for v in result.verdicts] == ["placeholder"]
    assert result.verdicts[0].check.status == "unverifiable"
    assert result.verdicts[0].check.evidence_value.raw.startswith("₹[●]")  # type: ignore[union-attr]


def test_a_real_value_beats_a_blank_for_the_same_metric() -> None:
    # RHP says [●], the Prospectus passage has the number
    assert codes("The offer for sale is ₹ 3,548 million [1].", [BLANK, OFFER]) == ["verified"]
    assert codes("The offer for sale is ₹ 3,648 million [1].", [BLANK, OFFER]) == ["wrong_value"]


def test_cited_passage_is_shown_as_evidence_when_it_has_the_value() -> None:
    twice = passage(5, "The Fresh Issue aggregates up to ₹ 26,260 million.", page=67)
    result = verify_answer("The fresh issue is ₹ 26,260 million [2].", [OFFER, twice])
    assert result.verdicts[0].check.evidence_passage_id == twice.id
    result = verify_answer("The fresh issue is ₹ 26,260 million [1].", [OFFER, twice])
    assert result.verdicts[0].check.evidence_passage_id == OFFER.id


def test_score_counts_verified_numbers_only() -> None:
    answer = (
        "The fresh issue is ₹ 26,260 million [1]. The offer for sale is ₹ 3,548 crore [1]. "
        "Marketing gets ₹ 999 million [1]."
    )
    result = verify_answer(answer, EVIDENCE)
    assert [v.check.reason_code for v in result.verdicts] == [
        "verified",
        "scale_mismatch",
        "not_found",
    ]
    assert result.score == pytest.approx(1 / 3)
    assert [v.index for v in result.verdicts] == [0, 1, 2]
    for v in result.verdicts:
        lo, hi = v.answer_char_span
        assert answer[lo:hi] == v.check.answer_value.raw  # type: ignore[union-attr]
    assert verify_answer("The registrar is KFin Technologies Limited [1].", EVIDENCE).score is None


def test_rounded_share_counts_match_at_the_printed_precision() -> None:
    exact = parse_amount("81,816,199 equity shares")
    assert same_value(parse_amount("8.18 crore shares"), exact)  # type: ignore[arg-type]
    assert not same_value(parse_amount("8.28 crore shares"), exact)  # type: ignore[arg-type]
    assert not same_value(parse_amount("81,816,198 equity shares"), exact)  # type: ignore[arg-type]


def test_protocol_check_returns_one_result_per_amount() -> None:
    sentence = "The fresh issue is ₹ 26,260 million and the offer for sale ₹ 3,548 crore [1]."
    amounts = [parse_amount("₹ 26,260 million"), parse_amount("₹ 3,548 crore")]
    claim = Claim(sentence=sentence, char_span=(0, len(sentence)), amounts=amounts, cited=[1])  # type: ignore[arg-type]
    results = NumericCheck().check(claim, EVIDENCE)
    assert [r.reason_code for r in results] == ["verified", "scale_mismatch"]
    assert all(r.check == "numeric" for r in results)
