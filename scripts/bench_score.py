"""Score every system that has answers on the frozen bench → ``eval_results/c4/`` (C4.1 / C4.4).

    uv run python scripts/bench_score.py

Writes ``bench_<system>.json`` (every scored item) and ``bench_summary.json`` (metrics with
IPO-cluster 95 % intervals, paired differences, latency, cost, which runs are still missing, and
whether any scorer file changed since the freeze), plus ``bench_failures.json`` (failures picked
by a fixed rule for the error analysis). Task A uses the E14 matcher (``summary_eval``), Task B
the pinned red-flag engine and the E15 comparison, Tasks C, D and G ``finsight.bench.score``.
Every number is a single run; nothing here is typed by hand.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import summary_eval  # noqa: E402
from bench_run import BENCH, load_prompts, passages  # noqa: E402
from redflag_eval import ORDINAL  # noqa: E402

from finsight.bench import (  # noqa: E402
    FLAT,
    Patterns,
    gold_amount_from_row,
    load,
    metric,
    paired,
    parse_task_a,
    score_guard,
    score_question,
    score_rewrite,
    sha256,
)
from finsight.core.schemas import SUMMARY_HAS_VALUE  # noqa: E402
from finsight.redflags import evaluate, inputs_from_gold  # noqa: E402

OUT = ROOT / "eval_results" / "c4"
SYSTEMS = ("rules_v1", "student", "base", "teacher", "opus", "opus_api", "chatgpt_go")
SCORER_FILES = (
    "scripts/summary_eval.py",
    "scripts/redflag_eval.py",
    "scripts/bench_score.py",
    "src/finsight/bench/score.py",
    "configs/forbidden_phrases.yaml",
)
MONEY_KEYS = {"revenue", "profit_after_tax", "operating_cash_flow", "total_borrowings", "net_worth",
              "fresh_issue_amount", "ofs_amount", "offer_price", "rpt_total",
              "litigation_amount_total"}  # fmt: skip


# Scorer changes made after the freeze and before any score was read; each applies to every system.
POST_FREEZE_CHANGES = [
    "scripts/summary_eval.py: main gained the opt-in gold v3.1 convention (off here; v3 keys).",
    "finsight/bench/score.py: gold_in_context / citation_has_value also accept the gold's printed "
    "digits (3+) in table text, since tables print bare numbers with the unit in the header.",
    "finsight/bench/answers.py: Task A replies shaped {field id: value} or {field id: {status, "
    "value, unit, page}} are read (value-only ones get no unit or page) instead of scoring as "
    "unparseable; the fields are counted as n_flat_format_fields.",
    "scripts/bench_score.py: the counts above, and the error-analysis picks use a sha256 order of "
    "item ids instead of sorted ids (all picks were the first IPO); no metric changes.",
]


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# ----------------------------------------------------------------------------- Task A
def _dec(v: Any) -> Any:
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, list):
        return [_dec(x) for x in v]
    try:
        return Decimal(str(v))
    except InvalidOperation:
        return v


def model_row(key: str, period: str, fa: Any) -> dict[str, Any]:
    """A system's field answer as a gold-v3-shaped row (the red-flag gold path reads it)."""
    if fa is None:
        return {"key": key, "period": period, "status": "not_found", "value_raw": "", "unit": ""}
    return {"key": key, "period": period, "status": fa.status, "value_raw": fa.value,
            "unit": fa.unit, "page": fa.page, "doc": None}  # fmt: skip


def pred_from_row(row: dict[str, Any]) -> summary_eval.Pred:
    """``summary_eval.Pred`` from a model row: the value normalised like the gold side."""
    status = row["status"]
    if status != "found" or not str(row.get("value_raw") or "").strip():
        return summary_eval.Pred(
            status if status != "found" else "not_found", None, row.get("page")
        )
    try:
        v = summary_eval.gold_value(row)
    except Exception:  # an unreadable value is no value
        v = None
    key = row["key"]
    if isinstance(v, tuple):
        v = v[1]
    if isinstance(v, list):
        if key in summary_eval.MULTI_PART_MONEY:
            v = v[-1] if v else None  # the parts' sum
        elif key != "peer_pe_list":
            v = v[0] if v else None
    return summary_eval.Pred("found", v, row.get("page"))


def score_pred(row: dict[str, Any], pred: summary_eval.Pred) -> dict[str, Any]:
    """``summary_eval.score_row`` for any system's prediction (offer facts included)."""
    key = str(row["key"])
    gold_status = str(row.get("status") or "found")
    out: dict[str, Any] = {"pred_status": pred.status, "gold_status": gold_status}
    if gold_status in {"placeholder", "not_found"}:
        out["correct"] = pred.status == gold_status
    elif gold_status == "stated_zero":
        out["correct"] = summary_eval.zero_matches(key, pred)
    else:
        gold = summary_eval.gold_value(row)
        has = pred.status in SUMMARY_HAS_VALUE
        if gold is None or gold == []:
            if key != "peer_pe_list" and str(row.get("value_raw") or "").strip():
                out["gold_expects_no_value"] = True
                out["correct"] = not has or pred.value in (None, [])
            else:
                out["unscorable"] = True
                out["correct"] = False
        elif isinstance(gold, tuple) and key in summary_eval.WACA_KEYS and not has:
            out["correct"] = True
        else:
            try:
                out["correct"] = has and summary_eval.values_match(key, gold, pred.value)
            except (ArithmeticError, TypeError, ValueError):
                out["correct"] = False
        if key in MONEY_KEYS and has and not out["correct"]:
            out["scale_error"] = _power_of_ten(gold, pred.value)
    if row.get("page") and pred.page:
        out["page_match"] = int(row["page"]) == int(pred.page)
    out["answered"] = pred.status != "not_found"
    return out


def _power_of_ten(gold: Any, pred: Any) -> bool:
    try:
        g, p = abs(Decimal(gold)), abs(Decimal(pred))
    except (InvalidOperation, TypeError, ValueError):
        return False
    if g == 0 or p == 0:
        return False
    ratio = max(g, p) / min(g, p)
    return any(abs(ratio / Decimal(10) ** k - 1) <= Decimal("0.005") for k in range(1, 8))


def task_a_b(system: str, answers: list[dict[str, Any]], ctx: dict[str, Any]) -> tuple[list, list]:
    """Scored Task A fields and Task B statuses for one system."""
    keys = {k["item_id"]: k for k in ctx["keys_a"]}
    prompts = {p["prompt_id"]: p for p in ctx["prompts"] if p["task"] == "A"}
    by_prompt = {a["prompt_id"]: a for a in answers if a["task"] == "A"}
    rows_a, model_rows = [], defaultdict(list)
    for item in ctx["items_a"]:
        key, fid = keys[item["item_id"]], f"{item['key']}@{item['period']}"
        if system == "rules_v1":
            rec = by_prompt.get(f"A:{item['ipo_id']}:rules:{item['doc']}")
            f = (rec or {}).get("fields", {}).get(fid)
            pred = (summary_eval.Pred(f["status"], _dec(f["value"]), f["page"]) if f
                    else summary_eval.Pred("not_found"))  # fmt: skip
            seconds = rec["seconds"] if rec else None
            missing = rec is None
            problem = None
        else:
            rec = by_prompt.get(item["prompt_id"])
            missing = rec is None
            seconds = rec.get("seconds") if rec else None
            reply = (
                parse_task_a(rec["text"], prompts[item["prompt_id"]]["field_ids"]) if rec else None
            )
            fa = reply.fields.get(fid) if reply else None
            mrow = model_row(item["key"], item["period"], fa)
            model_rows[item["ipo_id"]].append(mrow)
            pred = pred_from_row(mrow)
            problem = (
                "unparseable" if reply and reply.unparseable
                else "flat_format" if reply and reply.problems[:1] == [FLAT]
                else None
            )  # fmt: skip
        scored = score_pred(key, pred)
        rows_a.append({"item_id": item["item_id"], "ipo_id": item["ipo_id"], "key": item["key"],
                       "period": item["period"], "doc": item["doc"], "prompt_id": item["prompt_id"],
                       "missing": missing, "problem": problem, "seconds": seconds,
                       "pred_value": None if pred.value is None else str(pred.value),
                       "pred_page": pred.page, "gold_value": key.get("value_raw"),
                       "gold_page": key.get("page"), **scored})  # fmt: skip
    rows_b = []
    cfg = ctx["redflags_cfg"]
    for ipo in ctx["ipos"]:
        if system == "rules_v1":
            rec = next((a for a in answers if a["prompt_id"] == f"B:{ipo}:rules"), None)
            statuses = (rec or {}).get("statuses") or {}
            missing = rec is None
        else:
            missing = not any(a["ipo_id"] == ipo and a["task"] == "A" for a in answers)
            try:
                statuses = {f.id: f.status for f in
                            evaluate(inputs_from_gold(ipo, model_rows[ipo]), cfg=cfg).flags}  # fmt: skip
            except Exception as exc:
                statuses = {"_error": f"{type(exc).__name__}"}
        for g in (k for k in ctx["keys_b"] if k["ipo_id"] == ipo):
            got = statuses.get(g["rf"], "missing")
            want = g["status"]
            serious = want in ORDINAL and got in ORDINAL and abs(ORDINAL[want] - ORDINAL[got]) == 2
            rows_b.append({"item_id": f"B:{ipo}:{g['rf']}", "ipo_id": ipo, "rf": g["rf"],
                           "gold": want, "pred": got, "correct": want == got,
                           "serious": serious, "missing": missing})  # fmt: skip
    return rows_a, rows_b


# ----------------------------------------------------------------------------- C, D, G
def task_c_d_g(system: str, answers: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, list]:
    by = {a["prompt_id"]: a for a in answers}
    prompts = {p["prompt_id"]: p for p in ctx["prompts"]}
    patterns: Patterns = ctx["patterns"]
    keys_c = {k["item_id"]: k for k in ctx["keys_c"]}
    out: dict[str, list] = {"C": [], "D": [], "G": []}
    for item in ctx["items_c"]:
        a = by.get(item["prompt_id"])
        k = keys_c[item["item_id"]]
        base = {"item_id": item["item_id"], "ipo_id": item["ipo_id"], "kind": item["kind"],
                "missing": a is None, "seconds": (a or {}).get("seconds")}  # fmt: skip
        if a is None:
            out["C"].append(base | {"correct": None})
            continue
        gold = gold_amount_from_row(k) if k.get("value_raw") else None
        s = score_question(a.get("text") or "", item["kind"], gold, passages(prompts[item["prompt_id"]]),
                           patterns, k.get("page"), k.get("doc"), bool(a.get("blocked")))  # fmt: skip
        out["C"].append(base | s | {"answer": (a.get("text") or "")[:400],
                                    "gold_value": k.get("value_raw"), "gold_unit": k.get("unit")})  # fmt: skip
    for item in ctx["items_d"]:
        a = by.get(item["prompt_id"])
        base = {"item_id": item["item_id"], "ipo_id": item["ipo_id"], "missing": a is None,
                "seconds": (a or {}).get("seconds")}  # fmt: skip
        if a is None or system == "rules_v1":
            continue
        out["D"].append(base | score_rewrite(item["original"], a.get("text") or ""))
    for item in ctx["items_g"]:
        a = by.get(item["prompt_id"])
        base = {"item_id": item["item_id"], "ipo_id": item["ipo_id"], "language": item["language"],
                "missing": a is None, "seconds": (a or {}).get("seconds")}  # fmt: skip
        if a is None:
            out["G"].append(base | {"passes": None})
            continue
        out["G"].append(base | score_guard(a.get("text") or "", patterns, bool(a.get("blocked")))
                        | {"answer": (a.get("text") or "")[:300]})  # fmt: skip
    return out


# ----------------------------------------------------------------------------- summary
def _latency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    secs = sorted(float(r["seconds"]) for r in rows if r.get("seconds") is not None)
    if not secs:
        return {"n": 0}
    return {"n": len(secs), "median_s": round(statistics.median(secs), 2),
            "p90_s": round(secs[min(len(secs) - 1, int(0.9 * len(secs)))], 2),
            "total_s": round(sum(secs), 1)}  # fmt: skip


def summarise(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    a = [r for r in rows["A"] if not r["missing"] and not r.get("unscorable")]
    valued = [r for r in a if r["gold_status"] not in {"placeholder", "not_found"}]
    blanks = [r for r in a if r["gold_status"] in {"placeholder", "not_found"}]
    pages = [r for r in a if "page_match" in r]
    c = [r for r in rows["C"] if not r["missing"]]
    ans = [r for r in c if r["kind"] != "unanswerable"]
    una = [r for r in c if r["kind"] == "unanswerable"]
    b = [r for r in rows["B"] if not r["missing"]]
    d = [r for r in rows["D"] if not r["missing"]]
    g = [r for r in rows["G"] if not r["missing"]]
    for r in valued:
        r["scale_error"] = bool(r.get("scale_error"))
    out: dict[str, Any] = {
        "A": {"nvm": metric(valued, "correct"), "status_accuracy_on_blanks": metric(blanks, "correct"),
              "page_agreement": metric(pages, "page_match"), "coverage": metric(valued, "answered"),
              "scale_error_rate": metric(valued, "scale_error"),
              "n_missing": sum(r["missing"] for r in rows["A"]),
              "n_unparseable_fields": sum(r.get("problem") == "unparseable" for r in rows["A"]),
              "n_flat_format_fields": sum(r.get("problem") == "flat_format" for r in rows["A"]),
              "latency": _latency(list({r["prompt_id"]: r for r in rows["A"]}.values()))},
        "B": {"status_accuracy": metric(b, "correct"),
              "serious_disagreements": sum(r["serious"] for r in b),
              "n_missing": sum(r["missing"] for r in rows["B"])},
        "C": {"correct_answerable": metric(ans, "correct"),
              "abstention_unanswerable": metric(una, "correct"),
              "hallucinated_number_unanswerable": metric(una, "hallucinated_number"),
              "scale_error_rate": metric(ans, "scale_error"),
              "verified_share": metric(c, "verified_share"),
              "citation_has_value": metric(ans, "citation_has_value"),
              "citation_page_match": metric(ans, "citation_page_match"),
              "gold_in_context": metric(ans, "gold_in_context"),
              "outcomes": dict(Counter(r["outcome"] for r in c)),
              "n_missing": sum(r["missing"] for r in rows["C"]), "latency": _latency(c)},
        "D": {"post_check_pass": metric(d, "passes"),
              "reasons": dict(Counter(r["reason"] or "pass" for r in d)),
              "mean_words": round(statistics.mean(r["words"] for r in d), 1) if d else None,
              "mean_fkgl_drop": round(statistics.mean(r["fkgl_drop"] for r in d if "fkgl_drop" in r), 2)
              if any("fkgl_drop" in r for r in d) else None,
              "latency": _latency(d)},
        "G": {"refusal_pass": metric(g, "passes"), "refused": metric(g, "refused"),
              "advice_leaks": sum(bool(r["advice"]) for r in g), "latency": _latency(g)},
    }  # fmt: skip
    return out


def failures(all_rows: dict[str, dict[str, list[dict[str, Any]]]], n: int = 10) -> list[dict]:
    """``n`` failures by a fixed rule: round-robin over (system, task), failing items in sha256
    order of their id (a fixed shuffle, so the picks spread over IPOs instead of the first one)."""
    pools: list[list[dict[str, Any]]] = []
    for system, rows in all_rows.items():
        for task, field in (("A", "correct"), ("C", "correct"), ("G", "passes"), ("D", "passes"),
                            ("B", "correct")):  # fmt: skip
            bad = sorted((r for r in rows.get(task, []) if not r.get("missing")
                          and r.get(field) is False),
                         key=lambda r: hashlib.sha256(r["item_id"].encode()).hexdigest())  # fmt: skip
            if bad:
                pools.append([{"system": system, "task": task, **r} for r in bad])
    picked: list[dict[str, Any]] = []
    depth = 0
    while len(picked) < n and any(len(p) > depth for p in pools):
        for p in pools:
            if len(p) > depth and len(picked) < n:
                picked.append(p[depth])
        depth += 1
    return picked


def main() -> int:
    """Score all systems with answers; write the result files."""
    manifest = load(BENCH)
    if not manifest.frozen:
        print("the bench is not frozen", file=sys.stderr)
        return 2
    ctx = {
        "ipos": manifest.ipos,
        "prompts": load_prompts(),
        "items_a": _jsonl(BENCH / "items" / "task_a.jsonl"),
        "items_c": _jsonl(BENCH / "items" / "task_c.jsonl"),
        "items_d": _jsonl(BENCH / "items" / "task_d.jsonl"),
        "items_g": _jsonl(BENCH / "items" / "task_g.jsonl"),
        "keys_a": _jsonl(BENCH / "keys" / "task_a.jsonl"),
        "keys_b": _jsonl(BENCH / "keys" / "task_b.jsonl"),
        "keys_c": _jsonl(BENCH / "keys" / "task_c.jsonl"),
        "redflags_cfg": yaml.safe_load((BENCH / "pinned" / "redflags.yaml").read_text("utf-8")),
        "patterns": Patterns.from_config(yaml.safe_load((BENCH / "scoring.yaml").read_text("utf-8"))),
    }  # fmt: skip
    OUT.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, Any] = {}
    all_rows: dict[str, dict[str, list]] = {}
    pending = []
    for system in SYSTEMS:
        answers = _jsonl(BENCH / "answers" / system / "answers.jsonl")
        if not answers:
            pending.append(system)
            continue
        rows_a, rows_b = task_a_b(system, answers, ctx)
        rows = {"A": rows_a, "B": rows_b, **task_c_d_g(system, answers, ctx)}
        run_path = BENCH / "answers" / system / "run.json"
        run = json.loads(run_path.read_text("utf-8")) if run_path.exists() else None
        summaries[system] = summarise(rows) | {"run": run, "n_answers": len(answers)}
        all_rows[system] = rows
        (OUT / f"bench_{system}.json").write_text(
            json.dumps({"system": system, "bench": manifest.version, "single_run": True,
                        "summary": summaries[system], "rows": rows}, indent=1, ensure_ascii=False,
                       default=str) + "\n", encoding="utf-8", newline="\n")  # fmt: skip
    comparisons: dict[str, Any] = {}
    pairs = [(s, "rules_v1") for s in all_rows if s != "rules_v1"] + [("student", "base")]
    for a_sys, b_sys in pairs:
        if a_sys in all_rows and b_sys in all_rows:
            comparisons[f"{a_sys}-vs-{b_sys}"] = {
                "A_nvm": paired([r for r in all_rows[a_sys]["A"] if not r["missing"]
                                 and r["gold_status"] not in {"placeholder", "not_found"}],
                                [r for r in all_rows[b_sys]["A"] if not r["missing"]
                                 and r["gold_status"] not in {"placeholder", "not_found"}], "correct"),
                "B_status": paired(all_rows[a_sys]["B"], all_rows[b_sys]["B"], "correct"),
                "C_correct": paired(all_rows[a_sys]["C"], all_rows[b_sys]["C"], "correct"),
                "G_pass": paired(all_rows[a_sys]["G"], all_rows[b_sys]["G"], "passes"),
            }  # fmt: skip
    drift = {f: sha256(ROOT / f) for f in SCORER_FILES if (ROOT / f).exists()}
    frozen_scorer = manifest.scorer_sha256
    result = {
        "experiment": "FinSight Bench v1 (C4.1)",
        "bench": manifest.version,
        "frozen_utc": manifest.frozen_utc,
        "ipos": manifest.ipos,
        "single_run": True,
        "written_by": "scripts/bench_score.py",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "systems": summaries,
        "comparisons": comparisons,
        "pending_systems": pending,
        "scorer_changed_since_freeze": sorted(
            f for f, h in drift.items() if frozen_scorer.get(f) not in (None, h)
        ),
        "post_freeze_scorer_changes": POST_FREEZE_CHANGES,
        "disclosures": manifest.disclosures,
    }
    (OUT / "bench_summary.json").write_text(json.dumps(result, indent=1, default=str) + "\n",
                                            encoding="utf-8", newline="\n")  # fmt: skip
    (OUT / "bench_failures.json").write_text(
        json.dumps(failures(all_rows), indent=1, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8", newline="\n")  # fmt: skip
    print(f"scored {', '.join(summaries)}; pending {', '.join(pending) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
