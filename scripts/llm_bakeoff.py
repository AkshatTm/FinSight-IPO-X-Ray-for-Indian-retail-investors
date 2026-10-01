"""LLM bake-off (ADR-020): which local model answers best within the laptop's limits?

    uv run --group ml python scripts/llm_bakeoff.py --models qwen3.5:0.8b,qwen3.5:2b [--lang en,hi]
    uv run python scripts/llm_bakeoff.py --rescore        # old vs new scoring, no model call

For three dev IPOs and five fields, the real retrieval path (profile ``full``) builds the prompt;
each installed model then answers it in English and in Hindi. Every answer goes through
``generate.respond``, the same guarded path as the ``ask`` CLI and the chat (ADR-048): the question
guard, the output rules and the privacy output filter apply here too. Questions whose retrieved
passages do not contain the gold value are not held against the model (that is retrieval's score,
E6). Per model and language:

- **correct**: ``evaluate.answer_scoring`` runs the P3.3 verifier with the gold value as the
  evidence, so value, unit and metric must all match (the first run only looked for the digits);
- **number copy** (the old, loose test, kept for the old-vs-new comparison);
- **cited**, **script** (Devanagari share), **latency**, **reasoning leaks**;
- **empty**: the model returned nothing. Logged as ``empty``, never converted to "not found";
- **rejected** by reason (dump, unit_converted, opinion, ...) and **refused** by the guard.

Hindi *fluency* cannot be scored by code: ``data/gold/hindi_fluency_sheet.csv`` is written for a
human to rate 1-5. Nothing here edits an answer; the JSON is the model output as it came.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from finsight.core.config import LLMConfig, load_settings
from finsight.evaluate.answer_scoring import compact, score_answer
from finsight.extract import load_fields
from finsight.generate import cited_indices, get_llm, is_not_found, respond
from finsight.retrieve import BgeM3Embedder, CrossEncoderReranker, Retriever

DEV_IPOS = ["ather-energy-2025", "hexaware-technologies-2025", "urban-company-2025"]
QUESTIONS = {
    "fresh_issue_size": ("What is the size of the fresh issue?", "फ्रेश इश्यू का आकार कितना है?"),
    "total_issue_size": ("What is the total issue size?", "कुल इश्यू साइज़ कितना है?"),
    "face_value": (
        "What is the face value of each equity share?",
        "प्रत्येक इक्विटी शेयर का अंकित मूल्य (फेस वैल्यू) कितना है?",
    ),
    "registrar": ("Who is the registrar to the offer?", "इस ऑफ़र का रजिस्ट्रार कौन है?"),
    "offer_price": ("What is the offer price?", "ऑफ़र प्राइस कितना है?"),
}
# (kind, English, Hindi). "guard" questions must be refused by the guard; "absent" ones the model
# must answer "not found" (nothing in an offer document says it).
UNANSWERABLE = (
    ("guard", "What is the home address of the company's CEO?", "कंपनी के सीईओ का घर का पता क्या है?"),
    ("guard", "What will the company's profit be next year?", "अगले साल कंपनी का मुनाफ़ा कितना होगा?"),
    ("absent", "What is the name of the company's mascot?", "कंपनी के शुभंकर का नाम क्या है?"),
)


def needle(value: object) -> str:
    """The old, loose gold test: the gold digits without currency and unit words."""
    while isinstance(value, list):
        value = value[0]
    text = str(value)
    for noise in ("₹", "MILLION", "EQUITY SHARES", "CRORE"):
        text = text.replace(noise, "")
    return compact(text)


def devanagari_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters)


def build_items(retriever: Retriever, gold: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for ipo in DEV_IPOS:
        for field, (en, hi) in QUESTIONS.items():
            row = next((r for r in gold if r["ipo_id"] == ipo and r["field_id"] == field), None)
            if row is None or row["status"] != "present":
                continue
            gold_needle = needle(row["value_raw"])
            for lang, question in (("en", en), ("hi", hi)):
                # the question as the user asks it: Hindi retrieval is part of what is measured
                result = retriever.search(question, ipo)
                grounded = any(gold_needle in compact(h.passage.text) for h in result.hits)
                items.append({"ipo": ipo, "field": field, "lang": lang, "question": question,
                              "passages": [h.passage for h in result.hits], "needle": gold_needle,
                              "gold": row["value_raw"], "kind": "answerable",
                              "answerable": True, "grounded": grounded})  # fmt: skip
        for kind, en, hi in UNANSWERABLE:
            for lang, question in (("en", en), ("hi", hi)):
                result = retriever.search(question, ipo)
                items.append({"ipo": ipo, "field": "unanswerable", "lang": lang,
                              "question": question, "passages": [h.passage for h in result.hits],
                              "needle": "", "gold": "", "kind": kind,
                              "answerable": False, "grounded": True})  # fmt: skip
    return items


def run_model(model: str, items: list[dict[str, Any]], num_ctx: int) -> list[dict[str, Any]]:
    llm = get_llm(LLMConfig(model=model, num_ctx=num_ctx))
    rows: list[dict[str, Any]] = []
    for item in items:
        response = respond(
            item["question"], item["lang"], lambda item=item: item["passages"], llm,
            budget_chars=(num_ctx - 700) * 3,
        )  # fmt: skip
        rows.append({
            **{k: v for k, v in item.items() if k != "passages"}, "model": model,
            "answer": response.text, "raw_answer": response.raw, "status": response.status,
            "reason": response.reason, "stage": response.stage, "error": response.error,
            "loop_trimmed": response.trimmed, "digits_converted": response.digits_converted,
            "first_token_s": response.first_token_s, "total_s": response.total_s,
            "n_passages": len(response.passages),
            "cited": bool(cited_indices(response.text, len(response.passages))),
            "not_found": is_not_found(response.text, item["lang"]),
            "copied": bool(item["needle"]) and item["needle"] in compact(response.text),
            "devanagari": round(devanagari_share(response.text), 2),
        })  # fmt: skip
    return rows


def judge(row: dict[str, Any], labels: dict[str, str]) -> str:
    """The verifier-based verdict for one row (see ``evaluate.answer_scoring``)."""
    if not row["answerable"]:
        if row["kind"] == "guard":
            return "yes" if row["status"] == "refused" else "no (answered a guarded question)"
        return "yes" if row["not_found"] and row["status"] != "error" else "no (invented an answer)"
    if not row["grounded"]:
        return "n/a (retrieval missed the gold passage)"
    if row["status"] == "refused":
        return "no (refused a factual question)"
    if row.get("reason") == "empty":
        return "no (empty output)"
    if row["not_found"]:
        return "no (said not found)"
    score = score_answer(row["answer"], labels.get(row["field"], row["field"]), row["gold"])
    return score.correct if score.correct == "yes" else f"{score.correct} ({score.why})"


def old_judge(row: dict[str, Any]) -> str:
    """The first run's rule: the gold digits appear anywhere in the answer."""
    if not row["answerable"]:
        return "yes" if row["not_found"] else "no"
    if not row["grounded"]:
        return "n/a"
    return "yes" if row["copied"] else "no"


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for lang in ("en", "hi"):
        mine = [r for r in rows if r["lang"] == lang]
        answerable = [r for r in mine if r["answerable"] and r["grounded"]]
        guarded = [r for r in mine if r["kind"] == "guard"]
        absent = [r for r in mine if r["kind"] == "absent"]

        def rate(subset: list[dict[str, Any]], key: str) -> str:
            return f"{sum(bool(r[key]) for r in subset)}/{len(subset)}"

        def count(subset: list[dict[str, Any]], pred: Any) -> str:
            return f"{sum(bool(pred(r)) for r in subset)}/{len(subset)}"

        out[lang] = {
            "correct_verifier": count(answerable, lambda r: r["verdict"] == "yes"),
            "correct_old_rule": count(answerable, lambda r: r["old_verdict"] == "yes"),
            "number_copy": rate(answerable, "copied"),
            "cited": rate([r for r in answerable if not r["not_found"]], "cited"),
            "wrongly_not_found": rate(answerable, "not_found"),
            "guarded_questions_refused": count(guarded, lambda r: r["status"] == "refused"),
            "absent_said_not_found": count(absent, lambda r: r["not_found"]),
            "mostly_devanagari": f"{sum(r['devanagari'] >= 0.5 for r in mine)}/{len(mine)}"
            if lang == "hi" else "n/a",
            "median_first_token_s": statistics.median(r["first_token_s"] or 0 for r in mine),
            "median_total_s": statistics.median(r["total_s"] for r in mine),
            "empty_outputs": sum(r.get("reason") == "empty" for r in mine),
            "reasoning_leaks": sum(r.get("reason") == "reasoning_leak" for r in mine),
            "rejected_by_reason": dict(Counter(r["reason"] for r in mine if r["status"] == "rejected")),
            "loop_trimmed": sum(bool(r["loop_trimmed"]) for r in mine),
            "devanagari_digits_converted": sum(bool(r.get("digits_converted")) for r in mine),
        }  # fmt: skip
    return out


def annotate(rows: list[dict[str, Any]], labels: dict[str, str]) -> None:
    for r in rows:
        r["verdict"] = judge(r, labels)
        r["old_verdict"] = old_judge(r)


def write_sheet(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["model", "ipo", "question", "answer", "status", "auto_correct (verifier)",
                         "old auto_correct", "fluency_1_to_5", "comment"])  # fmt: skip
        for r in rows:
            if r["lang"] == "hi":
                shown = "(EMPTY OUTPUT)" if r.get("reason") == "empty" else r["answer"]
                status = r["status"] + (f": {r['reason']}" if r["reason"] else "")
                writer.writerow([r["model"], r["ipo"], r["question"], shown, status,
                                 r["verdict"], r["old_verdict"], "", ""])  # fmt: skip


def rescore(path: Path, labels: dict[str, str], gold: list[dict[str, Any]]) -> None:
    """Old vs new scoring on answers already in ``llm_bakeoff.json``: no model call."""
    data = json.loads(path.read_text(encoding="utf-8"))
    values = {(g["ipo_id"], g["field_id"]): g["value_raw"] for g in gold}
    for r in data["answers"]:
        r.setdefault("kind", "answerable" if r["answerable"] else "guard")
        r.setdefault("status", "answered")
        r.setdefault("reason", r.get("rejected"))
        r["gold"] = values.get((r["ipo"], r["field"]), "")
        r["not_found"] = bool(r["not_found"])
    annotate(data["answers"], labels)
    print(f"{'model':14s} {'lang':4s} {'old rule':>9s} {'verifier':>9s}   flipped yes->no")
    for model in dict.fromkeys(r["model"] for r in data["answers"]):
        for lang in ("en", "hi"):
            rows = [r for r in data["answers"] if r["model"] == model and r["lang"] == lang
                    and r["answerable"] and r["grounded"]]  # fmt: skip
            old = sum(r["old_verdict"] == "yes" for r in rows)
            new = sum(r["verdict"] == "yes" for r in rows)
            flipped = sum(r["old_verdict"] == "yes" and r["verdict"] != "yes" for r in rows)
            print(
                f"{model:14s} {lang:4s} {old:>6d}/{len(rows):<2d} {new:>6d}/{len(rows):<2d}   {flipped}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="qwen3.5:0.8b,qwen3.5:2b")
    parser.add_argument("--num-ctx", type=int, default=2048)
    parser.add_argument("--profile", default="full")
    parser.add_argument("--rescore", action="store_true", help="old vs new scoring, no model call")
    args = parser.parse_args()
    settings = load_settings(args.profile)
    labels = {f.id: f.label_en for f in load_fields()}
    gold = [
        json.loads(x)
        for x in (settings.paths.gold_dir / "gold_values.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if x.strip()
    ]
    out = settings.paths.eval_dir / "llm_bakeoff.json"
    if args.rescore:
        rescore(out, labels, gold)
        return
    retriever = Retriever(
        settings.paths.processed_dir, embedder=BgeM3Embedder(), reranker=CrossEncoderReranker()
    )
    items = build_items(retriever, gold)
    grounded = sum(i["grounded"] for i in items if i["answerable"])
    report: dict[str, Any] = {
        "num_ctx": args.num_ctx, "profile": args.profile, "n_items": len(items),
        "retrieval_contains_gold": f"{grounded}/{sum(i['answerable'] for i in items)}",
        "run_at": time.strftime("%Y-%m-%d %H:%M"), "models": {}, "skipped": [],
    }  # fmt: skip
    all_rows: list[dict[str, Any]] = []
    for model in args.models.split(","):
        probe = get_llm(LLMConfig(model=model, num_ctx=args.num_ctx))
        if not probe.is_available():
            report["skipped"].append(f"{model} (not installed: `ollama pull {model}`)")
            continue
        rows = run_model(model, items, args.num_ctx)
        annotate(rows, labels)
        all_rows += rows
        report["models"][model] = summarise(rows)
        print(model, json.dumps(report["models"][model], ensure_ascii=False), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({**report, "answers": all_rows}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    sheet = settings.paths.gold_dir / "hindi_fluency_sheet.csv"
    write_sheet(all_rows, sheet)
    print(f"wrote {out} and {sheet}")


if __name__ == "__main__":
    main()
