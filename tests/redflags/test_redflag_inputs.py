"""B1.4a: red-flag inputs from gold v3 rows and from ``summary.json`` + X-Ray; the stage; the
status-gold script. All data here is synthetic (gold v3 is not filled yet)."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from finsight.core.schemas import (
    Candidate,
    FieldResult,
    FinancialSummary,
    Money,
    PageEvidence,
    Peer,
    RedFlags,
    SummaryValue,
    XRay,
)
from finsight.normalize import parse_amount
from finsight.redflags import auditor_kind, build, evaluate, inputs_from_gold, inputs_from_summary
from finsight.storage import LocalStorage, doc_key, get_json, put_json

ROOT = Path(__file__).resolve().parents[2]
DOC = "doc_0123456789abcdef"
SPEC = importlib.util.spec_from_file_location(
    "redflag_status_gold", ROOT / "scripts" / "redflag_status_gold.py"
)
assert SPEC is not None
assert SPEC.loader is not None
script = importlib.util.module_from_spec(SPEC)
sys.modules["redflag_status_gold"] = script
SPEC.loader.exec_module(script)


def row(key: str, value: str, unit: str = "", period: str = "latest", **kw: Any) -> dict[str, Any]:
    base = {
        "ipo_id": "acme-2025",
        "key": key,
        "period": period,
        "doc": "rhp",
        "value_raw": value,
        "unit": unit,
        "page": None,
        "quote": "",
        "status": "found",
        "label_source": "claude_chat_prefill+akshat_verified",
    }
    return {**base, **kw}


GOLD = [
    row("revenue", "1,000.0", "₹ million"),
    row("revenue", "800.0", "₹ million", "latest-1"),
    row("revenue", "600.0", "₹ million", "latest-2"),
    row("profit_after_tax", "(120.5)", "₹ million", page=210, quote="Loss for the year (120.5)"),
    row("profit_after_tax", "(80.0)", "₹ million", "latest-1"),
    row("profit_after_tax", "10.0", "₹ million", "latest-2"),
    row("total_borrowings", "300", "₹ million"),
    row("net_worth", "200", "₹ million"),
    row("offer_price", "321", "₹", "final", doc="prospectus", page=1),
    row("fresh_issue_amount", "2,626.00", "₹ million", "final", doc="prospectus"),
    row("ofs_amount", "", "", "final", status="not_found"),
    row("waca_selling_shareholders", "10.70", "₹", "final"),
    row("promoter_holding_post_pct", "38.2", "%", "final"),
    row("general_purposes_pct_of_fresh", "[●]", "", "final", status="placeholder"),
    row("criminal_cases_any", "yes"),
    row("peer_pe_list", "45.6; 30.0; 20.1", "", "final"),
    row("issuer_pe", "60", "", "final"),
    row("auditor_remarks", "Emphasis of Matter on the recoverability of deferred tax assets"),
    row("pledged_promoter_pct", "0", "%", "final"),
    row("is_financial_company", "no", "", "final"),
]


def test_gold_rows_become_inputs_with_units_and_evidence() -> None:
    x = inputs_from_gold(DOC, GOLD, {"rhp": DOC, "prospectus": "doc_fedcba9876543210"})
    assert [m.value_inr if m else None for m in x.profit_after_tax] == [
        Decimal("-120500000.0"),
        Decimal("-80000000.0"),
        Decimal("10000000.0"),
    ]
    assert x.offer_price is not None
    assert x.offer_price.value_inr == Decimal("321")
    assert x.waca is not None
    assert x.waca.raw.endswith("10.70")
    assert x.ofs_amount is None  # not_found stays None, never 0
    assert x.general_purposes_pct is None  # a [●] placeholder is not a number
    assert (x.promoter_post_pct, x.criminal_any, x.criminal_cases) == (Decimal("38.2"), True, None)
    assert x.peer_median_pe == Decimal("30.0")
    assert (x.auditor, x.pledged_pct, x.is_financial_company) == ("emphasis", Decimal("0"), False)
    assert x.evidence["profit_after_tax"] == PageEvidence(
        doc_id=DOC, page=210, sentence="Loss for the year (120.5)"
    )
    assert x.evidence["offer_price"].doc_id == "doc_fedcba9876543210"


def test_gold_inputs_through_the_rules() -> None:
    by_id = {f.id: f for f in evaluate(inputs_from_gold(DOC, GOLD)).flags}
    assert by_id["RF01"].status == "watch"  # loss in the latest year only
    assert by_id["RF01"].sentence == "Made a loss of ₹120.5 million in the latest year."
    assert by_id["RF03"].status == "watch"  # 1.5x
    assert by_id["RF04"].status == "ok"  # all fresh issue
    assert by_id["RF05"].status == "concern"  # 321 / 10.70 = 30x
    assert by_id["RF06"].status == "watch"
    assert by_id["RF07"].status == "not_available"
    assert by_id["RF08"].status == "watch"
    assert by_id["RF11"].status == "not_applicable"  # loss-making
    assert by_id["RF12"].status == "watch"
    assert by_id["RF13"].status == "ok"


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("", "none"),
        ("Nil", "none"),
        ("The auditor has issued an unmodified opinion.", "none"),
        ("Qualified opinion: inventories could not be verified", "qualified"),
        ("Emphasis of Matter regarding going concern", "emphasis"),
        ("Remarks under Companies (Auditor's Report) Order, 2020", "caro"),
        ("an unqualified opinion with an emphasis of matter", "emphasis"),
    ],
)
def test_auditor_kind(text: str, kind: str) -> None:
    assert auditor_kind(text) == kind


def _money(text: str, unit: str = "₹ in million") -> Money:
    value = parse_amount(text, unit)
    assert isinstance(value, Money)
    return value


def _sv(key: str, value: Any, page: int = 5) -> SummaryValue:
    return SummaryValue(
        key=key, value=value, status="found", evidence=PageEvidence(doc_id=DOC, page=page)
    )


def _xray() -> XRay:
    price = parse_amount("₹ 321")
    cand = Candidate(
        field_id="offer_price",
        extractor="rules",
        doc_type="prospectus",
        raw="₹321",
        value=price,
        page=1,
        score=1.0,
    )
    field = FieldResult(
        field_id="offer_price",
        chosen=cand,
        candidates=[cand],
        verdict="verified",
        reason_code="verified",
        reason="",
        checks=[],
    )
    return XRay(ipo_id=DOC, company="Acme", built_at=datetime.now(UTC), fields=[field], derived={})


def test_summary_and_xray_become_inputs_and_the_stage_writes_redflags(tmp_path: Path) -> None:
    summary = FinancialSummary(
        doc_id=DOC,
        profit_after_tax=[_sv("profit_after_tax", _money("15.0"), 200)],
        revenue=[_sv("revenue", _money("100.0"))],
        rpt_total=_sv("rpt_total", _money("30.0")),
        pledged_pct=_sv("pledged_pct", parse_amount("12%")),
        litigation={"criminal_cases": _sv("criminal_cases", parse_amount("3"))},
        peers=[
            Peer(name="Acme", eps=Decimal("10"), is_issuer=True),
            Peer(name="Beta", pe=Decimal("20")),
        ],
        auditor_remarks=[_sv("auditor_remarks", "Qualified opinion on inventory")],
    )
    x = inputs_from_summary(summary, _xray())
    assert x.issuer_pe == Decimal("32.1")  # 321 / EPS 10, the compare package's rule
    assert x.peer_median_pe == Decimal("20")
    assert (x.criminal_cases, x.auditor) == (3, "qualified")
    assert x.evidence["offer_price"].page == 1

    storage = LocalStorage(tmp_path)
    put_json(storage, doc_key(DOC, "summary.json"), summary.model_dump(mode="json"))
    put_json(storage, doc_key(DOC, "xray.json"), _xray().model_dump(mode="json"))
    flags = build(storage, DOC)
    saved = RedFlags.model_validate(get_json(storage, doc_key(DOC, "redflags.json")))
    assert saved == flags
    by_id = {f.id: f for f in saved.flags}
    assert [by_id[i].status for i in ("RF08", "RF09", "RF11", "RF12", "RF13")] == [
        "watch",
        "concern",
        "watch",
        "concern",
        "concern",
    ]
    assert by_id["RF09"].evidence == [
        PageEvidence(doc_id=DOC, page=5),
        PageEvidence(doc_id=DOC, page=5),
    ]


def test_status_gold_script_refuses_unverified_rows_unless_asked(tmp_path: Path) -> None:
    gold, out = tmp_path / "gold.jsonl", tmp_path / "status.jsonl"
    rows = [*GOLD[:-1], {**GOLD[-1], "label_source": "claude_chat_prefill"}]
    gold.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert script.main(["--gold", str(gold), "--out", str(out)]) == 1
    assert not out.exists()
    assert script.main(["--gold", str(gold), "--out", str(out), "--allow-unverified"]) == 0
    written = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["rf"] for r in written] == [f"RF{i:02d}" for i in range(1, 14)]
    assert {r["label_source"] for r in written} == {"computed_from_gold_v3_unverified_draft"}
    assert next(r for r in written if r["rf"] == "RF05")["status"] == "concern"


def test_status_gold_script_without_gold_v3(tmp_path: Path) -> None:
    assert script.main(["--gold", str(tmp_path / "missing.jsonl")]) == 1


def test_every_showcase_ipo_has_doc_ids_for_the_evidence() -> None:
    docs = script.doc_ids_by_ipo()
    assert len(docs) == 10
    assert all(ids.get("rhp", "").startswith("doc_") for ids in docs.values())
