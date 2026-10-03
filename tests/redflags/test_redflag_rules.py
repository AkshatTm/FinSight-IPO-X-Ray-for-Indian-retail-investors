"""B1.4a: the 13 red-flag checks at every threshold edge (B01 §5) with B05 §5.4 sentences."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from finsight.core.schemas import Money, PageEvidence
from finsight.guard import find_forbidden
from finsight.normalize import parse_amount
from finsight.redflags import CHECKS, DRAFT_SENTENCES, RedFlagInputs, evaluate, load_config
from finsight.redflags.rules import money, num


def m(text: str, unit: str = "₹ in million") -> Money:
    value = parse_amount(text, unit)
    assert isinstance(value, Money)
    return value


def run(**kw: Any) -> dict[str, tuple[str, str]]:
    flags = evaluate(RedFlagInputs(doc_id="doc_0123456789abcdef", **kw))
    return {f.id: (f.status, f.sentence) for f in flags.flags}


def status(rf: str, **kw: Any) -> str:
    return run(**kw)[rf][0]


def test_all_13_checks_always_come_back_and_empty_inputs_are_not_available() -> None:
    flags = evaluate(RedFlagInputs(doc_id="doc_0123456789abcdef"))
    assert [f.id for f in flags.flags] == [f"RF{i:02d}" for i in range(1, 14)]
    assert flags.thresholds_version == load_config()["version"]
    statuses = {f.id: f.status for f in flags.flags}
    assert set(statuses.values()) == {"not_available"}
    texts = {f.id: f.sentence for f in flags.flags}
    assert texts["RF01"] == "FinSight couldn't find the profit figures."
    assert texts["RF05"] == "Not available until the price is set."
    assert texts["RF10"] == "The document doesn't give customer shares."
    assert texts["RF02"] == "FinSight couldn't find this in the document."
    assert all(f.points == 0 and f.rule for f in flags.flags)


def test_rf01_profit_or_loss() -> None:
    assert run(profit_after_tax=[m("100"), m("90"), m("80")])["RF01"] == (
        "ok",
        "Profitable in each of the last 3 years (latest profit ₹100 million).",
    )
    assert run(profit_after_tax=[m("(12.5)"), m("90"), m("80")])["RF01"] == (
        "watch",
        "Made a loss of ₹12.5 million in the latest year.",
    )
    assert run(profit_after_tax=[m("(12.5)"), m("(9)"), m("(8)")])["RF01"] == (
        "concern",
        "Made a loss in each of the last 3 years (latest loss ₹12.5 million).",
    )
    # A profit now after an earlier loss: OK, drafted sentence (not "each of the last 3 years").
    assert run(profit_after_tax=[m("5"), m("(9)"), m("80")])["RF01"] == (
        "ok",
        DRAFT_SENTENCES["RF01.ok_mixed"].format(pat="5 million"),
    )


def test_rf02_cash_from_the_business() -> None:
    assert status("RF02", operating_cash_flow=[m("10"), m("(1)"), m("5")]) == "ok"
    assert status("RF02", operating_cash_flow=[m("(10)"), m("1"), m("5")]) == "watch"
    assert run(operating_cash_flow=[m("10"), m("(1)"), m("(5)")])["RF02"] == (
        "concern",
        "The business has used more cash than it brought in for 2 of the last 3 years.",
    )


@pytest.mark.parametrize(
    ("debt", "worth", "expected"),
    [
        ("100", "100", "ok"),
        ("100.1", "100", "watch"),
        ("200", "100", "watch"),
        ("200.1", "100", "concern"),
    ],
)
def test_rf03_debt_edges(debt: str, worth: str, expected: str) -> None:
    assert status("RF03", total_borrowings=m(debt), net_worth=m(worth)) == expected


def test_rf03_lenders_and_negative_net_worth() -> None:
    assert run(is_financial_company=True, total_borrowings=m("900"), net_worth=m("100"))[
        "RF03"
    ] == ("not_applicable", "Not applicable: borrowing is a normal part of a lender's business.")
    assert status("RF03", total_borrowings=m("10"), net_worth=m("(5)")) == "not_available"
    assert run(total_borrowings=m("150"), net_worth=m("100"))["RF03"][1] == (
        "Debt is 1.5× its net worth, which is high for a company like this."
    )


@pytest.mark.parametrize(
    ("fresh", "ofs", "expected"),
    [
        ("50", "50", "ok"),
        ("49", "51", "watch"),
        ("20", "80", "watch"),
        ("19", "81", "concern"),
        ("0", "100", "concern"),
    ],
)
def test_rf04_ofs_share_edges(fresh: str, ofs: str, expected: str) -> None:
    assert status("RF04", fresh_amount=m(fresh), ofs_amount=m(ofs)) == expected


def test_rf04_sentences() -> None:
    assert (
        run(fresh_amount=m("75"), ofs_amount=m("25"))["RF04"][1]
        == "75% of the money goes to the company."
    )
    assert run(fresh_amount=m("10"), ofs_amount=m("90"))["RF04"][1] == (
        "90% of the money goes to existing shareholders who are selling, not to the company."
    )


@pytest.mark.parametrize(
    ("waca", "expected"), [("21", "ok"), ("20", "watch"), ("5.25", "watch"), ("5", "concern")]
)
def test_rf05_insider_price_gap_edges(waca: str, expected: str) -> None:
    assert (
        status("RF05", offer_price=parse_amount("₹ 100"), waca=parse_amount(f"₹ {waca}"))
        == expected
    )


def test_rf05_sentence_uses_units_as_written() -> None:
    flag = run(offer_price=parse_amount("₹ 321"), waca=parse_amount("₹ 10.70"))["RF05"]
    assert flag == (
        "concern",
        "Selling shareholders bought their shares at an average of ₹10.70. "
        "The IPO price is ₹321, about 30× more.",
    )


@pytest.mark.parametrize(
    ("p", "expected"), [("40", "ok"), ("39.9", "watch"), ("25", "watch"), ("24.9", "concern")]
)
def test_rf06_promoter_stake_edges(p: str, expected: str) -> None:
    assert status("RF06", promoter_post_pct=Decimal(p)) == expected


def test_rf06_no_identifiable_promoter_is_a_concern() -> None:
    assert run(promoter_identifiable=False)["RF06"] == (
        "concern",
        "This company has no identifiable promoter.",
    )


@pytest.mark.parametrize(
    ("g", "expected"), [("20", "ok"), ("20.1", "watch"), ("29.9", "watch"), ("30", "concern")]
)
def test_rf07_vague_use_edges(g: str, expected: str) -> None:
    assert status("RF07", general_purposes_pct=Decimal(g)) == expected


def test_rf07_pure_ofs_is_not_applicable() -> None:
    assert run(fresh_amount=m("0"), ofs_amount=m("100"), general_purposes_pct=Decimal("25"))[
        "RF07"
    ] == ("not_applicable", "Not applicable: the company receives no money from this IPO.")


def test_rf08_court_cases() -> None:
    worth = m("1,000")
    assert status("RF08", criminal_cases=0, litigation_amount=m("100"), net_worth=worth) == "ok"
    assert run(criminal_cases=2, litigation_amount=m("100"), net_worth=worth)["RF08"] == (
        "watch",
        "There are 2 criminal case(s) involving the company, promoters or directors.",
    )
    assert run(criminal_cases=0, litigation_amount=m("100.1"), net_worth=worth)["RF08"] == (
        "concern",
        "Pending cases involve ₹100.1 million, about 10% of the company's net worth.",
    )
    assert status("RF08", criminal_any=True) == "watch"
    assert (
        status("RF08", criminal_any=False) == "not_available"
    )  # amounts unknown: can't say "small"


@pytest.mark.parametrize(
    ("rpt", "expected"), [("10", "ok"), ("10.1", "watch"), ("25", "watch"), ("25.1", "concern")]
)
def test_rf09_related_party_edges(rpt: str, expected: str) -> None:
    assert status("RF09", rpt_total=m(rpt), revenue=[m("100"), None, None]) == expected


@pytest.mark.parametrize(
    ("t1", "t10", "expected"),
    [
        ("20", "50", "ok"),
        ("20.1", None, "watch"),
        ("5", "50.1", "watch"),
        ("40", "90", "watch"),
        ("40.1", None, "concern"),
    ],
)
def test_rf10_customer_edges(t1: str, t10: str | None, expected: str) -> None:
    kw: dict[str, Any] = {"customer_top1_pct": Decimal(t1)}
    if t10 is not None:
        kw["customer_top10_pct"] = Decimal(t10)
    assert status("RF10", **kw) == expected


def test_rf10_sentence() -> None:
    assert run(customer_top1_pct=Decimal("45"), customer_top10_pct=Decimal("80"))["RF10"][1] == (
        "The top customer brings in 45% of revenue, and the top 10 bring in 80%."
    )


@pytest.mark.parametrize(
    ("pe", "expected"), [("30", "ok"), ("30.1", "watch"), ("50", "watch"), ("50.1", "concern")]
)
def test_rf11_price_vs_peers_edges(pe: str, expected: str) -> None:
    assert status("RF11", issuer_pe=Decimal(pe), peer_median_pe=Decimal("20")) == expected


def test_rf11_loss_making_is_not_applicable() -> None:
    assert run(profit_after_tax=[m("(1)")], issuer_pe=None, peer_median_pe=Decimal("20"))[
        "RF11"
    ] == ("not_applicable", "Not applicable: P/E can't be calculated for a loss-making company.")


def test_rf12_auditor() -> None:
    assert status("RF12", auditor="none") == "ok"
    assert run(auditor="emphasis", auditor_short="recoverability of deferred tax assets")[
        "RF12"
    ] == ("watch", "The auditor drew attention to: recoverability of deferred tax assets.")
    assert status("RF12", auditor="caro") == "watch"
    assert status("RF12", auditor="qualified") == "concern"


@pytest.mark.parametrize(
    ("p", "expected"), [("0", "ok"), ("0.01", "watch"), ("10", "watch"), ("10.1", "concern")]
)
def test_rf13_pledge_edges(p: str, expected: str) -> None:
    assert status("RF13", pledged_pct=Decimal(p)) == expected


def test_points_and_evidence_follow_the_status() -> None:
    ev = PageEvidence(doc_id="doc_0123456789abcdef", page=42)
    flags = evaluate(
        RedFlagInputs(
            doc_id="doc_0123456789abcdef",
            pledged_pct=Decimal("12"),
            promoter_post_pct=Decimal("30"),
            evidence={"pledged_promoter_pct": ev},
        )
    )
    by_id = {f.id: f for f in flags.flags}
    assert (by_id["RF13"].points, by_id["RF13"].evidence) == (2, [ev])
    assert (by_id["RF06"].points, by_id["RF06"].evidence) == (1, [])
    assert by_id["RF13"].numbers_used == {"pct": "12"}


def test_no_sentence_or_rule_text_contains_a_forbidden_phrase() -> None:
    texts = [str(c["rule"]) for c in load_config()["checks"].values()] + list(
        DRAFT_SENTENCES.values()
    )
    rich = RedFlagInputs(
        doc_id="doc_0123456789abcdef",
        profit_after_tax=[m("(1)"), m("(1)"), m("(1)")],
        operating_cash_flow=[m("(1)"), m("(1)"), m("1")],
        total_borrowings=m("300"),
        net_worth=m("100"),
        fresh_amount=m("10"),
        ofs_amount=m("90"),
        offer_price=parse_amount("₹ 500"),
        waca=parse_amount("₹ 5"),
        promoter_post_pct=Decimal("20"),
        general_purposes_pct=Decimal("35"),
        criminal_cases=3,
        litigation_amount=m("50"),
        rpt_total=m("1"),
        revenue=[m("2")],
        customer_top1_pct=Decimal("60"),
        auditor="qualified",
        auditor_short="inventory could not be verified",
        pledged_pct=Decimal("50"),
    )
    texts += [f.sentence for f in evaluate(rich).flags]
    texts += [f.sentence for f in evaluate(RedFlagInputs(doc_id="doc_0123456789abcdef")).flags]
    assert [(t, find_forbidden(t)) for t in texts if find_forbidden(t)] == []
    assert len(CHECKS) == 13


def test_formatting_helpers() -> None:
    assert money(m("(1,23,456.5)", "₹ in lakh")) == "1,23,456.5 lakh"
    assert num(Decimal("2.50"), 2) == "2.5"
    assert num(Decimal("33.35")) == "33.4"
    assert num(Decimal("40")) == "40"
