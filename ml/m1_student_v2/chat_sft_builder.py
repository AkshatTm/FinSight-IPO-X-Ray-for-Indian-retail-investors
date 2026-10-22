# ruff: noqa: E501
"""Chat SFT data generator (scripted same-section near-miss unanswerables + numkeep filter + rewrite mixer).

Implements Task AR-04 (P-1 approved):
1. Renders prompts strictly with the frozen `ml/handoff/data/student_chat_template.txt` (EN) and
   `ml/handoff/data/student_chat_template_hi.txt` (HI).
2. Builds ~1,500 scripted same-section hard near-miss unanswerable SFT examples over multi-number
   passages from non-excluded `train`/`dev` IPOs, targeting the exact abstain string:
   - EN: `"I could not find this in the document."`
   - HI: `"मुझे यह जानकारी दस्तावेज़ में नहीं मिली।"`
3. Filters teacher-generated (`Gemma-4-31B-it`) answerable numeric Q&A (~1,000) and adversarial
   near-miss unanswerables (~500) using `ml/handoff/eval/numkeep.py` (`finsight_lite.numcheck.unmatched_numbers`)
   plus `[n]` citation and <=120-word checks.
4. Mixes the new chat SFT rows with the existing risk-rewrite SFT pairs (`student_v1_train.jsonl.gz`
   10,362 rows / `student_v1_dev.jsonl.gz` 529 rows) so rewrite quality does not regress.

Zero product imports (`src/finsight/...` is never imported).
"""

from __future__ import annotations

import argparse
import gzip
import json
import pathlib
import random
import re
import sys
from collections import Counter, defaultdict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
HANDOFF_DIR = ROOT / "ml" / "handoff"
VENDOR_DIR = HANDOFF_DIR / "eval" / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from finsight_lite.numcheck import unmatched_numbers  # noqa: E402

ABSTAIN_EN = "I could not find this in the document."
ABSTAIN_HI = "मुझे यह जानकारी दस्तावेज़ में नहीं मिली।"

_CITATION_RE = re.compile(r"\[\d+\]")
_NUMBER_HINT_RE = re.compile(r"(?:₹|rs\.?|inr|\d+(?:\.\d+)?\s*(?:%|million|crore|lakh))", re.I)

# Same-section near-miss question templates grouped by risk category.
# Each entry is: (question_en, question_hi, forbidden_substrings_in_passages)
NEAR_MISS_TEMPLATES: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
    "financial": [
        (
            "What was the company's net cash flow from operating activities in the latest full financial year?",
            "नवीनतम पूर्ण वित्तीय वर्ष में कंपनी का परिचालन गतिविधियों से शुद्ध नकदी प्रवाह (net cash flow from operating activities) कितना था?",
            ("cash flow from operating", "operating activities", "परिचालन गतिविधियों"),
        ),
        (
            "What was the company's net worth at the end of the latest full financial year?",
            "नवीनतम पूर्ण वित्तीय वर्ष के अंत में कंपनी की नेट वर्थ (net worth) कितनी थी?",
            ("net worth", "नेट वर्थ"),
        ),
        (
            "What revenue from operations does the company forecast for the financial year 2030?",
            "वित्तीय वर्ष 2030 के लिए कंपनी परिचालन से कितने राजस्व (revenue from operations) का अनुमान लगाती है?",
            ("2030", "forecast for the financial year 2030"),
        ),
        (
            "What was the company's restated profit or loss after tax in Fiscal 2017?",
            "वित्तीय वर्ष 2017 में कर के बाद कंपनी का पुनर्गठित लाभ या हानि (restated profit or loss after tax) क्या था?",
            ("2017", "fiscal 2017", "fy17", "fy 2017"),
        ),
        (
            "What was the company's return on net worth (RoNW) in the latest full financial year?",
            "नवीनतम पूर्ण वित्तीय वर्ष में कंपनी का रिटर्न ऑन नेट वर्थ (RoNW) कितना था?",
            ("return on net worth", "ronw"),
        ),
    ],
    "debt_liquidity": [
        (
            "What was the exact interest rate per annum charged on the company's unsecured commercial paper in Fiscal 2024?",
            "वित्तीय वर्ष 2024 में कंपनी के असुरक्षित कमर्शियल पेपर (commercial paper) पर प्रति वर्ष सटीक ब्याज दर क्या थी?",
            ("commercial paper", "कमर्शियल पेपर"),
        ),
        (
            "What was the company's debt-to-equity ratio at the end of Fiscal 2018?",
            "वित्तीय वर्ष 2018 के अंत में कंपनी का ऋण-इक्विटी अनुपात (debt-to-equity ratio) क्या था?",
            ("2018", "debt-to-equity", "debt equity ratio"),
        ),
        (
            "How much money from the Fresh Issue is allocated specifically to redeeming preference shares?",
            "फ्रेश इश्यू (Fresh Issue) से कितनी राशि विशेष रूप से प्रेफरेंस शेयरों के मोचन (redemption of preference shares) के लिए आवंटित की गई है?",
            ("preference share", "redeeming preference", "redemption of preference"),
        ),
        (
            "What were the company's total borrowings at the end of Fiscal 2016?",
            "वित्तीय वर्ष 2016 के अंत में कंपनी का कुल उधार (total borrowings) कितना था?",
            ("2016", "fiscal 2016", "fy16"),
        ),
    ],
    "legal": [
        (
            "What was the total amount of compounding fees paid by the company to the Enforcement Directorate in Fiscal 2023?",
            "वित्तीय वर्ष 2023 में प्रवर्तन निदेशालय (Enforcement Directorate) को कंपनी द्वारा भुगतान किए गए कंपाउंडिंग शुल्क की कुल राशि क्या थी?",
            ("enforcement directorate", "pmla", "प्रवर्तन निदेशालय"),
        ),
        (
            "How many criminal proceedings are currently pending against the Independent Directors before the Supreme Court of India?",
            "भारत के सर्वोच्च न्यायालय के समक्ष स्वतंत्र निदेशकों (Independent Directors) के विरुद्ध वर्तमान में कितने आपराधिक मामले लंबित हैं?",
            ("supreme court", "independent director", "स्वतंत्र निदेशक"),
        ),
        (
            "What was the arbitral award amount granted against the company by the Singapore International Arbitration Centre?",
            "सिंगापुर इंटरनेशनल आर्बिट्रेशन सेंटर द्वारा कंपनी के विरुद्ध पारित आर्बिट्रल अवार्ड की राशि क्या थी?",
            ("singapore", "siac", "arbitral award"),
        ),
    ],
    "regulatory": [
        (
            "What monetary penalty was imposed on the company by the Competition Commission of India (CCI)?",
            "भारतीय प्रतिस्पर्धा आयोग (CCI) द्वारा कंपनी पर कितना मौद्रिक जुर्माना लगाया गया था?",
            ("competition commission", "cci", "प्रतिस्पर्धा आयोग"),
        ),
        (
            "How much customs duty penalty did the Directorate of Revenue Intelligence levy on the company in Fiscal 2022?",
            "वित्तीय वर्ष 2022 में राजस्व खुफिया निदेशालय (DRI) ने कंपनी पर कितना सीमा शुल्क जुर्माना लगाया?",
            ("directorate of revenue intelligence", "dri", "customs duty penalty"),
        ),
    ],
    "governance": [
        (
            "What is the exact post-Offer shareholding percentage of the Promoter Group after the exercise of the green shoe option?",
            "ग्रीन शू विकल्प (green shoe option) के प्रयोग के बाद प्रमोटर समूह की सटीक पोस्ट-ऑफर शेयरधारिता प्रतिशत क्या है?",
            ("green shoe", "post-offer shareholding", "ग्रीन शू"),
        ),
        (
            "What was the total sitting fee paid to the Chairman of the Audit Committee in Fiscal 2023?",
            "वित्तीय वर्ष 2023 में ऑडिट समिति के अध्यक्ष को भुगतान किया गया कुल सिटिंग शुल्क (sitting fee) कितना था?",
            ("sitting fee", "audit committee", "सिटिंग शुल्क"),
        ),
    ],
    "default": [
        (
            "How much money is the fresh issue raising?",
            "फ्रेश इश्यू (fresh issue) के माध्यम से कितनी राशि जुटाई जा रही है?",
            ("fresh issue", "offer for sale", "net proceeds"),
        ),
        (
            "What is the offer price per equity share?",
            "प्रति इक्विटी शेयर ऑफर मूल्य (offer price) क्या है?",
            ("offer price", "price band", "floor price", "cap price"),
        ),
        (
            "What is the size of the offer for sale?",
            "ऑफर फॉर सेल (offer for sale) का आकार क्या है?",
            ("offer for sale", "selling shareholder", "fresh issue"),
        ),
        (
            "What was the company's share price at the close of its first day of trading on the stock exchange?",
            "स्टॉक एक्सचेंज में कारोबार के पहले दिन के अंत में कंपनी का शेयर मूल्य क्या था?",
            ("first day of trading", "closing price on listing"),
        ),
        (
            "What was the grey market premium for this IPO on the day before it opened?",
            "इस IPO के खुलने से एक दिन पहले इसका ग्रे मार्केट प्रीमियम (grey market premium) क्या था?",
            ("grey market", "gmp"),
        ),
    ],
}


def load_chat_template(lang: str = "en", handoff_dir: pathlib.Path | None = None) -> str:
    base = (handoff_dir or HANDOFF_DIR) / "data"
    fname = "student_chat_template_hi.txt" if lang == "hi" else "student_chat_template.txt"
    return (base / fname).read_text(encoding="utf-8")


def format_passage_blocks(passages: list[dict[str, Any]]) -> str:
    """Format passage dicts into `[n] (RHP page p)\\n<text>` blocks separated by `\\n\\n`."""
    blocks: list[str] = []
    for idx, p in enumerate(passages, start=1):
        doc_type = str(p.get("doc_type") or "RHP").upper()
        page = p.get("page") or p.get("page_start") or 1
        text = " ".join(str(p.get("text") or "").split())
        blocks.append(f"[{idx}] ({doc_type} page {page})\n{text}")
    return "\n\n".join(blocks)


def render_chat_prompt(
    question: str,
    passages: list[dict[str, Any]],
    lang: str = "en",
    handoff_dir: pathlib.Path | None = None,
) -> str:
    """Render the frozen EN or HI chat template with `{{QUESTION}}` (twice) and `{{PASSAGE_BLOCKS}}`."""
    tpl = load_chat_template(lang=lang, handoff_dir=handoff_dir)
    blocks_str = format_passage_blocks(passages)
    q_clean = question.strip()
    rendered = tpl.replace("{{QUESTION}}", q_clean).replace("{{PASSAGE_BLOCKS}}", blocks_str)
    return rendered.strip()


def build_scripted_near_miss_unanswerables(
    risk_rows: list[dict[str, Any]],
    excluded_ipos: set[str],
    target_count: int = 1500,
    seed: int = 42,
    hi_ratio: float = 0.20,
    handoff_dir: pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    """Deterministically build same-section hard near-miss unanswerable SFT rows from non-excluded train/dev passages.

    Every generated example:
    - Uses 2-3 passages from the SAME non-excluded IPO and SAME risk category that contain numbers (`₹`, `%`, etc.).
    - Asks a plausible investor question for that category whose target keywords/period are verified ABSENT from the passages.
    - Maps the assistant response to the exact frozen abstain string (`ABSTAIN_EN` or `ABSTAIN_HI`).
    """
    rng = random.Random(seed)

    by_ipo_cat: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in risk_rows:
        ipo_id = str(r.get("ipo_id") or "").strip()
        if not ipo_id or ipo_id in excluded_ipos or r.get("excluded"):
            continue
        split = str(r.get("split") or r.get("slice") or "train").strip()
        if split not in ("train", "dev"):
            continue
        text = " ".join(str(r.get("text") or "").split())
        if len(text.split()) < 25 or not _NUMBER_HINT_RE.search(text):
            continue
        cat = str(r.get("label") or r.get("category") or "default").strip()
        by_ipo_cat[(ipo_id, cat)].append(
            {
                "risk_id": r.get("risk_id") or r.get("id") or f"{ipo_id}#p",
                "ipo_id": ipo_id,
                "company": r.get("company") or ipo_id,
                "split": split,
                "category": cat,
                "page": int(r.get("page") or r.get("page_start") or 35),
                "doc_type": "RHP",
                "text": text,
            }
        )

    groups = sorted(by_ipo_cat.items(), key=lambda kv: kv[0])
    rng.shuffle(groups)

    out_rows: list[dict[str, Any]] = []
    seen_prompt_hashes: set[tuple[str, str, str]] = set()

    # Pass over groups until target_count is reached (or all valid combinations exhausted)
    for round_idx in range(6):
        if len(out_rows) >= target_count:
            break
        for (ipo_id, cat), passages_pool in groups:
            if len(out_rows) >= target_count:
                break
            if len(passages_pool) < 2:
                continue

            k = min(len(passages_pool), 2 if round_idx % 2 == 0 else 3)
            sampled_passages = rng.sample(passages_pool, k)
            combined_low = " ".join(p["text"] for p in sampled_passages).lower()

            cand_templates = NEAR_MISS_TEMPLATES.get(cat, []) + NEAR_MISS_TEMPLATES["default"]
            rng.shuffle(cand_templates)

            chosen: tuple[str, str, tuple[str, ...]] | None = None
            for q_en, q_hi, forbidden in cand_templates:
                if any(tok in combined_low for tok in forbidden):
                    continue
                sig = (ipo_id, q_en, sampled_passages[0]["risk_id"])
                if sig not in seen_prompt_hashes:
                    chosen = (q_en, q_hi, forbidden)
                    seen_prompt_hashes.add(sig)
                    break

            if chosen is None:
                continue

            use_hi = rng.random() < hi_ratio
            lang = "hi" if use_hi else "en"
            question = chosen[1] if use_hi else chosen[0]
            abstain = ABSTAIN_HI if use_hi else ABSTAIN_EN
            prompt = render_chat_prompt(
                question=question,
                passages=sampled_passages,
                lang=lang,
                handoff_dir=handoff_dir,
            )

            out_rows.append(
                {
                    "id": f"chat_unans_scripted_{len(out_rows) + 1:05d}",
                    "ipo_id": ipo_id,
                    "company": sampled_passages[0]["company"],
                    "split": sampled_passages[0]["split"],
                    "label_source": "rule",
                    "task_type": "chat_unanswerable_scripted",
                    "lang": lang,
                    "question": question,
                    "passages": [p["text"] for p in sampled_passages],
                    "answer": abstain,
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": abstain},
                    ],
                }
            )

    return out_rows


def filter_teacher_chat_rows(
    raw_rows: list[dict[str, Any]],
    excluded_ipos: set[str],
    handoff_dir: pathlib.Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Filter teacher-generated chat rows using `unmatched_numbers` (`numkeep.py`) + citation/length rules."""
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()

    for row in raw_rows:
        ipo_id = str(row.get("ipo_id") or "").strip()
        if not ipo_id or ipo_id in excluded_ipos or row.get("excluded"):
            reasons["excluded_ipo"] += 1
            rejected.append({**row, "reject_reason": "excluded_ipo"})
            continue

        split = str(row.get("split") or row.get("slice") or "train").strip()
        if split not in ("train", "dev"):
            reasons["invalid_split"] += 1
            rejected.append({**row, "reject_reason": "invalid_split"})
            continue

        lang = str(row.get("lang") or "en").strip()
        expected_abstain = ABSTAIN_HI if lang == "hi" else ABSTAIN_EN
        task_type = str(row.get("task_type") or "chat_answerable_teacher").strip()
        answer = str(row.get("answer") or "").strip()
        question = str(row.get("question") or "").strip()
        passage_objs = row.get("passage_objs") or [
            {"page": 1, "doc_type": "RHP", "text": t} for t in (row.get("passages") or [])
        ]
        passages_text = format_passage_blocks(passage_objs)

        if not question or not answer or not passages_text.strip():
            reasons["empty_field"] += 1
            rejected.append({**row, "reject_reason": "empty_field"})
            continue

        if task_type == "chat_unanswerable_teacher":
            # Force exact abstain string on unanswerable teacher examples
            if answer not in (ABSTAIN_EN, ABSTAIN_HI):
                answer = expected_abstain
            missing_nums = unmatched_numbers(passages_text, answer)
            if missing_nums:
                reasons["unmatched_numbers"] += 1
                rejected.append(
                    {
                        **row,
                        "reject_reason": "unmatched_numbers",
                        "unmatched_numbers": missing_nums,
                    }
                )
                continue
        else:
            # Answerable numeric teacher row: must not abstain, must cite [n], <= 120 words, 0 unmatched numbers
            if (
                answer in (ABSTAIN_EN, ABSTAIN_HI)
                or "could not find this in the document" in answer.lower()
            ):
                reasons["unexpected_abstain"] += 1
                rejected.append({**row, "reject_reason": "unexpected_abstain"})
                continue
            if not _CITATION_RE.search(answer):
                reasons["missing_citation"] += 1
                rejected.append({**row, "reject_reason": "missing_citation"})
                continue
            if len(answer.split()) > 120:
                reasons["too_long_over_120_words"] += 1
                rejected.append({**row, "reject_reason": "too_long_over_120_words"})
                continue
            missing_nums = unmatched_numbers(passages_text, answer)
            if missing_nums:
                reasons["unmatched_numbers"] += 1
                rejected.append(
                    {
                        **row,
                        "reject_reason": "unmatched_numbers",
                        "unmatched_numbers": missing_nums,
                    }
                )
                continue

        prompt = render_chat_prompt(
            question=question,
            passages=passage_objs,
            lang=lang,
            handoff_dir=handoff_dir,
        )
        clean_row = {
            "id": row.get("id") or f"{task_type}_{len(kept) + 1:05d}",
            "ipo_id": ipo_id,
            "company": row.get("company") or ipo_id,
            "split": split,
            "label_source": "ai",
            "task_type": task_type,
            "lang": lang,
            "question": question,
            "passages": [
                f"[{i}] ({str(p.get('doc_type') or 'RHP').upper()} page {p.get('page') or p.get('page_start') or 1})\n{p.get('text', '')}"
                for i, p in enumerate(passage_objs, start=1)
            ],
            "answer": answer,
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": answer},
            ],
        }
        kept.append(clean_row)

    total = len(kept) + len(rejected)
    stats = {
        "kept": len(kept),
        "dropped": len(rejected),
        "drop_rate": round(len(rejected) / max(1, total), 4),
        "reasons": dict(reasons),
    }
    return kept, rejected, stats


def mix_rewrite_and_chat_sft(
    rewrite_train: list[dict[str, Any]],
    rewrite_dev: list[dict[str, Any]],
    chat_rows: list[dict[str, Any]],
    excluded_ipos: set[str],
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Combine existing `student_v1` rewrite SFT pairs with new chat SFT rows without excluded IPO leakage."""
    rng = random.Random(seed)

    clean_rw_train = [r for r in rewrite_train if r.get("ipo_id") not in excluded_ipos]
    clean_rw_dev = [r for r in rewrite_dev if r.get("ipo_id") not in excluded_ipos]

    chat_train = [
        r for r in chat_rows if r.get("split") == "train" and r.get("ipo_id") not in excluded_ipos
    ]
    chat_dev = [
        r for r in chat_rows if r.get("split") == "dev" and r.get("ipo_id") not in excluded_ipos
    ]

    combined_train = list(clean_rw_train) + list(chat_train)
    combined_dev = list(clean_rw_dev) + list(chat_dev)
    rng.shuffle(combined_train)
    rng.shuffle(combined_dev)

    task_counts = Counter(r.get("task_type", "risk_rewrite") for r in chat_train + chat_dev)
    source_counts = Counter(r.get("label_source", "ai") for r in combined_train + combined_dev)

    summary = {
        "rewrite_train": len(clean_rw_train),
        "rewrite_dev": len(clean_rw_dev),
        "chat_train": len(chat_train),
        "chat_dev": len(chat_dev),
        "total_train": len(combined_train),
        "total_dev": len(combined_dev),
        "chat_breakdown": dict(task_counts),
        "label_source_mix": {
            "human": int(source_counts.get("human", 0)),
            "human_verified_ai": int(source_counts.get("human_verified_ai", 0)),
            "ai": int(source_counts.get("ai", 0)),
            "rule": int(source_counts.get("rule", 0)),
        },
    }
    return combined_train, combined_dev, summary


def _load_jsonl_or_gz(path: pathlib.Path) -> list[dict[str, Any]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--handoff-dir",
        type=pathlib.Path,
        default=HANDOFF_DIR,
        help="Path to ml/handoff directory",
    )
    ap.add_argument(
        "--out-dir",
        type=pathlib.Path,
        required=True,
        help="Directory to write scripted near-miss unanswerables and/or filtered SFT files",
    )
    ap.add_argument(
        "--target-scripted",
        type=int,
        default=1500,
        help="Number of scripted same-section near-miss unanswerables to generate (default: 1500)",
    )
    ap.add_argument(
        "--teacher-raw",
        type=pathlib.Path,
        default=None,
        help="Optional path to raw teacher-generated JSONL to filter with numkeep and mix",
    )
    args = ap.parse_args(argv)

    data_dir = args.handoff_dir / "data"
    excluded_obj = json.loads((data_dir / "excluded_ipos.json").read_text(encoding="utf-8"))
    excluded_set = set(excluded_obj["ipos"].keys())

    splits_obj = json.loads((data_dir / "splits_by_ipo.json").read_text(encoding="utf-8"))
    ipo_to_split = {
        item["ipo_id"]: item["slice"]
        for item in splits_obj["ipos"]
        if not item.get("excluded") and item["ipo_id"] not in excluded_set
    }

    # Load available non-excluded risk passages from classifier_train (if downloaded) + classifier_dev
    risk_rows: list[dict[str, Any]] = []
    for fname, default_split in [
        ("classifier_train.jsonl.gz", "train"),
        ("classifier_dev.jsonl.gz", "dev"),
    ]:
        fpath = data_dir / fname
        if fpath.exists():
            for r in _load_jsonl_or_gz(fpath):
                if r["ipo_id"] not in excluded_set:
                    r["split"] = ipo_to_split.get(r["ipo_id"], default_split)
                    risk_rows.append(r)

    scripted_rows = build_scripted_near_miss_unanswerables(
        risk_rows=risk_rows,
        excluded_ipos=excluded_set,
        target_count=args.target_scripted,
        handoff_dir=args.handoff_dir,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    scripted_path = args.out_dir / "scripted_near_miss_unanswerables.jsonl"
    with scripted_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in scripted_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    result_meta: dict[str, Any] = {
        "scripted_near_miss_count": len(scripted_rows),
        "scripted_path": str(scripted_path),
    }

    if args.teacher_raw and args.teacher_raw.exists():
        raw_teacher = _load_jsonl_or_gz(args.teacher_raw)
        kept_teacher, rejected_teacher, filter_stats = filter_teacher_chat_rows(
            raw_rows=raw_teacher,
            excluded_ipos=excluded_set,
            handoff_dir=args.handoff_dir,
        )
        kept_path = args.out_dir / "teacher_chat_kept.jsonl"
        rej_path = args.out_dir / "teacher_chat_kept.rejected.jsonl"
        with kept_path.open("w", encoding="utf-8", newline="\n") as f:
            for r in kept_teacher:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with rej_path.open("w", encoding="utf-8", newline="\n") as f:
            for r in rejected_teacher:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        result_meta["teacher_filter_stats"] = filter_stats

    print(json.dumps(result_meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
