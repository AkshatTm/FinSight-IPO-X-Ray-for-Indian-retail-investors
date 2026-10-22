"""Summary and financial extraction: an offer document → ``summary.json`` (B02 §6a, C3.1).

``extract_summary(doc, sections)`` reads the red-flag inputs from the parsed pages and returns a
``FinancialSummary``. Every value is ``found`` or ``stated_zero`` with its page evidence,
``placeholder`` (``[●]``) or ``not_found``; nothing is guessed, and a computed value (a sum, a
weighted average, a share) says so in its evidence. C3.1a reads the financial tables (revenue,
profit after tax, operating cash flow, total borrowings, net worth); C3.1b reads litigation,
promoter holdings and pledges, WACA, customers, objects, related-party total, peers, auditor
remarks and whether the issuer is a bank, NBFC or insurer (whose statements use other rows).
``build(storage, doc_id)`` is the ``financials`` upload stage.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import TypeAdapter

from finsight.core.logging import get_logger
from finsight.core.schemas import FinancialSummary, ParsedDoc, Peer, Section, SummaryValue, Table
from finsight.parse import find_subsection_pages
from finsight.storage import Storage, doc_key, put_json
from finsight.summary.auditor import extract_auditor_remarks, is_financial_company
from finsight.summary.customers import extract_customers
from finsight.summary.financials import (
    FinancialValues,
    clean_label,
    extract_financials,
    values_by_source,
)
from finsight.summary.holdings import Holdings, extract_holdings
from finsight.summary.layout import GridTable, read_tables
from finsight.summary.litigation import extract_litigation
from finsight.summary.locate import has_sod, reader_pages, scan_start, source_of
from finsight.summary.objects import general_purposes, related_party_total
from finsight.summary.peers import extract_peers
from finsight.summary.periods import PERIOD_KEYS, Period, parse_period, rank_years

SUMMARY_FILE = "summary.json"
PEER_SECTIONS = ("basis_for_offer_price",)  # ruled tables the stage extracts for the peers
_SECTIONS = TypeAdapter(list[Section])
logger = get_logger("finsight.summary")
T = TypeVar("T")


def _guard(name: str, fn: Callable[[], T], default: T) -> T:
    """One reader failing leaves its field empty (``not_found``), not the whole summary."""
    try:
        return fn()
    except Exception:  # a reader bug must not drop the other fields
        logger.exception("summary reader failed", extra={"reader": name})
        return default


def extract_summary(
    doc: ParsedDoc,
    sections: list[Section],
    doc_id: str | None = None,
    subsections: dict[str, list[int]] | None = None,
    tables: list[Table] | None = None,
) -> FinancialSummary:
    """``summary.json`` for one parsed document.

    Args:
        doc: The parsed document (all pages, or only some, e.g. a fixture pack).
        sections: Its detected sections.
        doc_id: The id written into the evidence; defaults to ``doc.ipo_id``.
        subsections: Pages of the restated cash-flow statement and the auditor's report; found
            from ``doc`` when omitted (``find_subsection_pages``).
        tables: Ruled tables (``parse.extract_tables``) of Basis for Offer Price, if extracted;
            the peer table is read from the words otherwise.
    """
    did = doc_id or doc.ipo_id
    subs = subsections if subsections is not None else _subsections(doc, sections)
    financial = _guard("financial_company", lambda: is_financial_company(doc, sections), False)
    fin = extract_financials(doc, sections, did, subs.get("cash_flows", []), financial=financial)
    holdings = _guard(
        "holdings", lambda: extract_holdings(doc, sections, did), Holdings(None, None, True)
    )
    no_share: tuple[SummaryValue | None, SummaryValue | None] = (None, None)
    top1, top10 = _guard("customers", lambda: extract_customers(doc, sections, did), no_share)
    none: SummaryValue | None = None
    no_litigation: dict[str, SummaryValue] = {}
    no_peers: list[Peer] = []
    no_remarks: list[SummaryValue] = []
    return FinancialSummary(
        doc_id=did,
        currency_unit=fin.currency_unit,
        revenue=fin.revenue,
        profit_after_tax=fin.profit_after_tax,
        operating_cash_flow=fin.operating_cash_flow,
        total_borrowings=fin.total_borrowings,
        net_worth=fin.net_worth,
        total_borrowings_stub=fin.total_borrowings_stub,
        net_worth_stub=fin.net_worth_stub,
        waca=holdings.waca,
        litigation=_guard(
            "litigation", lambda: extract_litigation(doc, sections, did), no_litigation
        ),
        rpt_total=_guard("rpt", lambda: related_party_total(doc, sections, did), none),
        promoter_holding_post=holdings.promoter_holding_post,
        promoter_identifiable=holdings.promoter_identifiable,
        pledged_pct=holdings.pledged_pct,
        customer_top1_pct=top1,
        customer_top10_pct=top10,
        general_purposes_pct=_guard("gcp", lambda: general_purposes(doc, sections, did), none),
        peers=_guard("peers", lambda: extract_peers(doc, sections, did, tables), no_peers),
        auditor_remarks=_guard(
            "auditor",
            lambda: extract_auditor_remarks(doc, sections, did, subs.get("auditors_report")),
            no_remarks,
        ),
        is_financial_company=financial,
    )


def _subsections(doc: ParsedDoc, sections: list[Section]) -> dict[str, list[int]]:
    # find_subsection_pages indexes pages by position, so it needs every page of the document.
    if len(doc.pages) != doc.n_pages:
        return {}
    return find_subsection_pages(doc, sections)


def build(storage: Storage, doc_id: str) -> FinancialSummary:
    """The ``financials`` stage without a PDF: ``parsed.json`` + ``sections.json`` →
    ``summary.json`` (peers from the words only)."""
    doc = ParsedDoc.model_validate_json(storage.get_bytes(doc_key(doc_id, "parsed.json")))
    sections = _SECTIONS.validate_json(storage.get_bytes(doc_key(doc_id, "sections.json")))
    summary = extract_summary(doc, sections, doc_id)
    put_json(storage, doc_key(doc_id, SUMMARY_FILE), summary.model_dump(mode="json"))
    return summary


__all__ = [
    "PEER_SECTIONS",
    "PERIOD_KEYS",
    "SUMMARY_FILE",
    "FinancialValues",
    "GridTable",
    "Period",
    "build",
    "clean_label",
    "extract_financials",
    "extract_summary",
    "has_sod",
    "parse_period",
    "rank_years",
    "read_tables",
    "reader_pages",
    "scan_start",
    "source_of",
    "values_by_source",
]
