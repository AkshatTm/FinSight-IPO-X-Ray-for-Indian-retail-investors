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
from finsight.core.schemas import (
    SUMMARY_HAS_VALUE,
    FinancialSummary,
    Money,
    PageEvidence,
    Percent,
    SummaryValue,
    XRay,
)
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
    fresh_blank: bool = False  # the document prints [●] for it: unknown, never zero
    ofs_blank: bool = False
    waca: Money | None = None  # promoters only, share-weighted (C-ADR-16)
    waca_selling: Money | None = None  # selling shareholders, shown beside it, not used
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
    """Yes/no from the first word, so "Yes — 9 criminal proceedings" and "No (Nil ...)" work."""
    t = re.split(r"[\s(—–:,;]+", text.strip().lower(), maxsplit=1)[0]
    if t in {"yes", "y", "true"}:
        return True
    if t in {"no", "n", "false", "nil", "none"}:
        return False
    return None


# ------------------------------------------------------------------------- gold v3 rows
_YEARS = {"latest": 0, "latest-1": 1, "latest-2": 2}


_LEAD_NUMBER = re.compile(r"^\s*[<>~≈]?\s*(-?\d[\d,]*(?:\.\d+)?)(?=\s|\(|;|$)")
_REMARK = re.compile(r"\s+\((?=[^)]*[A-Za-z]{2})[^)]*\)\s*$")  # not "(120.5)", a negative
_NUMERIC_KEYS = frozenset(
    {
        "promoter_holding_post_pct", "general_purposes_pct_of_fresh", "customer_top1_pct",
        "customer_top10_pct", "issuer_pe", "pledged_promoter_pct",
    }
)  # fmt: skip


def gold_number(raw: str) -> Decimal | None:
    """A plain number, or the leading one of an annotated value such as ``"0 (Nil)"``.

    ``"N.A. (no fresh issue)"`` and other words give ``None``; a leading ``<`` is dropped.
    """
    plain = _decimal(raw)
    if plain is not None:
        return plain
    match = _LEAD_NUMBER.match(raw)
    return _decimal(match.group(1)) if match else None


_PE_TAIL = re.compile(r"\(?\s*(?:highest|industry average|average)\b", re.IGNORECASE)
_PE_NUMBER = re.compile(r"(?<![\d.])\d[\d,]*\.\d+")


def gold_peer_pes(raw: str) -> list[Decimal]:
    """Per-peer P/E values from ``"Name 24.88; Name 19.80 (highest 24.88, ...)"``.

    The "(highest ..., average ...)" tail is cut off; a list with no per-peer figures gives ``[]``.
    """
    head = _PE_TAIL.split(raw, maxsplit=1)[0]
    if re.fullmatch(r"[\d.,;\s]+", head):  # a bare list "68.2, 20"
        values = [_decimal(p) for p in re.split(r"[;,]\s*", head.strip()) if p.strip()]
    else:  # names may carry digits ("360 One WAM 26.85"), so only decimals count
        values = [_decimal(m.group(0)) for m in _PE_NUMBER.finditer(head)]
    return [v for v in values if v is not None]


_SCALE_WORD = re.compile(r"\b(?:thousand|lakh|lac|million|mn|crore|cr|billion|bn)\b", re.IGNORECASE)
_MULTI_PART_AMOUNTS = frozenset({"litigation_amount_total", "rpt_total"})
_FOREIGN = re.compile(
    r"(?:USD|EUR|US\$|\$|€)\s*\d[\d,]*(?:\.\d+)?(?:\s*(?:million|billion))?", re.IGNORECASE
)
_AMOUNT = re.compile(r"(?<![\d.])\d[\d,]*(?:\.\d+)?")


def gold_amount_parts(raw: str) -> list[Decimal]:
    """Every rupee amount printed in a by-party text such as ``"Company: 1,011.7 and 179.0"``.

    Parenthetical remarks and foreign-currency claims (USD, EUR) are left out.
    """
    text = _FOREIGN.sub(" ", re.sub(r"\([^)]*\)", " ", raw))
    values = [_decimal(m.group(0)) for m in _AMOUNT.finditer(text)]
    return [v for v in values if v is not None]


def _zero_money(raw: str) -> Money:
    return Money(value_inr=Decimal(0), currency="INR", raw=raw or "0", precision=0)


def _gold_amount(row: Mapping[str, Any]) -> Any:
    raw = str(row.get("value_raw") or "").strip()
    unit = _REMARK.sub("", str(row.get("unit") or "").strip())  # "₹ million (plus USD claims)"
    if row.get("status") == "stated_zero":  # an explicit Nil / "-" / N.A.: the value is 0
        return Decimal(0) if unit == "%" else _zero_money(raw)
    if not raw or row.get("status") in {"not_found", "placeholder"}:
        return None
    raw = _REMARK.sub("", raw)  # "5,882.43 (income-tax demand)" -> "5,882.43"
    if row.get("key") in _MULTI_PART_AMOUNTS and re.search(r"[A-Za-z]{3}", raw):
        parts = gold_amount_parts(raw)
        if parts:  # "Against Company 1,391.41; against Directors 0.50": no printed total, so sum
            raw = f"{sum(parts):.2f}"
    if unit.startswith("%"):
        return gold_number(raw)
    try:
        if _SCALE_WORD.search(unit):  # "₹ million", "₹ in crore"
            header = (
                unit if unit.lower().startswith("₹ in") else f"₹ in {unit.replace('₹', '').strip()}"
            )
            return parse_amount(raw, header)
        if unit:  # "₹", "₹ per share": rupees as printed
            return parse_amount(f"₹ {raw}")
        return parse_amount(raw) or _decimal(raw)
    except ValueError:  # text that is not an amount ("Negligible")
        return None


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
        if row.get("status") == "stated_zero":
            if key == "criminal_cases_any":
                raw = "No"
            elif key == "auditor_remarks":
                raw = "None"
            elif key in _NUMERIC_KEYS or key.startswith("waca_"):
                raw = "0"
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
            data["waca_selling"] = _money(value) or (
                parse_amount(f"₹ {raw}") if raw and _decimal(raw) is not None else None
            )
        elif key == "waca_promoters":
            data["waca"] = _money(value) or (
                parse_amount(f"₹ {raw}") if raw and _decimal(raw) is not None else None
            )
        elif key == "promoter_holding_post_pct":
            if raw.lower() in {"no identifiable promoter", "none", "professionally managed"}:
                data["promoter_identifiable"] = False
            else:
                data["promoter_post_pct"] = gold_number(raw)
        elif key == "general_purposes_pct_of_fresh":
            data["general_purposes_pct"] = gold_number(raw)
        elif key == "criminal_cases_any":
            if raw.isdigit():
                data["criminal_cases"] = int(raw)
            else:
                data["criminal_any"] = _yes_no(raw)
        elif key == "litigation_amount_total":
            data["litigation_amount"] = _money(value)
        elif key == "customer_top1_pct":
            data["customer_top1_pct"] = gold_number(raw)
        elif key == "customer_top10_pct":
            data["customer_top10_pct"] = gold_number(raw)
        elif key == "peer_pe_list":
            peers = gold_peer_pes(raw)
        elif key == "issuer_pe":
            data["issuer_pe"] = gold_number(raw)
        elif key == "auditor_remarks":
            data["auditor"] = auditor_kind(raw) if raw else None
            data["auditor_short"] = _short(raw)
        elif key == "pledged_promoter_pct":
            data["pledged_pct"] = gold_number(raw)
        elif key == "is_financial_company":
            data["is_financial_company"] = bool(_yes_no(raw))
    for key, values in yearly.items():
        data[key] = values if any(values) else []
    if peers:
        data["peer_median_pe"] = Decimal(statistics.median(peers))
    return RedFlagInputs(**data)


# ------------------------------------------------------------------------- pipeline
def _value(sv: SummaryValue | None) -> Any:
    return sv.value if sv is not None and sv.status in SUMMARY_HAS_VALUE else None


def _offer_value(
    xray: XRay | None, field_id: str, doc_id: str
) -> tuple[Money | None, PageEvidence | None, bool]:
    """A real amount (the Prospectus one when both documents have it) and whether the only
    thing the documents print is a ``[●]`` blank (unknown, never zero)."""
    if xray is None:
        return None, None, False
    for field in xray.fields:
        if field.field_id != field_id:
            continue
        pool = ([field.chosen] if field.chosen else []) + [
            c for c in field.candidates if c is not field.chosen
        ]
        real = [c for c in pool if _money(c.value) is not None]
        real.sort(key=lambda c: c.doc_type != "prospectus")  # Prospectus first, stable
        if real:
            best = real[0]
            ev = PageEvidence(doc_id=doc_id, page=best.page, bbox=best.bbox, sentence=best.sentence)
            return _money(best.value), ev, False
        return None, None, any(c.value is not None and c.value.kind == "placeholder" for c in pool)
    return None, None, False


def inputs_from_summary(summary: FinancialSummary, xray: XRay | None = None) -> RedFlagInputs:
    """Inputs for the ``redflags`` stage from ``summary.json`` and the X-Ray's offer facts."""
    evidence: dict[str, PageEvidence] = {}

    def keep(name: str, sv: SummaryValue | None) -> Any:
        if sv is not None and sv.evidence is not None and sv.status in SUMMARY_HAS_VALUE:
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
    by_key = {v.key: v for v in summary.waca if v.key != "waca_holder"}
    data["waca"] = _money(keep("waca_promoters", by_key.get("waca_promoters")))
    data["waca_selling"] = _money(
        keep("waca_selling_shareholders", by_key.get("waca_selling_shareholders"))
    )
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
        money, ev, blank = _offer_value(xray, field_id, summary.doc_id)
        data[name] = money
        if name != "offer_price":
            data[name.replace("_amount", "_blank")] = blank
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
