"""Jio Platforms (CC-05b / CC-06): the RHP without a Summary of the Offer Document.

``@local``: needs the stored upload parse (``data/store/docs/doc_72480c2e249eb8da``), which is
not committed. Jio is an excluded IPO (C-ADR-02): it is used only as this end-to-end check, never
for training or thresholds. Price-dependent checks (RF05/06/07/11) wait for the price band
(CC-07), so 7 of the 13 checks are decided from the RHP alone.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from finsight.core.config import project_root
from finsight.core.schemas import Count, Money, ParsedDoc, Percent
from finsight.parse import find_sections
from finsight.redflags import detect_severe, evaluate, inputs_from_summary
from finsight.summary import extract_summary
from finsight.summary.sod import build_sod

pytestmark = pytest.mark.local
JIO = project_root() / "data" / "store" / "docs" / "doc_72480c2e249eb8da"
OFFER_FIELDS = ("offer_price", "fresh_issue_size", "ofs_amount", "ofs_shares", "price_band")


@pytest.fixture(scope="module")
def jio() -> tuple[ParsedDoc, list, object]:  # type: ignore[type-arg]
    if not (JIO / "parsed.json").exists():
        pytest.skip("the Jio upload parse is not on this machine")
    doc = ParsedDoc.model_validate_json(Path(JIO / "parsed.json").read_bytes())
    sections = find_sections(doc)
    return doc, sections, extract_summary(doc, sections, JIO.name)


def _flags(doc, sections, summary):  # type: ignore[no-untyped-def]
    from finsight.extract.fields import load_fields
    from finsight.extract.rules import RulesExtractor
    from finsight.extract.xray import DocInputs, build_xray

    fields, rules = load_fields(), RulesExtractor()
    cands = {f.id: rules.extract(doc, sections, [], f) for f in fields if f.id in OFFER_FIELDS}
    xray = build_xray("jio", "jio", {"rhp": DocInputs(candidates=cands)}, datetime.now(UTC),
                      fields=fields)  # fmt: skip
    return {f.id: f for f in evaluate(inputs_from_summary(summary, xray)).flags}


def test_jio_decides_seven_of_thirteen_checks_from_the_rhp(jio) -> None:  # type: ignore[no-untyped-def]
    doc, sections, summary = jio
    flags = _flags(doc, sections, summary)
    decided = {k: f.status for k, f in flags.items() if f.status != "not_available"}
    assert decided == {
        "RF01": "ok", "RF02": "ok", "RF03": "ok", "RF04": "ok", "RF08": "watch",
        "RF12": "ok", "RF13": "ok",
    }  # fmt: skip
    assert "counted from" in flags["RF08"].sentence


def test_jio_p40_covenant_is_no_longer_a_serious_finding(jio) -> None:  # type: ignore[no-untyped-def]
    doc, sections, _ = jio
    found = {o.id: o.evidence.page for o in detect_severe(doc, sections, JIO.name)}
    assert "default_or_recall" not in found
    assert found == {"regulator_order": 472}  # left for the C-ADR-26 rule (CC-07)


def test_jio_sod_result(jio) -> None:  # type: ignore[no-untyped-def]
    doc, sections, summary = jio
    sod = build_sod(doc, sections, summary, JIO.name)
    assert sod.has_sod is False
    assert sod.source["litigation"] == "fallback:outstanding_litigation"
    f = sod.fields()
    assert isinstance(f["profit_after_tax:latest"].value, Money)
    eps = f["eps_basic:latest"].value
    diluted = f["eps_diluted:latest"].value
    assert isinstance(eps, Money)
    assert eps.value_inr == Decimal("33.63")
    assert isinstance(diluted, Money)
    assert diluted.value_inr == Decimal("33.59")
    pre = sod.promoter_holding_pre
    assert pre is not None
    assert isinstance(pre.value, Percent)
    assert pre.value.value == Decimal("66.43")
    assert isinstance(f["criminal_cases"].value, Count)
    ratios = {(r.key, r.period): r for r in sod.derived}
    assert ratios[("debt_to_equity", "latest")].value == Decimal("0.21")
    assert ratios[("revenue_growth_yoy", "latest")].value == Decimal("14.56")
    assert [s.page for s in sod.strengths] == [206, 208, 210, 211, 213, 214]
    assert sod.price_band is None
