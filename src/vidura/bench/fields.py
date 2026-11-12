"""Task A fields: what each gold v3 key means, its retrieval group and the question the model gets.

A gold v3 row is ``(ipo_id, key, period, doc)``. The bench asks every model for the same fields
(``FIELDS``), grouped so that facts read from the same part of the document share one retrieved
context and one prompt (``GROUPS``: the retrieval query of each group). The texts were written
once, before any model ran, and are frozen with the bench (C-ADR-06).
"""

from __future__ import annotations

from dataclasses import dataclass

PERIODS = {
    "latest": "the latest full financial year",
    "latest-1": "the financial year before the latest full financial year",
    "latest-2": "two financial years before the latest full financial year",
    "final": "as stated in this offer document",
}


@dataclass(frozen=True)
class Field:
    """One Task A field: its group and a plain description for the prompt."""

    key: str
    group: str
    text: str  # "{period}" is filled with ``PERIODS[period]``


FIELDS: dict[str, Field] = {
    f.key: f
    for f in (
        Field("revenue", "pnl", "Revenue from operations (restated, consolidated) for {period}."),
        Field(
            "profit_after_tax",
            "pnl",
            "Restated profit or loss after tax for {period}; a loss is a negative value.",
        ),
        Field(
            "operating_cash_flow",
            "cashflow",
            "Net cash flow from (or used in) operating activities for {period}; cash used is "
            "negative.",
        ),
        Field(
            "total_borrowings",
            "balance",
            "Total borrowings (current plus non-current) at the end of the latest full financial "
            "year.",
        ),
        Field("net_worth", "balance", "Net worth at the end of the latest full financial year."),
        Field("offer_price", "offer", "Offer price per equity share."),
        Field(
            "fresh_issue_amount",
            "offer",
            "Amount raised by the fresh issue (zero or stated_zero when there is no fresh issue).",
        ),
        Field("ofs_amount", "offer", "Amount of the offer for sale."),
        Field(
            "promoter_holding_post_pct",
            "shareholding",
            "Promoters' (and promoter group's) shareholding after the offer, as a percentage.",
        ),
        Field(
            "pledged_promoter_pct",
            "shareholding",
            "Percentage of promoter shares pledged or encumbered.",
        ),
        Field(
            "waca_promoters",
            "waca",
            "Weighted average cost of acquisition per share for the promoters.",
        ),
        Field(
            "waca_selling_shareholders",
            "waca",
            "Weighted average cost of acquisition per share for the selling shareholders (give "
            "the figure for each selling shareholder if they differ).",
        ),
        Field(
            "general_purposes_pct_of_fresh",
            "objects",
            "General corporate purposes as a percentage of the fresh issue proceeds.",
        ),
        Field(
            "litigation_amount_total",
            "litigation",
            "Total amount involved in outstanding litigation (sum of the amounts printed in the "
            "summary of outstanding litigation).",
        ),
        Field(
            "criminal_cases_any",
            "litigation",
            "Are there outstanding criminal proceedings (by or against the company, its "
            "directors, promoters or subsidiaries)? Answer Yes or No, with the count if printed.",
        ),
        Field(
            "rpt_total",
            "rpt",
            "Total of related party transactions for {period}.",
        ),
        Field(
            "customer_top1_pct",
            "customers",
            "Share of revenue from the single largest customer, as a percentage, for {period}.",
        ),
        Field(
            "customer_top10_pct",
            "customers",
            "Share of revenue from the top ten customers, as a percentage, for {period}.",
        ),
        Field(
            "issuer_pe",
            "peers",
            "The company's own price-to-earnings (P/E) ratio at the offer price, in times.",
        ),
        Field(
            "peer_pe_list",
            "peers",
            "P/E ratios of the listed industry peers in the comparison table (name and P/E for "
            "each peer).",
        ),
        Field(
            "auditor_remarks",
            "auditor",
            "Auditor qualifications, reservations or adverse remarks on the financial statements "
            "(write 'No qualifications' if the document says there are none).",
        ),
        Field(
            "is_financial_company",
            "company",
            "Is the company itself a bank, NBFC or insurer? Answer Yes or No.",
        ),
    )
}

GROUPS: dict[str, str] = {
    "pnl": "restated summary statement of profit and loss revenue from operations restated "
    "profit after tax for the year",
    "cashflow": "restated statement of cash flows net cash flow from operating activities",
    "balance": "restated statement of assets and liabilities net worth total borrowings",
    "offer": "offer price per equity share fresh issue aggregating offer for sale aggregating",
    "shareholding": "promoter and promoter group shareholding pre-offer post-offer percentage "
    "pledged encumbered shares",
    "waca": "weighted average cost of acquisition per equity share promoters selling shareholders",
    "objects": "objects of the offer general corporate purposes amount proposed to be funded "
    "from net proceeds",
    "litigation": "summary of outstanding litigation criminal proceedings aggregate amount "
    "involved",
    "rpt": "summary of related party transactions total",
    "customers": "revenue from largest customer top ten customers percentage of revenue from "
    "operations",
    "peers": "basis for offer price comparison with listed industry peers price earnings ratio",
    "auditor": "auditor qualifications reservations adverse remarks emphasis of matter "
    "restated financial information",
    "company": "non-banking financial company registered with the reserve bank of india bank "
    "insurance company",
}


def field_id(key: str, period: str) -> str:
    """The id a Task A answer uses for one field (``revenue@latest``)."""
    return f"{key}@{period}"


def describe(key: str, period: str) -> str:
    """The field's description with the period filled in."""
    return FIELDS[key].text.format(period=PERIODS.get(period, period))
