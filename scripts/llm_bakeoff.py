"""LLM bake-off (ADR-020): which local model answers best within the laptop's limits?

    uv run --group ml python scripts/llm_bakeoff.py --models qwen3.5:0.8b,qwen3.5:2b [--lang en,hi]

For three dev IPOs and five fields, the real retrieval path (profile ``full``) builds the prompt;
each installed model then answers it in English and in Hindi. Questions whose retrieved passages
do not contain the gold value are not held against the model (that is retrieval's score, E6);
two unanswerable questions per language test "not found". Measured per model and language:

- **number copy**: the gold value appears in the answer exactly as written (digits and name);
- **cited**: at least one valid ``[n]`` marker; **grounded not-found**: says so when it should;
- **script**: for Hindi, answers mostly in Devanagari (a model that copies English fails here);
- **latency**: median seconds to the first token and per answer; **reasoning leaks**.

Hindi *fluency* cannot be scored by code: ``data/gold/hindi_fluency_sheet.csv`` is written for
Akshat to rate 1-5. Nothing here edits an answer; the JSON is the model output as it came.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from typing import Any

from finsight.core.config import LLMConfig, load_settings
from finsight.generate import (
    LLMUnavailable,
    LoopDetector,
    ReasoningLeak,
    build_prompt,
    cited_indices,
    clean_answer,
    get_llm,
    is_not_found,
)
from finsight.retrieve import BgeM3Embedder, CrossEncoderReranker, Retriever
from finsight.retrieve.evaluate import compact

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
UNANSWERABLE = (
    ("What is the home address of the company's CEO?", "कंपनी के सीईओ का घर का पता क्या है?"),
    ("What will the company's profit be next year?", "अगले साल कंपनी का मुनाफ़ा कितना होगा?"),
)
_NOISE = ("₹", "MILLION", "EQUITY SHARES", "CRORE")


def needle(value: object) -> str:
    while isinstance(value, list):
        value = value[0]
    text = str(value)
    for noise in _NOISE:
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
            result = retriever.search(en, ipo)
            gold_needle = needle(row["value_raw"])
            grounded = any(gold_needle in compact(h.passage.text) for h in result.hits)
            for lang, question in (("en", en), ("hi", hi)):
                items.append({"ipo": ipo, "field": field, "lang": lang, "question": question,
                              "passages": [h.passage for h in result.hits], "needle": gold_needle,
                              "answerable": True, "grounded": grounded})  # fmt: skip
        for en, hi in UNANSWERABLE:
            result = retriever.search(en, ipo)
            for lang, question in (("en", en), ("hi", hi)):
                items.append({"ipo": ipo, "field": "unanswerable", "lang": lang,
                              "question": question, "passages": [h.passage for h in result.hits],
                              "needle": "", "answerable": False, "grounded": True})  # fmt: skip
    return items


def run_model(model: str, items: list[dict[str, Any]], num_ctx: int) -> list[dict[str, Any]]:
    llm = get_llm(LLMConfig(model=model, num_ctx=num_ctx))
    rows: list[dict[str, Any]] = []
    for item in items:
        prompt = build_prompt(
            item["question"], item["passages"], item["lang"], budget_chars=(num_ctx - 700) * 3
        )
        started = time.perf_counter()
        first: float | None = None
        pieces: list[str] = []
        error = None
        loop = LoopDetector()
        try:
            for piece in llm.stream(prompt.text, max_tokens=300, temperature=0.2,
                                    language=item["lang"]):  # fmt: skip
                first = first or time.perf_counter()
                pieces.append(piece)
                if loop.feed(piece):
                    break
        except ReasoningLeak as exc:
            error = f"reasoning_leak: {exc}"
        raw = "".join(pieces)
        cleaned = clean_answer(raw, prompt.passages, item["lang"])
        answer = cleaned.text
        ended = time.perf_counter()
        rows.append({**{k: v for k, v in item.items() if k != "passages"},
                     "model": model, "answer": answer, "raw_answer": raw,
                     "rejected": cleaned.reason, "loop_trimmed": cleaned.trimmed, "error": error,
                     "first_token_s": round((first or ended) - started, 2),
                     "total_s": round(ended - started, 2),
                     "n_passages": len(prompt.passages),
                     "cited": bool(cited_indices(answer, len(prompt.passages))),
                     "not_found": is_not_found(answer, item["lang"]),
                     "copied": bool(item["needle"]) and item["needle"] in compact(answer),
                     "devanagari": round(devanagari_share(answer), 2)})  # fmt: skip
    return rows


def auto_correct(row: dict[str, Any]) -> str:
    """Pre-filled from the gold value, never typed by hand: Akshat confirms or overrides."""
    if not row["answerable"]:
        return "yes" if row["not_found"] else "no (answered an unanswerable question)"
    if not row["grounded"]:
        return "n/a (retrieval missed the gold passage)"
    if row["copied"]:
        return "yes (gold value copied exactly)"
    return "no (not found)" if row["not_found"] else "no (gold value missing or altered)"


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for lang in ("en", "hi"):
        mine = [r for r in rows if r["lang"] == lang]
        answerable = [r for r in mine if r["answerable"] and r["grounded"]]
        unanswerable = [r for r in mine if not r["answerable"]]

        def rate(subset: list[dict[str, Any]], key: str) -> str:
            return f"{sum(bool(r[key]) for r in subset)}/{len(subset)}"

        out[lang] = {
            "number_copy": rate(answerable, "copied"),
            "cited": rate([r for r in answerable if not r["not_found"]], "cited"),
            "wrongly_not_found": rate(answerable, "not_found"),
            "unanswerable_said_not_found": rate(unanswerable, "not_found"),
            "mostly_devanagari": f"{sum(r['devanagari'] >= 0.5 for r in mine)}/{len(mine)}"
            if lang == "hi" else "n/a",
            "median_first_token_s": statistics.median(r["first_token_s"] for r in mine),
            "median_total_s": statistics.median(r["total_s"] for r in mine),
            "reasoning_leaks": sum(bool(r["error"]) for r in mine),
            "rejected_outputs": sum(bool(r["rejected"]) for r in mine),
            "loop_trimmed": sum(bool(r["loop_trimmed"]) for r in mine),
        }  # fmt: skip
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="qwen3.5:0.8b,qwen3.5:2b")
    parser.add_argument("--num-ctx", type=int, default=2048)
    parser.add_argument("--profile", default="full")
    args = parser.parse_args()
    settings = load_settings(args.profile)
    retriever = Retriever(
        settings.paths.processed_dir, embedder=BgeM3Embedder(), reranker=CrossEncoderReranker()
    )
    gold = [
        json.loads(x)
        for x in (settings.paths.gold_dir / "gold_values.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if x.strip()
    ]
    items = build_items(retriever, gold)
    grounded = sum(i["grounded"] for i in items if i["answerable"])
    report: dict[str, Any] = {
        "num_ctx": args.num_ctx, "profile": args.profile, "n_items": len(items),
        "retrieval_contains_gold": f"{grounded}/{sum(i['answerable'] for i in items)}",
        "models": {}, "skipped": [],
    }  # fmt: skip
    all_rows: list[dict[str, Any]] = []
    for model in args.models.split(","):
        probe = get_llm(LLMConfig(model=model, num_ctx=args.num_ctx))
        if not probe.is_available():
            report["skipped"].append(f"{model} (not installed: `ollama pull {model}`)")
            continue
        try:
            rows = run_model(model, items, args.num_ctx)
        except LLMUnavailable as exc:
            report["skipped"].append(f"{model} ({exc})")
            continue
        all_rows += rows
        report["models"][model] = summarise(rows)
        print(model, json.dumps(report["models"][model], ensure_ascii=False), flush=True)
    out = settings.paths.eval_dir / "llm_bakeoff.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({**report, "answers": all_rows}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    sheet = settings.paths.gold_dir / "hindi_fluency_sheet.csv"
    with sheet.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["model", "ipo", "question", "answer", "auto_correct", "fluency_1_to_5", "comment"]
        )
        for r in all_rows:
            if r["lang"] == "hi":
                writer.writerow([r["model"], r["ipo"], r["question"], r["answer"],
                                 auto_correct(r), "", ""])  # fmt: skip
    print(f"wrote {out} and {sheet}")


if __name__ == "__main__":
    main()
