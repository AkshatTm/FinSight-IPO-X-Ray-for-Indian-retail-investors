from decimal import Decimal

import pytest

from finsight.core.schemas import Hedging, Risk
from finsight.risks.numbers import risk_numbers
from finsight.risks.seriousness import (
    importance,
    ranked_rids,
    score_risks,
    seriousness,
    seriousness_score,
)


def risk(rid: str = "r", order: int = 1, text: str = "", **kw: object) -> Risk:
    base: dict[str, object] = dict(
        rid=rid,
        order=order,
        title="T",
        body=text or "Body.",
        page_start=1,
        page_end=1,
        numbers=risk_numbers(text),
    )
    return Risk.model_validate({**base, **kw})


@pytest.mark.parametrize(
    ("kw", "text", "score", "level"),
    [
        ({"category": "debt_liquidity"}, "", 2, "medium"),
        ({"category": "debt_liquidity", "hedging": Hedging(hard_fact=True)}, "", 3, "high"),
        ({"category": "competition"}, "", 0, "low"),
        ({"category": "customers_suppliers"}, "Top customer gave 61% of revenue.", 2, "medium"),
        ({"category": "customers_suppliers"}, "Top customer gave 6% of revenue.", 1, "low"),
        ({"category": "financial", "novelty": 0.9}, "", 1, "low"),  # boilerplate
        ({"category": None}, "", 1, "low"),
        (
            {"category": "legal_litigation", "hedging": Hedging(hard_fact=True), "novelty": 0.05},
            "Claims of 25% of net worth.",
            4,
            "high",
        ),
    ],
)
def test_seriousness_rule_table(kw: dict[str, object], text: str, score: int, level: str) -> None:
    r = risk(text=text, **kw)
    assert seriousness_score(r) == score
    assert seriousness(score) == level


def test_money_is_material_only_against_a_known_reference() -> None:
    r = risk(text="A penalty of ₹50 crore was imposed.", category="regulatory")
    assert seriousness_score(r) == 1
    assert seriousness_score(r, reference_inr=Decimal("4000000000")) == 2  # 50 cr >= 10% of 400 cr
    assert seriousness_score(r, reference_inr=Decimal("40000000000")) == 1


def test_importance_and_ranking() -> None:
    assert importance("high", 0.0) == 3.0
    assert importance("high", 0.9) == pytest.approx(0.3)
    assert importance("low", None) == 0.5  # unknown novelty counts as 0.5
    scored = score_risks(
        [
            risk("a", 1, category="competition", novelty=0.1),
            risk("b", 2, category="debt_liquidity", novelty=0.5, hedging=Hedging(hard_fact=True)),
            risk("c", 3, category="debt_liquidity", novelty=0.5, hedging=Hedging(hard_fact=True)),
        ]
    )
    assert [r.seriousness for r in scored] == ["low", "high", "high"]
    assert ranked_rids(scored) == ["b", "c", "a"]  # ties keep document order
