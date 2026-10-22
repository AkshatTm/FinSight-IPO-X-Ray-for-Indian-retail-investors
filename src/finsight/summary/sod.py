"""``sod.json`` (CC-05b / CC-06): the Summary of the Offer Document as one result per upload.

``build_sod`` gathers what the summary readers found (financials, promoter holding before and
after the offer, litigation, related-party total, auditor remarks), the extra financial rows and
ratios (``derived``) and the issuer's own list of strengths (``strengths``). ``source`` says per
reader where its values came from: ``sod``, ``fallback:<section ids>`` (an RHP without a
Summary, e.g. Jio) or ``window`` (pages before Risk Factors).

``price_band`` stays ``None`` here: the band is announced after the RHP, so it is set on the
upload by a person or from the announcement (CC-07), never read from the RHP.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter

from finsight.core.config import get_settings
from finsight.core.schemas import (
    DecimalStr,
    FinancialSummary,
    ParsedDoc,
    Section,
    SummaryValue,
)
from finsight.storage import Storage, doc_key, put_json
from finsight.summary.derived import Ratio, extract_rows, ratios
from finsight.summary.holdings import promoter_pre
from finsight.summary.locate import Purpose, has_sod, source_of
from finsight.summary.strengths import Strength, extract_strengths

SOD_FILE = "sod.json"
_SECTIONS = TypeAdapter(list[Section])
_PURPOSES: tuple[Purpose, ...] = ("financials", "holdings", "litigation", "rpt", "objects")


class PriceBand(BaseModel):
    """The announced price band (₹ per share); set on an upload, never read from the RHP."""

    low: DecimalStr
    high: DecimalStr
    source: Literal["user", "announcement"]
    ref: str | None = None  # page or URL of the announcement


class SODResult(BaseModel):
    """What the SOD engine read from one offer document."""

    doc_id: str
    pipeline_version: str
    has_sod: bool
    source: dict[str, str] = Field(default_factory=dict)
    currency_unit: str = ""
    financials: dict[str, list[SummaryValue]] = Field(default_factory=dict)
    derived: list[Ratio] = Field(default_factory=list)
    promoter_holding_pre: SummaryValue | None = None
    promoter_holding_post: SummaryValue | None = None
    litigation: dict[str, SummaryValue] = Field(default_factory=dict)
    rpt_total: SummaryValue | None = None
    auditor_remarks: list[SummaryValue] = Field(default_factory=list)
    strengths: list[Strength] = Field(default_factory=list)
    price_band: PriceBand | None = None

    def fields(self) -> dict[str, SummaryValue]:
        """Flat ``{key: value}`` for fixture checks: ``revenue:latest``, ``net_worth:stub``,
        ``promoter_holding_pre``, ``criminal_cases`` …"""
        out: dict[str, SummaryValue] = {}
        for key, values in self.financials.items():
            for v in values:
                period = v.period if v.period in ("latest", "latest-1", "latest-2") else "stub"
                out.setdefault(f"{key}:{period}", v)
        singles: dict[str, SummaryValue | None] = {
            "promoter_holding_pre": self.promoter_holding_pre,
            "promoter_holding_post": self.promoter_holding_post,
            "rpt_total": self.rpt_total,
        }
        out.update({k: v for k, v in singles.items() if v is not None})
        out.update(self.litigation)
        return out


def _point(v: SummaryValue | None, stub: SummaryValue | None, key: str) -> list[SummaryValue]:
    latest = v or SummaryValue(key=key, period="latest")
    return [latest, stub or SummaryValue(key=key, period="stub")]


def build_sod(
    doc: ParsedDoc, sections: list[Section], summary: FinancialSummary, doc_id: str
) -> SODResult:
    """``SODResult`` from the parsed document and its already-built ``summary.json``."""
    rows = extract_rows(doc, sections, doc_id)
    financials: dict[str, list[SummaryValue]] = {
        "revenue": summary.revenue,
        "profit_after_tax": summary.profit_after_tax,
        "operating_cash_flow": summary.operating_cash_flow,
        "net_worth": _point(summary.net_worth, summary.net_worth_stub, "net_worth"),
        "total_borrowings": _point(
            summary.total_borrowings, summary.total_borrowings_stub, "total_borrowings"
        ),
        **rows,
    }
    return SODResult(
        doc_id=doc_id,
        pipeline_version=get_settings().pipeline_version,
        has_sod=has_sod(sections),
        source={p: source_of(sections, p) for p in _PURPOSES},
        currency_unit=summary.currency_unit,
        financials=financials,
        derived=ratios(summary),
        promoter_holding_pre=promoter_pre(doc, sections, doc_id),
        promoter_holding_post=summary.promoter_holding_post,
        litigation=summary.litigation,
        rpt_total=summary.rpt_total,
        auditor_remarks=summary.auditor_remarks,
        strengths=extract_strengths(doc, sections),
    )


def build(storage: Storage, doc_id: str) -> SODResult:
    """The ``sod`` stage: ``parsed.json`` + ``sections.json`` + ``summary.json`` → ``sod.json``."""
    doc = ParsedDoc.model_validate_json(storage.get_bytes(doc_key(doc_id, "parsed.json")))
    sections = _SECTIONS.validate_json(storage.get_bytes(doc_key(doc_id, "sections.json")))
    summary = FinancialSummary.model_validate_json(
        storage.get_bytes(doc_key(doc_id, "summary.json"))
    )
    result = build_sod(doc, sections, summary, doc_id)
    put_json(storage, doc_key(doc_id, SOD_FILE), result.model_dump(mode="json"))
    return result


__all__ = ["SOD_FILE", "PriceBand", "SODResult", "build", "build_sod"]
