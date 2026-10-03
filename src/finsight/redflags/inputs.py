"""The numbers the 13 checks read, from either source they come from.

- ``inputs_from_summary``: the pipeline path, from ``summary.json`` (B1.3) and the X-Ray's offer
  facts (price, fresh issue, OFS amount).
- ``inputs_from_gold``: the gold path, from ``data/gold/gold_v3_summary.jsonl`` rows (B04), so the
  red-flag status gold is computed by the same rules the pipeline uses.

Money keeps its raw text and scale word (sentences show units as written); percentages and ratios
are decimals. ``None`` always means "not found", never zero.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, Field

from finsight.compare import issuer_pe, peer_median_pe
from finsight.core.schemas import FinancialSummary, Money, PageEvidence, Percent, SummaryValue, XRay
from finsight.normalize import parse_amount

AuditorKind = Literal["none", "emphasis", "caro", "qualified"]


class RedFlagInputs(BaseModel):
    """Everything the checks need for one document; yearly lists are latest first."""

    doc_id: str
    revenue: list[Money | None] = Field(default_factory=list)
    profit_after_tax: list[Money | None] = Field(default_factory=list)
    operating_cash_flow: list[Money | None] = Field(default_factory=list)
    total_borrowings: Money | None = None
    net_worth: Money | None = None
    offer_price: Money | None = None
    fresh_amount: Money | None = None
    ofs_amount: Money | None = None
    waca: Money | None = None
    promoter_post_pct: Decimal | None = None
    promoter_identifiable: bool = True
    general_purposes_pct: Decimal | None = None
    criminal_cases: int | None = None  # a count when the document gives one
    criminal_any: bool | None = None  # yes/no when only that is known
    litigation_amount: Money | None = None
    rpt_total: Money | None = None
    customer_top1_pct: Decimal | None = None
    customer_top10_pct: Decimal | None = None
    issuer_pe: Decimal | None = None
    peer_median_pe: Decimal | None = None
    auditor: AuditorKind | None = None
    auditor_short: str = ""
    pledged_pct: Decimal | None = None
    is_financial_company: bool = False
    evidence: dict[str, PageEvidence] = Field(default_factory=dict)


# ------------------------------------------------------------------------- small readers
def _money(value: Any) -> Money | None:
    return value if isinstance(value, Money) and value.value_inr is not None else None


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, Percent):
        return value.value
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        try:
            return Decimal(value.replace(",", "").replace("%", "").strip())
        except InvalidOperation:
            return None
    return None


_QUALIFIED = re.compile(
    r"\bqualified (?:audit )?opinion\b|\badverse opinion\b|\bdisclaimer of opinion\b", re.I
)
_UNQUALIFIED = re.compile(r"\bun-?qualified\b|\bunmodified\b", re.I)
_EMPHASIS = re.compile(r"\bemphasis of matters?\b", re.I)
_CARO = re.compile(r"\bCARO\b|Companies \(Auditor'?s Report\) Order", re.I)
_NONE = re.compile(r"^\s*(none|nil|no remarks?|not applicable|-)\s*\.?\s*$", re.I)


def auditor_kind(text: str) -> AuditorKind:
    """Classify an auditor remark: qualified opinion > emphasis of matter > CARO remark > none."""
    if not text.strip() or _NONE.match(text):
        return "none"
    if _QUALIFIED.search(text) and not _UNQUALIFIED.search(text):
        return "qualified"
    if _EMPHASIS.search(text):
        return "emphasis"
    if _CARO.search(text):
        return "caro"
    return "none"


def _short(text: str, words: int = 18) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def _yes_no(text: str) -> bool | None:
    t = text.strip().lower()
    if t in {"yes", "y", "true"}:
        return True
    if t in {"no", "n", "false", "nil", "none"}:
        return False
    return None


# ------------------------------------------------------------------------- gold v3 rows
_YEARS = {"latest": 0, "latest-1": 1, "latest-2": 2}


def _gold_amount(row: Mapping[str, Any]) -> Any:
    raw = str(row.get("value_raw") or "").strip()
    if not raw or row.get("status") in {"not_found", "placeholder"}:
        return None
    unit = str(row.get("unit") or "").strip()
    if unit == "%":
        return _decimal(raw)
    if unit:
        header = (
            unit if unit.lower().startswith("₹ in") else f"₹ in {unit.replace('₹', '').strip()}"
        )
        return (
            parse_amount(raw, header)
            if unit.lower() not in {"₹", "rs", "inr"}
            else parse_amount(f"₹ {raw}")
        )
    return parse_amount(raw) or _decimal(raw)


def inputs_from_gold(
    doc_id: str, rows: Iterable[Mapping[str, Any]], doc_ids: Mapping[str, str] | None = None
) -> RedFlagInputs:
    """Inputs from the gold v3 rows of one IPO (keys as in ``gold_v3_template.jsonl``).

    ``doc_ids`` maps a row's ``doc`` ("rhp", "prospectus") to that document's ``doc_id`` for the
    evidence; without it every page points at ``doc_id``.
    """
    data: dict[str, Any] = {"doc_id": doc_id, "evidence": {}}
    yearly: dict[str, list[Money | None]] = {
        k: [None, None, None] for k in ("revenue", "profit_after_tax", "operating_cash_flow")
    }
    peers: list[Decimal] = []
    for row in rows:
        key, raw = str(row["key"]), str(row.get("value_raw") or "").strip()
        value = _gold_amount(row)
        if row.get("page"):
            data["evidence"][key] = PageEvidence(
                doc_id=(doc_ids or {}).get(str(row.get("doc")), doc_id),
                page=int(row["page"]),
                sentence=row.get("quote") or None,
            )
        if key in yearly and str(row.get("period")) in _YEARS:
            yearly[key][_YEARS[str(row["period"])]] = _money(value)
        elif key in {"total_borrowings", "net_worth", "offer_price", "rpt_total"}:
            data[key] = _money(value)
        elif key == "fresh_issue_amount":
            data["fresh_amount"] = _money(value)
        elif key == "ofs_amount":
            data["ofs_amount"] = _money(value)
        elif key == "waca_selling_shareholders":
            data["waca"] = _money(value) or (
                parse_amount(f"₹ {raw}") if raw and _decimal(raw) is not None else None
            )
        elif key == "promoter_holding_post_pct":
            if raw.lower() in {"no identifiable promoter", "none", "professionally managed"}:
                data["promoter_identifiable"] = False
            else:
                data["promoter_post_pct"] = _decimal(raw)
        elif key == "general_purposes_pct_of_fresh":
            data["general_purposes_pct"] = _decimal(raw)
        elif key == "criminal_cases_any":
            if raw.isdigit():
                data["criminal_cases"] = int(raw)
            else:
                data["criminal_any"] = _yes_no(raw)
        elif key == "litigation_amount_total":
            data["litigation_amount"] = _money(value)
        elif key == "customer_top1_pct":
            data["customer_top1_pct"] = _decimal(raw)
        elif key == "customer_top10_pct":
            data["customer_top10_pct"] = _decimal(raw)
        elif key == "peer_pe_list":
            peers = [d for part in re.split(r"[;,]\s*", raw) if (d := _decimal(part)) is not None]
        elif key == "issuer_pe":
            data["issuer_pe"] = _decimal(raw)
        elif key == "auditor_remarks":
            data["auditor"] = auditor_kind(raw) if raw else None
            data["auditor_short"] = _short(raw)
        elif key == "pledged_promoter_pct":
            data["pledged_pct"] = _decimal(raw)
        elif key == "is_financial_company":
            data["is_financial_company"] = bool(_yes_no(raw))
    for key, values in yearly.items():
        data[key] = values if any(values) else []
    if peers:
        data["peer_median_pe"] = Decimal(statistics.median(peers))
    return RedFlagInputs(**data)


# ------------------------------------------------------------------------- pipeline
def _value(sv: SummaryValue | None) -> Any:
    return sv.value if sv is not None and sv.status == "found" else None


def _offer_value(
    xray: XRay | None, field_id: str, doc_id: str
) -> tuple[Money | None, PageEvidence | None]:
    if xray is None:
        return None, None
    for field in xray.fields:
        if field.field_id == field_id and field.chosen is not None:
            money = _money(field.chosen.value)
            ev = PageEvidence(
                doc_id=doc_id, page=field.chosen.page, bbox=field.chosen.bbox,
                sentence=field.chosen.sentence,
            )  # fmt: skip
            return money, ev if money else None
    return None, None


def inputs_from_summary(summary: FinancialSummary, xray: XRay | None = None) -> RedFlagInputs:
    """Inputs for the ``redflags`` stage from ``summary.json`` and the X-Ray's offer facts."""
    evidence: dict[str, PageEvidence] = {}

    def keep(name: str, sv: SummaryValue | None) -> Any:
        if sv is not None and sv.evidence is not None and sv.status == "found":
            evidence[name] = sv.evidence
        return _value(sv)

    def years(name: str, values: list[SummaryValue]) -> list[Money | None]:
        out = [_money(keep(name if i == 0 else f"{name}_{i}", v)) for i, v in enumerate(values[:3])]
        return out if any(out) else []

    data: dict[str, Any] = {
        "doc_id": summary.doc_id,
        "revenue": years("revenue", summary.revenue),
        "profit_after_tax": years("profit_after_tax", summary.profit_after_tax),
        "operating_cash_flow": years("operating_cash_flow", summary.operating_cash_flow),
        "total_borrowings": _money(keep("total_borrowings", summary.total_borrowings)),
        "net_worth": _money(keep("net_worth", summary.net_worth)),
        "rpt_total": _money(keep("rpt_total", summary.rpt_total)),
        "promoter_post_pct": _decimal(
            keep("promoter_holding_post_pct", summary.promoter_holding_post)
        ),
        "promoter_identifiable": summary.promoter_identifiable,
        "pledged_pct": _decimal(keep("pledged_promoter_pct", summary.pledged_pct)),
        "customer_top1_pct": _decimal(keep("customer_top1_pct", summary.customer_top1_pct)),
        "customer_top10_pct": _decimal(keep("customer_top10_pct", summary.customer_top10_pct)),
        "general_purposes_pct": _decimal(
            keep("general_purposes_pct_of_fresh", summary.general_purposes_pct)
        ),
        "is_financial_company": summary.is_financial_company,
    }
    if summary.waca:
        data["waca"] = _money(keep("waca_selling_shareholders", summary.waca[0]))
    criminal = keep("criminal_cases_any", summary.litigation.get("criminal_cases"))
    if isinstance(criminal, str):
        data["criminal_any"] = _yes_no(criminal)
    elif criminal is not None and hasattr(criminal, "value"):
        data["criminal_cases"] = int(criminal.value)
    data["litigation_amount"] = _money(
        keep("litigation_amount_total", summary.litigation.get("amount_total"))
    )
    remarks = [
        str(v.value)
        for v in summary.auditor_remarks
        if v.status == "found" and isinstance(v.value, str)
    ]
    if summary.auditor_remarks:
        text = " ".join(remarks)
        data["auditor"], data["auditor_short"] = auditor_kind(text), _short(text)
    for name, field_id, key in (
        ("offer_price", "offer_price", "offer_price"),
        ("fresh_amount", "fresh_issue_size", "fresh_issue_amount"),
        ("ofs_amount", "ofs_amount", "ofs_amount"),
    ):
        money, ev = _offer_value(xray, field_id, summary.doc_id)
        data[name] = money
        if ev is not None:
            evidence[key] = ev
    price = data["offer_price"].value_inr if data["offer_price"] else None
    issuer = next((p for p in summary.peers if p.is_issuer), None)
    data["issuer_pe"] = (
        issuer.pe
        if issuer and issuer.pe is not None
        else issuer_pe(price, issuer.eps if issuer else None)
    )
    data["peer_median_pe"] = peer_median_pe(summary.peers)
    return RedFlagInputs(**data, evidence=evidence)
