"""Summary and financial extraction: an offer document → ``summary.json`` (B02 §6a, C3.1).

``extract_summary(doc, sections)`` reads the red-flag inputs from the parsed pages and returns a
``FinancialSummary``. Every value is ``found`` with its page evidence, ``placeholder`` or
``not_found``; nothing is guessed. C3.1a reads the financial tables (revenue, profit after tax,
operating cash flow, total borrowings, net worth); the other fields (WACA, litigation,
related-party transactions, shareholding, pledges, customers, peers, auditor remarks, financial
company) stay empty until C3.1b. ``build(storage, doc_id)`` is the ``financials`` upload stage.
"""

from __future__ import annotations

from pydantic import TypeAdapter

from finsight.core.schemas import FinancialSummary, ParsedDoc, Section
from finsight.parse import find_subsection_pages
from finsight.storage import Storage, doc_key, put_json
from finsight.summary.financials import (
    FinancialValues,
    clean_label,
    extract_financials,
    values_by_source,
)
from finsight.summary.layout import GridTable, read_tables
from finsight.summary.periods import PERIOD_KEYS, Period, parse_period, rank_years

SUMMARY_FILE = "summary.json"
_SECTIONS = TypeAdapter(list[Section])


def extract_summary(
    doc: ParsedDoc,
    sections: list[Section],
    doc_id: str | None = None,
    subsections: dict[str, list[int]] | None = None,
) -> FinancialSummary:
    """``summary.json`` for one parsed document.

    Args:
        doc: The parsed document (all pages, or only some, e.g. a fixture pack).
        sections: Its detected sections.
        doc_id: The id written into the evidence; defaults to ``doc.ipo_id``.
        subsections: Pages of the restated cash-flow statement etc.; found from ``doc`` when
            omitted (``find_subsection_pages``).
    """
    did = doc_id or doc.ipo_id
    subs = subsections if subsections is not None else _subsections(doc, sections)
    fin = extract_financials(doc, sections, did, subs.get("cash_flows", []))
    return FinancialSummary(
        doc_id=did,
        currency_unit=fin.currency_unit,
        revenue=fin.revenue,
        profit_after_tax=fin.profit_after_tax,
        operating_cash_flow=fin.operating_cash_flow,
        total_borrowings=fin.total_borrowings,
        net_worth=fin.net_worth,
    )


def _subsections(doc: ParsedDoc, sections: list[Section]) -> dict[str, list[int]]:
    # find_subsection_pages indexes pages by position, so it needs every page of the document.
    if len(doc.pages) != doc.n_pages:
        return {}
    return find_subsection_pages(doc, sections)


def build(storage: Storage, doc_id: str) -> FinancialSummary:
    """The ``financials`` stage: ``parsed.json`` + ``sections.json`` → ``summary.json``."""
    doc = ParsedDoc.model_validate_json(storage.get_bytes(doc_key(doc_id, "parsed.json")))
    sections = _SECTIONS.validate_json(storage.get_bytes(doc_key(doc_id, "sections.json")))
    summary = extract_summary(doc, sections, doc_id)
    put_json(storage, doc_key(doc_id, SUMMARY_FILE), summary.model_dump(mode="json"))
    return summary


__all__ = [
    "PERIOD_KEYS",
    "SUMMARY_FILE",
    "FinancialValues",
    "GridTable",
    "Period",
    "build",
    "clean_label",
    "extract_financials",
    "extract_summary",
    "parse_period",
    "rank_years",
    "read_tables",
    "values_by_source",
]
