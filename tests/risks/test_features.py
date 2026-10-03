"""B2.2a: risk bank, novelty, hedging, numbers (fake bank: tests/fixtures/make_fake_bank.py)."""

from pathlib import Path

import numpy as np
import pytest

from finsight.core.schemas import Risk
from finsight.risks import (
    add_features,
    company_key,
    embed_text,
    hedge_count,
    hedging,
    load_bank,
    novelty,
    risk_numbers,
    risks_config,
    unusualness_label,
)

BANK = Path(__file__).resolve().parents[1] / "fixtures" / "fake_bank.parquet"
DIM = 32


def topic(k: int) -> np.ndarray:
    v = np.zeros((1, DIM), dtype=np.float32)
    v[0, k * 4 : k * 4 + 4] = 1.0
    return v


def test_fixture_is_small() -> None:
    assert BANK.stat().st_size < 200_000


def test_bank_keeps_only_the_reference_years() -> None:
    bank = load_bank(BANK)
    assert "Company J Limited" not in bank.companies  # 2024 rows dropped
    assert len(bank) == 9 + 5 + 1
    assert np.allclose(np.linalg.norm(bank.vectors, axis=1), 1.0, atol=1e-5)
    assert len(load_bank(BANK, years=(2018, 2024))) == len(bank) + 2


def test_company_key_ignores_suffixes() -> None:
    assert company_key("ABC Industries Limited") == company_key("abc industries ltd.")
    assert company_key("XYZ Pvt Ltd") == "xyz"


def test_novelty_counts_distinct_past_companies_above_tau() -> None:
    bank = load_bank(BANK)
    queries = np.vstack([topic(0), topic(1), topic(2), topic(3)])
    debt, customers, cyber, drones = novelty(queries, bank, "New Co Limited", tau=0.9)
    assert debt.novelty == pytest.approx(9 / 9)  # every company has a debt risk: common
    assert customers.novelty == pytest.approx(5 / 9)
    assert cyber.novelty == pytest.approx(1 / 9)
    assert drones.novelty == 0.0  # only a 2024 company had it: outside the reference years
    assert cyber.nearest[0].company == "Company A Limited"
    assert cyber.nearest[0].similarity > 0.9
    assert len({e.company for e in debt.nearest}) == 3  # distinct companies


def test_the_issuer_itself_is_excluded() -> None:
    bank = load_bank(BANK)
    [r] = novelty(topic(2), bank, "COMPANY A LTD", tau=0.9)
    assert r.novelty == 0.0  # A is the only one with a cyber risk, and A is the issuer
    assert all(e.company != "Company A Limited" for e in r.nearest)
    [r] = novelty(topic(0), bank, "Company A Limited", tau=0.9)
    assert r.novelty == pytest.approx(8 / 8)


def test_labels_follow_the_configured_cut_offs() -> None:
    cfg = risks_config()["novelty"]
    lo, hi = cfg["unusual_below"], cfg["common_above"]
    assert unusualness_label(0.05, lo, hi) == "unusual"
    assert unusualness_label(0.7, lo, hi) == "common"
    assert unusualness_label(0.3, lo, hi) == "neutral"
    assert unusualness_label(None, lo, hi) is None
    assert unusualness_label(float("nan"), lo, hi) is None


def test_embed_text_uses_title_and_two_sentences() -> None:
    assert embed_text("Debt", "One. Two. Three.") == "Debt. One. Two."
    assert embed_text("", "One. Two. Three.") == "One. Two."


FACT = (
    "We have incurred losses in the past and may incur losses in future. In Fiscal 2024, we "
    "incurred a net loss of ₹45.20 crore. There can be no assurance that we will become "
    "profitable, which could adversely affect our business."
)


def test_hedges_and_hard_facts() -> None:
    h = hedging(FACT)
    assert h.hedge_count == 4  # may, there can be no assurance (once), could, adversely affect
    assert h.hard_fact
    assert h.flag
    assert h.fact_sentence == "In Fiscal 2024, we incurred a net loss of ₹45.20 crore."
    soft = hedging("Our business may be affected by laws. In Fiscal 2024, rules could change.")
    assert not soft.hard_fact  # a year alone is not a fact with a number; modals skip a sentence
    share = hedging("In Fiscal 2025, 61% of our revenue came from our top customer.")
    assert share.hard_fact
    assert not share.flag  # no hedges
    assert hedge_count("No assurance. There can be no assurance.") == 2


def test_numbers_are_parsed_once_each() -> None:
    nums = risk_numbers("A loss of ₹45.20 crore, then ₹45.20 crore again, and 61% of revenue.")
    assert [n.kind for n in nums] == ["money", "percent"]


def test_add_features_with_and_without_a_bank() -> None:
    risks = [
        Risk(
            rid="r1",
            order=1,
            title="Cyber attacks",
            body="A cyber attack could hurt us.",
            page_start=30,
            page_end=30,
        ),
        Risk(rid="r2", order=2, title="Losses", body=FACT, page_start=31, page_end=31),
    ]
    plain = add_features(risks, "New Co")
    assert plain[0].novelty is None
    assert plain[1].hedging.flag
    assert plain[1].numbers

    class Embed:
        def embed(self, texts: list[str]) -> np.ndarray:
            return np.vstack([topic(2) if "Cyber" in t else topic(0) for t in texts])

    scored = add_features(risks, "New Co", bank=load_bank(BANK), embedder=Embed(), tau=0.9)
    assert scored[0].novelty == pytest.approx(round(1 / 9, 4))
    assert scored[1].novelty == 1.0
    assert scored[0].nearest_examples[0].company == "Company A Limited"
    assert risks[0].novelty is None  # inputs are not changed
