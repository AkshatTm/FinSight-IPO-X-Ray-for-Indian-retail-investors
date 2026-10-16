"""Gold v3.1: the C-ADR-20 convention fixes as a NEW file; gold v3 is never edited.

    uv run python scripts/make_gold_v3_1.py [--gold-dir data/gold]

Reads ``gold_v3_summary.jsonl`` and writes, beside it:

* ``gold_v3_1_summary.jsonl``  v3 plus the fixes below (every other row is byte-identical),
* ``gold_v3_1_changelog.md``   every changed row, old and new,
* ``gold_v3_1_verify.csv``     only the changed rows, with what to check, for Akshat.

The fixes are *test-informed convention fixes* (Akshat's decisions after the v2 run, C-ADR-20):

* ``auditor_remarks``: the gold value is qualifications only; an Emphasis of Matter goes to notes.
* ``promoter_holding_post_pct``: three rows the Prospectus prints (``claude_code_fix``).
* ``waca_selling_shareholders``: all selling shareholders, promoter sellers included.
* ``issuer_pe`` (Hexaware): the computed value stays, flagged ``computed``.

A changed row keeps its original ``label_source`` and gains ``+claude_code_fix`` and
``needs_akshat_verify: true`` (a newly filled row is ``claude_code_fix`` alone); ``v3_1_change``
says what changed. ``summary_eval.py --pending-ok`` scores such rows and counts them.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = ROOT / "data" / "gold"
FIX = "claude_code_fix"

# Emphasis-of-Matter headings the pipeline's reader found on the examination-report pages. They are
# not part of the gold value (qualifications only); they are recorded so nothing is lost.
EOM_NOTES: dict[str, str] = {
    "ather-energy-2025": "RHP p366 (FY2022 note 1.2, basis of preparation)",
    "lg-electronics-india-2025": "RHP p278 (heading only; the extracted text is a fragment)",
    "tata-capital-2025": "RHP p445 (basis of accounting, special-purpose interim statements)",
    "urban-company-2025": "RHP p407 (special-purpose interim statements)",
}

PW_QUALIFICATIONS = (
    "Qualifications in the audit reports and CARO 2020 annexures for Fiscals 2025, 2024 and 2023 "
    "(no restatement effect needed); disclaimer on internal financial controls for Fiscal 2023"
)

PROMOTER_POST: dict[str, dict[str, Any]] = {
    "hdb-financial-services-2025": {
        "value_raw": "73.98",
        "page": 21,
        "computed": False,
        "quote": "Promoter and Promoter Selling Shareholder HDFC Bank Limited 750,596,670 94.04 "
        "615,461,535 73.98 (Total 750,596,670 94.04 615,461,535 73.98, p22)",
        "notes": "Prospectus summary table, post-offer on a fully diluted basis; also p136.",
    },
    "physicswallah-2025": {
        "value_raw": "71.48",
        "page": 149,
        "computed": False,
        "quote": "Alakh Pandey 1,051,200,000 40.31 1,033,768,808 35.74 Prateek Boob "
        "1,051,200,000 40.31 1,033,768,808 35.74 Total 2,102,400,000 80.62 2,067,537,616 71.48",
        "notes": "Printed total of the two promoters (also 35.74 + 35.74 on p33).",
    },
    "urban-company-2025": {
        "value_raw": "19.35 (computed: 3 promoters x 6.45)",
        "page": 27,
        "computed": True,
        "quote": "Raghav Chandra 97,762,500 7.03 6.65 97,762,500 6.45 Varun Khaitan 97,762,500 "
        "7.03 6.65 97,762,500 6.45 (Abhiraj Singh Bhal likewise 6.45; p28: 6.45% each)",
        "notes": "No printed promoter total: the three printed 6.45 rows added up (computed).",
    },
}

ATHER_SELLERS = (
    "Promoter selling shareholders: Tarun Sanjay Mehta 21.09; Swapnil Babanlal Jain 21.09. "
    "Other selling shareholders: Caladium Investment Pte Ltd 204.24; National Investment and "
    "Infrastructure Fund II 183.71; Internet Fund III Pte. Ltd. 38.58; IITM Incubation Cell Nil; "
    "IITMS Rural Technology and Business Incubator 8.31; Amit Bhatia 184.82"
)
GROWW_SELLERS = (
    "All 15 selling shareholders (all investors, no promoter sells): Peak XV Partners "
    "Investments VI-1 1.91; YC Holdings II 3.45; Ribbit Capital V 2.30; GW-E Ribbit Opportunity V "
    "37.87; Internet Fund VI 21.97; Propel Venture Partners 5.39; Sequoia Capital Global Growth "
    "37.94; Kauffman Fellows Fund 0.51; Friale Fund IV 0.29; Alkeon Innovation Master Fund II "
    "37.83; Alkeon Innovation Master Fund II Private Series 37.83; Alkeon Innovation Master Fund "
    "37.83; Alkeon Innovation Opportunity 37.83; Nirman Investments 0.79; Nirman Holdings 0.79"
)


def _change(row: Mapping[str, Any], **fields: Any) -> dict[str, Any]:
    """A copy of ``row`` with ``fields`` set, marked as changed and awaiting verification."""
    out = dict(row)
    out.update(fields)
    out["needs_akshat_verify"] = True
    return out


def _tag(label: str) -> str:
    return label if FIX in label else f"{label}+{FIX}"


def fix_row(row: Mapping[str, Any]) -> tuple[dict[str, Any], str] | None:
    """The v3.1 version of one row and a one-line description, or ``None`` when unchanged."""
    ipo, key = str(row["ipo_id"]), str(row["key"])
    label = str(row.get("label_source") or "")
    if key == "auditor_remarks":
        if ipo == "physicswallah-2025":
            note = (
                f"{row.get('notes') or ''} Emphasis of Matter on the FY2023 special-purpose "
                "statements (moved here from the value: gold v3.1 records qualifications only)."
            ).strip()
            new = _change(row, value_raw=PW_QUALIFICATIONS, notes=note, label_source=_tag(label))
            return new, "value is qualifications only; Emphasis of Matter moved to notes"
        if ipo in EOM_NOTES:
            note = (
                f"{row.get('notes') or ''} Emphasis of Matter heading found by the pipeline "
                f"reader at {EOM_NOTES[ipo]}; not part of the value (qualifications only)."
            ).strip()
            return _change(row, notes=note), "notes only: Emphasis of Matter recorded, value kept"
        return None
    if key == "promoter_holding_post_pct" and ipo in PROMOTER_POST:
        p = PROMOTER_POST[ipo]
        new = _change(
            row, status="found", value_raw=p["value_raw"], page=p["page"], quote=p["quote"],
            notes=p["notes"] + " Filled from the Prospectus after the v2 run (labeller's pack "
            "lacked the page).", computed=p["computed"], label_source=FIX,
        )  # fmt: skip
        return new, "was not_found; value, page and quote from the Prospectus"
    if key == "waca_selling_shareholders" and ipo == "ather-energy-2025":
        note = (
            "All selling shareholders, promoter sellers included (Hero MotoCorp, a promoter, "
            "does not sell). Pairing read from the Prospectus table, pp44-45 (the cover text "
            "was column-scrambled)."
        )
        new = _change(row, value_raw=ATHER_SELLERS, page=44, notes=note, label_source=_tag(label))
        return new, "complete list of selling shareholders (was the two promoter sellers only)"
    if key == "waca_selling_shareholders" and ipo == "groww-2025":
        note = "All 15 selling shareholders from the Prospectus table, p40 (v3 listed 10)."
        new = _change(row, value_raw=GROWW_SELLERS, page=40, notes=note, label_source=_tag(label))
        return new, "complete list of selling shareholders (was the top 10)"
    if key == "issuer_pe" and ipo == "hexaware-technologies-2025":
        note = (
            f"{row.get('notes') or ''} Computed value kept and flagged computed=true; the scorer "
            "accepts the computed value or the printed one."
        ).strip()
        return _change(row, computed=True, notes=note), "flagged computed=true, value kept"
    return None


# Rows that stay as they are on purpose; they go into the changelog so the reader sees them.
NOT_CHANGED = (
    "promoter_holding_post_pct: other not_found rows may also be printed in the Prospectus "
    "(Groww p30: Lalit Keshre 8.97 per row; Lenskart p34: Total (A) 17.51); Ather, Hexaware, "
    "Meesho and Tata Capital were not checked. Only the three rows Akshat named were filled. "
    "Filling the rest would turn Ather / Groww into pipeline misses (it reads not_found there); "
    "Lenskart (it reads 85.61) and Tata Capital (6.6) are wrong reads whatever the gold says.",
    "waca_selling_shareholders: Lenskart and Meesho list only some investors ('others on the "
    "cover'); the pipeline reads no WACA table there, so the score cannot change, but the rows "
    "are incomplete and need the cover read.",
    "auditor_remarks Lenskart: gold is not_found although the RHP summary (p36) prints a "
    "statement; unchanged.",
)


def build(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """``(v3.1 rows, change records)``; unchanged rows are returned as they came."""
    out: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for row in rows:
        fixed = fix_row(row)
        if fixed is None:
            out.append(dict(row))
            continue
        new, why = fixed
        out.append(new)
        changes.append({"old": dict(row), "new": new, "why": why})
    return out, changes


def _csv_rows(changes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    check = {
        "auditor_remarks": "Is the value only the qualifications? Is the Emphasis of Matter real?",
        "promoter_holding_post_pct": "Open the page: is this the post-offer % of the promoters?",
        "waca_selling_shareholders": "Is every selling shareholder listed once, with its cost?",
        "issuer_pe": "Nothing to change; the printed P/E is not in the text layer. Optional: type it.",
    }
    out = []
    for c in changes:
        o, n = c["old"], c["new"]
        out.append(
            {
                "ipo_id": n["ipo_id"], "key": n["key"], "period": n["period"],
                "what_changed": c["why"],
                "old_value": o.get("value_raw"), "new_value": n.get("value_raw"),
                "page": n.get("page"), "quote": n.get("quote"),
                "what_to_check": check[str(n["key"])],
                "verified_yes_no": "", "your_value_if_different": "",
            }
        )  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-dir", type=Path, default=GOLD_DIR)
    a = ap.parse_args(argv)
    src = a.gold_dir / "gold_v3_summary.jsonl"
    rows = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
    new_rows, changes = build(rows)
    (a.gold_dir / "gold_v3_1_summary.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_rows),
        encoding="utf-8", newline="\n",
    )  # fmt: skip
    lines = [
        "# Gold v3.1 changelog (test-informed convention fixes, C-ADR-20)",
        "",
        f"{len(changes)} rows changed out of {len(rows)}. Gold v3 is untouched.",
        "",
    ]
    for c in changes:
        n, o = c["new"], c["old"]
        lines += [
            f"## {n['ipo_id']} / {n['key']} / {n['period']}",
            f"- change: {c['why']}",
            f"- old: `{o.get('status')}` {o.get('value_raw')!r} (page {o.get('page')})",
            f"- new: `{n.get('status')}` {n.get('value_raw')!r} (page {n.get('page')})",
            f"- label_source: `{n.get('label_source')}`, needs_akshat_verify: true",
            "",
        ]
    lines += ["## Left unchanged on purpose", ""] + [f"- {t}" for t in NOT_CHANGED] + [""]
    (a.gold_dir / "gold_v3_1_changelog.md").write_text("\n".join(lines), encoding="utf-8")
    with (a.gold_dir / "gold_v3_1_verify.csv").open("w", encoding="utf-8-sig", newline="") as f:
        records = _csv_rows(changes)
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    print(f"wrote gold_v3_1 in {a.gold_dir}: {len(changes)} changed rows of {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
