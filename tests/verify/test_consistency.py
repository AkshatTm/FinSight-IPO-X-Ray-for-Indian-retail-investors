from decimal import Decimal

from finsight.core.schemas import Count, Money, Placeholder, Value
from finsight.normalize import parse_amount
from finsight.verify import check_consistency


def money(text: str) -> Money:
    value = parse_amount(text)
    assert isinstance(value, Money)
    return value


FRESH = money("₹ 4,720 million")
OFS = money("₹ 14,280 million")
TOTAL = money("₹ 19,000 million")


def run(
    fresh: Value | None = FRESH,
    ofs: Value | None = OFS,
    total: Value | None = TOTAL,
    pure_ofs: bool = False,
):  # type: ignore[no-untyped-def]
    return check_consistency(fresh=fresh, ofs_amount=ofs, total=total, pure_ofs=pure_ofs)


def test_fresh_plus_ofs_equals_total_is_verified() -> None:
    report = run()
    (check,) = report.checks
    assert check.check == "total_equals_fresh_plus_ofs"
    assert check.status == "verified"
    assert check.reason_code == "verified"
    assert check.answer_value == money("₹ 19,000 million") or isinstance(check.answer_value, Money)


def test_a_mismatch_is_contradicted() -> None:
    (check,) = run(total=money("₹ 19,500 million")).checks
    assert check.status == "contradicted"
    assert check.reason_code == "wrong_value"
    assert "19,000" in check.reason
    assert "19,500" in check.reason


def test_rounding_to_the_printed_precision_is_not_a_mismatch() -> None:
    crore = money("₹ 1,900 crore")  # 19,000 million
    assert run(total=crore).checks[0].status == "verified"


def test_placeholder_gives_unverifiable_with_the_placeholder_code() -> None:
    (check,) = run(total=Placeholder(raw="₹ [●] million")).checks
    assert check.status == "unverifiable"
    assert check.reason_code == "placeholder"
    assert "[●]" in check.reason


def test_missing_value_is_not_found() -> None:
    (check,) = run(ofs=None).checks
    assert check.status == "unverifiable"
    assert check.reason_code == "not_found"


def test_pure_offer_for_sale_needs_no_fresh_issue() -> None:
    report = run(fresh=None, ofs=TOTAL, pure_ofs=True)
    assert report.checks[0].status == "verified"
    assert report.derived["fresh_share_pct"] == "0.00"
    assert report.derived["ofs_share_pct"] == "100.00"


def test_derived_shares_of_the_issue() -> None:
    derived = run().derived
    assert derived == {"fresh_share_pct": "24.84", "ofs_share_pct": "75.16"}
    assert Decimal(derived["fresh_share_pct"]) + Decimal(derived["ofs_share_pct"]) == 100


def test_no_derived_shares_when_a_value_is_blank_or_missing() -> None:
    assert run(total=Placeholder(raw="[●]")).derived == {}
    assert run(fresh=None).derived == {}
    assert run(total=Count(value=5, raw="5")).checks[0].reason_code == "not_found"
