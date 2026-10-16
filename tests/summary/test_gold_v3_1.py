"""Gold v3.1 (C-ADR-20): the row fixes and the v3.1 scoring convention."""

from __future__ import annotations

import importlib.util
import sys
from typing import Any

from finsight.core.config import project_root
from finsight.core.schemas import FinancialSummary, PageEvidence, SummaryValue


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, project_root() / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mk = _load("make_gold_v3_1")
ev = _load("summary_eval")


def _row(ipo: str, key: str, **kw: Any) -> dict[str, Any]:
    base = {
        "ipo_id": ipo, "key": key, "period": "latest", "status": "found", "value_raw": "x",
        "page": 3, "label_source": "claude_chat_prefill+akshat_verified", "notes": "n",
    }  # fmt: skip
    return base | kw


def test_unrelated_rows_are_returned_unchanged() -> None:
    rows = [_row("groww-2025", "revenue"), _row("ather-energy-2025", "net_worth")]
    new, changes = mk.build(rows)
    assert new == rows
    assert changes == []


def test_promoter_post_pct_is_filled_from_the_prospectus_and_marked() -> None:
    row = _row("hdb-financial-services-2025", "promoter_holding_post_pct", status="not_found")
    row |= {"value_raw": "", "page": None}
    (new,), _ = mk.build([row])
    assert (new["status"], new["value_raw"], new["page"]) == ("found", "73.98", 21)
    assert new["label_source"] == "claude_code_fix"
    assert new["needs_akshat_verify"] is True
    assert "73.98" in new["quote"]


def test_a_summed_promoter_share_is_flagged_computed() -> None:
    row = _row("urban-company-2025", "promoter_holding_post_pct", status="not_found")
    (new,), _ = mk.build([row])
    assert new["computed"] is True
    assert new["value_raw"].startswith("19.35")


def test_physicswallah_auditor_value_drops_the_emphasis_of_matter() -> None:
    row = _row(
        "physicswallah-2025", "auditor_remarks", value_raw="Qualifications x; emphasis of matter y"
    )
    (new,), _ = mk.build([row])
    assert "emphasis" not in new["value_raw"].lower()
    assert "Emphasis of Matter" in new["notes"]
    assert "akshat_verified" in new["label_source"]  # the original label is kept
    assert new["label_source"].endswith("claude_code_fix")


def test_a_notes_only_change_keeps_the_value() -> None:
    row = _row("ather-energy-2025", "auditor_remarks", value_raw="No qualifications")
    (new,), changes = mk.build([row])
    assert new["value_raw"] == "No qualifications"
    assert "Emphasis of Matter" in new["notes"]
    assert changes[0]["new"]["needs_akshat_verify"] is True


def test_hexaware_issuer_pe_is_flagged_computed_with_the_value_kept() -> None:
    row = _row("hexaware-technologies-2025", "issuer_pe", value_raw="43.04 (computed)")
    (new,), _ = mk.build([row])
    assert new["computed"] is True
    assert new["value_raw"] == "43.04 (computed)"


def _auditor_summary(*texts: str) -> FinancialSummary:
    vals = [
        SummaryValue(
            key="auditor_remarks", value=t, period="latest", status="found",
            evidence=PageEvidence(doc_id="d", page=31),
        )
        for t in texts
    ]  # fmt: skip
    return FinancialSummary(doc_id="d", auditor_remarks=vals)


NO_QUAL = "The Statutory Auditors have not made any qualifications in their examination report."
EOM = "Emphasis of Matter: we draw attention to Note 1.2 on the basis of preparation."
CARO = "Qualifications by the respective auditors in the CARO reports: clause (vii) delays."


def test_v31_no_qualification_is_correct_even_with_an_emphasis_of_matter() -> None:
    row = _row("a", "auditor_remarks", value_raw="No qualifications")
    s = _auditor_summary(NO_QUAL, EOM)
    assert ev.score_row(row, s, "v3.1")["correct"] is True
    assert ev.score_row(row, s, "v3")["correct"] is False  # v3 scoring is unchanged


def test_v31_a_caro_qualification_is_not_no_qualification() -> None:
    row = _row("a", "auditor_remarks", value_raw="No qualifications")
    assert ev.score_row(row, _auditor_summary(NO_QUAL, CARO), "v3.1")["correct"] is False


def test_v31_qualified_gold_needs_a_qualification() -> None:
    row = _row("a", "auditor_remarks", value_raw="Qualifications in the audit reports and CARO")
    assert ev.score_row(row, _auditor_summary(CARO), "v3.1")["correct"] is True
    assert ev.score_row(row, _auditor_summary(NO_QUAL, EOM), "v3.1")["correct"] is False


def test_pending_rows_pass_the_verification_gate_only_with_the_flag() -> None:
    row = _row("a", "revenue", label_source="claude_code_fix", needs_akshat_verify=True)
    assert ev.unverified([row]) == ["a:revenue:latest"]
    assert ev.unverified([row], pending_ok=True) == []
    out = ev.score_row(row, None, "v3.1")
    assert out["pending_verify"] is True
