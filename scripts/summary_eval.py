"""E14: summary extraction against gold v3 → ``eval_results/b/summary_extraction.json``.

    uv run python scripts/summary_eval.py --slice dev --allow-unverified   # tuning aid, dev only
    uv run python scripts/summary_eval.py --slice all --final              # the E14 run, once

Each gold v3 row (``data/gold/gold_v3_summary.jsonl``, keys as in ``gold_v3_template.jsonl``) is
compared with the value ``extract_summary`` reads from the same document (the RHP, or the
Prospectus when the row says so and it was parsed). Gold values are normalised with the same
parsers as the red-flag gold path (``redflags.inputs``), so both sides use one unit convention.

* A gold ``placeholder`` or ``not_found`` row is correct when the pipeline reports that status.
* A gold value is correct (numeric value match, NVM) when the pipeline's value matches: money
  within 0.5 % (tables round differently), percentages within 0.05 points, counts exactly,
  yes/no exactly, auditor remarks by kind (qualified / emphasis / CARO / none), peer P/E lists
  element by element within 1 %.
* Page agreement is reported where both sides give a page.

Offer facts (price, fresh issue, OFS) are X-Ray fields, scored elsewhere; they are counted as out
of scope here. C-ADR-02: only ``dev`` may be scored before the final run, and a final run needs
every row verified by Akshat (``label_source`` contains ``akshat_verified``).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.core.schemas import (  # noqa: E402
    SUMMARY_HAS_VALUE,
    Count,
    FinancialSummary,
    Money,
    ParsedDoc,
    Percent,
    Section,
    SummaryValue,
)
from finsight.redflags.inputs import _decimal, _gold_amount, _yes_no, auditor_kind  # noqa: E402

GOLD = ROOT / "data" / "gold" / "gold_v3_summary.jsonl"
OUT = ROOT / "eval_results" / "b" / "summary_extraction.json"
VERIFIED = "akshat_verified"
OUT_OF_SCOPE = {"offer_price", "fresh_issue_amount", "ofs_amount"}
MONEY_TOL = Decimal("0.005")
PCT_TOL = Decimal("0.05")
PE_TOL = Decimal("0.01")
SECTIONS = TypeAdapter(list[Section])


@dataclass
class Pred:
    """The pipeline's answer for one gold row."""

    status: str  # found / stated_zero / placeholder / not_found
    value: Any = None
    page: int | None = None


def _sv(v: SummaryValue | None) -> Pred:
    if v is None:
        return Pred("not_found")
    page = v.evidence.page if v.evidence else None
    if v.status not in SUMMARY_HAS_VALUE:
        return Pred(v.status, None, page)
    val = v.value
    if isinstance(val, Money):
        out: Any = val.value_inr
    elif isinstance(val, Percent | Count):
        out = val.value
    else:
        out = val
    return Pred(v.status, out, page)


def predicted(summary: FinancialSummary, key: str, period: str) -> Pred:
    """The summary's value for a gold v3 key and period."""
    yearly = {"latest": 0, "latest-1": 1, "latest-2": 2}
    if key in {"revenue", "profit_after_tax", "operating_cash_flow"}:
        values = getattr(summary, key)
        i = yearly.get(period)
        return _sv(values[i]) if i is not None and i < len(values) else Pred("not_found")
    simple = {
        "total_borrowings": summary.total_borrowings,
        "net_worth": summary.net_worth,
        "promoter_holding_post_pct": summary.promoter_holding_post,
        "general_purposes_pct_of_fresh": summary.general_purposes_pct,
        "litigation_amount_total": summary.litigation.get("amount_total"),
        "criminal_cases_any": summary.litigation.get("criminal_cases"),
        "rpt_total": summary.rpt_total,
        "customer_top1_pct": summary.customer_top1_pct,
        "customer_top10_pct": summary.customer_top10_pct,
        "pledged_promoter_pct": summary.pledged_pct,
        "waca_selling_shareholders": summary.waca[0] if summary.waca else None,
    }
    if key in simple:
        return _sv(simple[key])
    if key == "is_financial_company":
        return Pred("found", summary.is_financial_company)
    if key == "auditor_remarks":
        texts = [str(v.value) for v in summary.auditor_remarks if v.status == "found"]
        if not texts:
            return Pred("not_found")
        page = summary.auditor_remarks[0].evidence
        return Pred("found", " ".join(texts), page.page if page else None)
    peers = [p for p in summary.peers if not p.is_issuer]
    issuer = next((p for p in summary.peers if p.is_issuer), None)
    if key == "peer_pe_list":
        pes = sorted(p.pe for p in peers if p.pe is not None)
        page = peers[0].evidence.page if peers and peers[0].evidence else None
        return Pred("found", pes, page) if pes else Pred("not_found")
    if key == "issuer_pe":
        if issuer is None:
            return Pred("not_found")
        page = issuer.evidence.page if issuer.evidence else None
        return Pred("found", issuer.pe, page) if issuer.pe is not None else Pred("placeholder")
    return Pred("not_found")


def gold_value(row: Mapping[str, Any]) -> Any:
    """The gold row's value normalised like the red-flag gold path."""
    key, raw = str(row["key"]), str(row.get("value_raw") or "").strip()
    if key == "criminal_cases_any":
        return int(raw) if raw.isdigit() else _yes_no(raw)
    if key == "is_financial_company":
        return _yes_no(raw)
    if key == "auditor_remarks":
        return raw
    if key == "peer_pe_list":
        return sorted(d for part in re.split(r"[;,]\s*", raw) if (d := _decimal(part)) is not None)
    if key in {
        "promoter_holding_post_pct", "general_purposes_pct_of_fresh", "customer_top1_pct",
        "customer_top10_pct", "pledged_promoter_pct", "issuer_pe",
    }:  # fmt: skip
        return _decimal(raw)
    value = _gold_amount(row)
    if isinstance(value, Money):
        return value.value_inr
    if key == "waca_selling_shareholders" and raw:
        return _decimal(raw)
    return value


def _close(a: Decimal, b: Decimal, rel: Decimal) -> bool:
    top = max(abs(a), abs(b))
    return a == b if top == 0 else abs(a - b) / top <= rel


def values_match(key: str, gold: Any, pred: Any) -> bool:
    """Whether the pipeline's value is the gold value under the key's rule."""
    if gold is None or pred is None:
        return False
    if key == "criminal_cases_any":
        if isinstance(gold, bool):
            return gold == (int(pred) > 0)
        return int(gold) == int(pred)
    if key == "is_financial_company":
        return bool(gold) == bool(pred)
    if key == "auditor_remarks":
        return auditor_kind(str(gold)) == auditor_kind(str(pred))
    if key == "peer_pe_list":
        return len(gold) == len(pred) and all(
            _close(Decimal(g), Decimal(p), PE_TOL) for g, p in zip(gold, pred, strict=True)
        )
    if key == "issuer_pe":
        return _close(Decimal(gold), Decimal(pred), PE_TOL)
    if key.endswith("_pct") or key == "general_purposes_pct_of_fresh":
        return abs(Decimal(gold) - Decimal(pred)) <= PCT_TOL
    return _close(Decimal(gold), Decimal(pred), MONEY_TOL)


def score_row(row: Mapping[str, Any], summary: FinancialSummary | None) -> dict[str, Any]:
    """One scored gold row."""
    key, period = str(row["key"]), str(row["period"])
    gold_status = str(row.get("status") or "found")
    out: dict[str, Any] = {
        "ipo_id": row["ipo_id"], "key": key, "period": period, "doc": row.get("doc"),
        "gold_status": gold_status, "label_source": row.get("label_source") or "",
    }  # fmt: skip
    if key in OUT_OF_SCOPE:
        return out | {"scope": "out_of_scope"}
    pred = predicted(summary, key, period) if summary is not None else Pred("not_found")
    out |= {"scope": "summary", "pred_status": pred.status}
    if gold_status in {"placeholder", "not_found"}:
        out["correct"] = pred.status == gold_status
    else:
        out["correct"] = pred.status in SUMMARY_HAS_VALUE and values_match(
            key, gold_value(row), pred.value
        )
    gold_page = row.get("page")
    if gold_page and pred.page:
        out["page_match"] = int(gold_page) == int(pred.page)
    return out


def summarise(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """Accuracy per key, NVM over gold values, status accuracy over gold blanks, page agreement."""
    rows = [r for r in scored if r.get("scope") == "summary"]
    per_key: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        per_key[r["key"]]["n"] += 1
        per_key[r["key"]]["correct"] += bool(r["correct"])
    valued = [r for r in rows if r["gold_status"] not in {"placeholder", "not_found"}]
    blanks = [r for r in rows if r["gold_status"] in {"placeholder", "not_found"}]
    pages = [r for r in rows if "page_match" in r]

    def share(xs: list[dict[str, Any]], field: str) -> float | None:
        return round(sum(bool(x[field]) for x in xs) / len(xs), 3) if xs else None

    return {
        "n_rows": len(rows),
        "n_out_of_scope": sum(r.get("scope") == "out_of_scope" for r in scored),
        "nvm": share(valued, "correct"),
        "n_valued": len(valued),
        "status_accuracy_on_blanks": share(blanks, "correct"),
        "n_blanks": len(blanks),
        "page_agreement": share(pages, "page_match"),
        "n_pages_compared": len(pages),
        "per_key": {
            k: {"n": c["n"], "accuracy": round(c["correct"] / c["n"], 3)}
            for k, c in sorted(per_key.items())
        },
        "label_sources": dict(Counter(r["label_source"] for r in rows)),
    }


def unverified(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """``ipo_id:key:period`` of every row Akshat has not verified."""
    return [
        f"{r['ipo_id']}:{r['key']}:{r['period']}"
        for r in rows
        if VERIFIED not in str(r.get("label_source") or "")
    ]


def _paths(processed: Path, ipo_id: str, doc: str) -> tuple[Path, Path]:
    suffix = "" if doc == "rhp" else "_prospectus"
    base = processed / ipo_id
    return base / f"parsed{suffix}.json", base / f"sections{suffix}.json"


def load_summary(processed: Path, ipo_id: str, doc: str) -> tuple[FinancialSummary | None, str]:
    """``extract_summary`` on the IPO's parsed document; the RHP when the Prospectus is missing."""
    from finsight.summary import extract_summary

    for which in dict.fromkeys((doc, "rhp")):
        parsed, sections = _paths(processed, ipo_id, which)
        if parsed.exists() and sections.exists():
            d = ParsedDoc.model_validate_json(parsed.read_bytes())
            secs = SECTIONS.validate_json(sections.read_bytes())
            return extract_summary(d, secs, ipo_id), which
    return None, "missing"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice", default="dev", choices=("dev", "test", "all"))
    ap.add_argument("--gold", type=Path, default=GOLD)
    ap.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--allow-unverified", action="store_true", help="dev only: a tuning draft")
    ap.add_argument("--final", action="store_true", help="the one E14 run on test/all slices")
    a = ap.parse_args(argv)
    demo = yaml.safe_load((ROOT / "configs" / "demo_ipos.yaml").read_text(encoding="utf-8"))
    split = {e["ipo_id"]: e["split"] for e in demo["ipos"]}
    if a.slice != "dev" and not a.final:
        ap.error("C-ADR-02: test documents are scored once, with --final")
    if a.slice != "dev" and a.allow_unverified:
        ap.error("the final E14 run needs every row verified")
    rows = [json.loads(x) for x in a.gold.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if a.slice == "all" or split.get(str(r["ipo_id"])) == a.slice]
    missing = unverified(rows)
    if missing and not a.allow_unverified:
        ap.error(f"{len(missing)} gold rows are not verified yet (e.g. {missing[0]})")
    cache: dict[tuple[str, str], tuple[FinancialSummary | None, str]] = {}
    scored = []
    for row in rows:
        k = (str(row["ipo_id"]), str(row.get("doc") or "rhp"))
        if k not in cache:
            cache[k] = load_summary(a.processed, *k)
        summary, used = cache[k]
        scored.append(score_row(row, summary) | {"doc_used": used})
    result = {
        "experiment": "E14 summary extraction",
        "slice": a.slice,
        "final": a.final,
        "draft": bool(missing),
        "written_by": "scripts/summary_eval.py",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rules": {"money_rel_tol": str(MONEY_TOL), "pct_abs_tol": str(PCT_TOL),
                  "pe_rel_tol": str(PE_TOL)},
        "summary": summarise(scored),
        "rows": scored,
    }  # fmt: skip
    out = a.out or (OUT if a.final else OUT.with_name(f"summary_extraction_{a.slice}_draft.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n")
    print(f"wrote {out}: NVM {result['summary']['nvm']} over {result['summary']['n_valued']} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
