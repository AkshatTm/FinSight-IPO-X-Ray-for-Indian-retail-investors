"""Write ``data/gold/gold_v3_template.jsonl``: one empty row per red-flag input per showcase IPO.

Gold v3 (B04 §2) holds the values the 13 red-flag checks need. Akshat pre-fills it with Claude
(chat) from the PDFs, with page and quote, then verifies every row (``label_source`` records
who filled it). Rows are generated, never typed, so the key list matches ``B01`` §5.

    uv run python scripts/make_gold_v3_template.py
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "gold" / "gold_v3_template.jsonl"

FISCALS = ("latest", "latest-1", "latest-2")

# (key, periods, doc, expected section, red flags that use it)
KEYS: list[tuple[str, tuple[str, ...], str, str, str]] = [
    ("revenue", FISCALS, "rhp", "summary: restated financial information", "RF09,RF10"),
    ("profit_after_tax", FISCALS, "rhp", "summary: restated financial information", "RF01,RF11"),
    ("operating_cash_flow", FISCALS, "rhp", "restated cash flow statement", "RF02"),
    ("total_borrowings", ("latest",), "rhp", "summary: restated financial information", "RF03"),
    ("net_worth", ("latest",), "rhp", "summary: restated financial information", "RF03,RF08"),
    ("offer_price", ("final",), "prospectus", "cover", "RF04,RF05,RF11"),
    ("fresh_issue_amount", ("final",), "prospectus", "cover / the offer", "RF04,RF07"),
    ("ofs_amount", ("final",), "prospectus", "cover / the offer", "RF04"),
    (
        "waca_selling_shareholders",
        ("final",),
        "prospectus",
        "summary: weighted average cost of acquisition",
        "RF05",
    ),
    (
        "promoter_holding_post_pct",
        ("final",),
        "prospectus",
        "capital structure / summary: shareholding",
        "RF06",
    ),
    ("general_purposes_pct_of_fresh", ("final",), "rhp", "objects of the offer", "RF07"),
    ("criminal_cases_any", ("latest",), "rhp", "summary: outstanding litigation", "RF08"),
    ("litigation_amount_total", ("latest",), "rhp", "summary: outstanding litigation", "RF08"),
    ("rpt_total", ("latest",), "rhp", "summary: related party transactions", "RF09"),
    ("customer_top1_pct", ("latest",), "rhp", "risk factors / our business", "RF10"),
    ("customer_top10_pct", ("latest",), "rhp", "risk factors / our business", "RF10"),
    ("peer_pe_list", ("final",), "prospectus", "basis for offer price", "RF11"),
    ("issuer_pe", ("final",), "prospectus", "basis for offer price", "RF11"),
    ("auditor_remarks", ("latest",), "rhp", "summary: auditor qualifications", "RF12"),
    ("pledged_promoter_pct", ("final",), "rhp", "capital structure: shareholding pattern", "RF13"),
    ("is_financial_company", ("final",), "rhp", "our business / cover", "RF03"),
]


def rows(ipo_ids: list[str]) -> list[dict[str, object]]:
    """Empty gold v3 rows for every IPO, key and period."""
    out: list[dict[str, object]] = []
    for ipo_id in ipo_ids:
        for key, periods, doc, section, flags in KEYS:
            for period in periods:
                out.append(
                    {
                        "ipo_id": ipo_id,
                        "key": key,
                        "period": period,
                        "doc": doc,
                        "expected_section": section,
                        "red_flags": flags,
                        "value_raw": "",
                        "unit": "",
                        "page": None,
                        "quote": "",
                        "status": "",  # found | placeholder | not_found
                        "label_source": "",  # e.g. claude_chat_prefill+akshat_verified
                        "changed_by_akshat": None,
                        "labelled_at": "",
                        "notes": "",
                    }
                )
    return out


def main() -> None:
    demo = yaml.safe_load((ROOT / "configs" / "demo_ipos.yaml").read_text(encoding="utf-8"))
    ipo_ids = [entry["ipo_id"] for entry in demo["ipos"]]
    lines = [json.dumps(r, ensure_ascii=False) for r in rows(ipo_ids)]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} rows for {len(ipo_ids)} IPOs to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
