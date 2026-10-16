"""E14 scorer (``scripts/summary_eval.py``): matching rules, row scoring and the C-ADR-02 gates."""

from __future__ import annotations

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from finsight.core.config import project_root
from finsight.core.schemas import (
    Count,
    FinancialSummary,
    Money,
    PageEvidence,
    Peer,
    Percent,
    SummaryValue,
)

SPEC = importlib.util.spec_from_file_location(
    "summary_eval", project_root() / "scripts" / "summary_eval.py"
)
assert SPEC is not None
assert SPEC.loader is not None
ev = importlib.util.module_from_spec(SPEC)
sys.modules["summary_eval"] = ev  # its dataclass looks its module up here
SPEC.loader.exec_module(ev)

DOC = "ather-energy-2025"


def _money(rupees: str, raw: str) -> Money:
    return Money(value_inr=Decimal(rupees), currency="INR", raw=raw, precision=0)


def _sv(key: str, value: Any, page: int = 30, status: str = "found") -> SummaryValue:
    return SummaryValue(
        key=key, value=value, period="latest", status=status,  # type: ignore[arg-type]
        evidence=PageEvidence(doc_id=DOC, page=page),
    )  # fmt: skip


def _summary() -> FinancialSummary:
    return FinancialSummary(
        doc_id=DOC,
        revenue=[_sv("revenue", _money("17538000000", "17,538"))],
        net_worth=_sv("net_worth", _money("5459000000", "5,459")),
        promoter_holding_post=_sv("promoter_holding_post_pct", None, 28, "placeholder"),
        litigation={
            "criminal_cases": _sv("criminal_cases", Count(value=12, raw="12"), 31),
            "amount_total": _sv("amount_total", _money("102600580000", "102,600.58"), 31),
        },
        pledged_pct=_sv("pledged_promoter_pct", Percent(value=Decimal("3.93"), raw="3.93%")),
        auditor_remarks=[_sv("auditor_remarks", "Emphasis of Matter: we draw attention", 366)],
        peers=[
            Peer(name="Our Company", eps=Decimal(-47), is_issuer=True),
            Peer(name="Hero MotoCorp", pe=Decimal(20)),
            Peer(name="TVS Motors", pe=Decimal("68.2")),
        ],
    )


def _row(key: str, raw: str = "", unit: str = "", status: str = "found", **kw: Any) -> dict:  # type: ignore[type-arg]
    return {
        "ipo_id": DOC, "key": key, "period": kw.get("period", "latest"), "doc": "rhp",
        "value_raw": raw, "unit": unit, "page": kw.get("page"), "status": status,
        "label_source": kw.get("label_source", "claude_chat_prefill+akshat_verified"),
    }  # fmt: skip


@pytest.mark.parametrize(
    ("row", "correct"),
    [
        (_row("revenue", "17,538", "₹ million", page=30), True),
        (_row("revenue", "17,540", "₹ million"), True),  # within 0.5 %: rounding
        (_row("revenue", "18,000", "₹ million"), False),
        (_row("net_worth", "5,459", "₹ in million"), True),
        (_row("promoter_holding_post_pct", status="placeholder"), True),
        (_row("promoter_holding_post_pct", "45.2", "%"), False),
        (_row("criminal_cases_any", "Yes"), True),
        (_row("criminal_cases_any", "12"), True),
        (_row("criminal_cases_any", "No"), False),
        (_row("litigation_amount_total", "102,600.58", "₹ million"), True),
        (_row("pledged_promoter_pct", "3.93", "%"), True),
        (_row("pledged_promoter_pct", "4.0", "%"), False),
        (_row("auditor_remarks", "Emphasis of matter on basis of preparation"), True),
        (_row("auditor_remarks", "None"), False),
        (_row("peer_pe_list", "68.2, 20"), True),
        (_row("peer_pe_list", "20"), True),  # contains: the pipeline may list more peers
        (_row("peer_pe_list", "20; 99.5"), False),
        (_row("peer_pe_list", "Hero 20.0; TVS 68.2 (highest 68.2, lowest 20.0)"), True),
        (_row("criminal_cases_any", "Yes — 12 proceedings by the Company"), True),
        (_row("criminal_cases_any", "Nil", status="stated_zero"), False),  # pipeline has 12
        (_row("pledged_promoter_pct", "0 (Nil)", "%", status="stated_zero"), False),  # has 3.93
        (_row("pledged_promoter_pct", "3.93 (of promoter holding)", "%"), True),
        (
            _row("litigation_amount_total", "Company 1,000.00; Promoter 101,600.58", "₹ million"),
            True,
        ),
        (_row("litigation_amount_total", "Company 1,000.00; Promoter 5.0", "₹ million"), False),
        (_row("issuer_pe", "N.A. (loss-making)", "times"), True),  # no figure on either side
        (_row("waca_promoters", "Negligible", "₹ per share"), True),  # pipeline leaves it out
        (_row("customer_top10_pct", "<0.34 (top 20 borrowers)", "% of loans"), False),
        (_row("issuer_pe", status="placeholder"), True),
        (_row("customer_top10_pct", status="not_found"), True),
        (_row("rpt_total", "125.38", "₹ million"), False),
        (_row("is_financial_company", "No"), True),
    ],
)
def test_score_row(row: dict, correct: bool) -> None:  # type: ignore[type-arg]
    assert ev.score_row(row, _summary())["correct"] is correct


def test_offer_facts_are_out_of_scope_and_pages_compared() -> None:
    assert ev.score_row(_row("offer_price", "321"), _summary())["scope"] == "out_of_scope"
    assert ev.score_row(_row("revenue", "17,538", "₹ million", page=30), _summary())["page_match"]


def test_summarise_counts_nvm_blanks_and_label_sources() -> None:
    rows = [
        ev.score_row(_row("revenue", "17,538", "₹ million"), _summary()),
        ev.score_row(_row("net_worth", "9,999", "₹ million"), _summary()),
        ev.score_row(_row("promoter_holding_post_pct", status="placeholder"), _summary()),
        ev.score_row(_row("offer_price", "321"), _summary()),
    ]
    s = ev.summarise(rows)
    assert (s["n_rows"], s["n_out_of_scope"], s["nvm"], s["n_valued"]) == (3, 1, 0.5, 2)
    assert s["status_accuracy_on_blanks"] == 1.0
    assert s["per_key"]["net_worth"] == {"n": 1, "accuracy": 0.0}
    assert s["label_sources"] == {"claude_chat_prefill+akshat_verified": 3}


def _gold(tmp_path: Path, rows: list[dict]) -> Path:  # type: ignore[type-arg]
    path = tmp_path / "gold.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_test_slice_needs_final_and_verified_rows(tmp_path: Path) -> None:
    gold = _gold(tmp_path, [_row("revenue", "1", label_source="claude_chat_prefill")])
    with pytest.raises(SystemExit):
        ev.main(["--slice", "test", "--gold", str(gold)])
    with pytest.raises(SystemExit):
        ev.main(["--slice", "all", "--final", "--allow-unverified", "--gold", str(gold)])
    with pytest.raises(SystemExit):  # dev, but unverified without the draft flag
        ev.main(["--slice", "dev", "--gold", str(gold)])


def test_dev_draft_run_writes_a_labelled_draft(tmp_path: Path) -> None:
    gold = _gold(tmp_path, [_row("revenue", "1", "₹ million", label_source="claude_chat_prefill")])
    out = tmp_path / "e14.json"
    args = ["--slice", "dev", "--allow-unverified", "--gold", str(gold)]
    assert ev.main([*args, "--processed", str(tmp_path), "--out", str(out)]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert (result["draft"], result["final"], result["slice"]) == (True, False, "dev")
    assert result["rows"][0]["doc_used"] == "missing"
    assert result["summary"]["nvm"] == 0.0
