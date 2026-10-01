"""Grow the dev question set to ~50 from the dev IPOs' gold values (P3.2c, item 6).

    uv run python scripts/expand_dev_questions.py [--dry-run]

Only the three dev IPOs are used (ADR-026); ``questions_test.jsonl`` is never read or written.
Each present gold field gets one more question in a language the IPO's set does not yet have for
that field (English, Hindi or Hinglish in rotation), with the gold page and document as evidence.
Six near-miss unanswerable questions (outcomes that happen after the offer documents are printed)
are added for tuning the abstain threshold. Written by Claude Code from the gold values:
``label_source = ai_drafted_claude_code``, ``review_status = pending``. Re-running is a no-op.
"""

from __future__ import annotations

import argparse
import json

from finsight.core.config import get_settings

DEV_IPOS = ["ather-energy-2025", "hexaware-technologies-2025", "urban-company-2025"]
LANGS = ("en", "hi", "hinglish")
TEMPLATES: dict[str, dict[str, str]] = {
    "fresh_issue_size": {
        "en": "What is the size of the fresh issue?",
        "hi": "फ्रेश इश्यू का साइज़ कितना है?",
        "hinglish": "fresh issue ka size kitna hai?",
    },
    "ofs_amount": {
        "en": "How much is the offer for sale worth in rupees?",
        "hi": "ऑफर फॉर सेल की राशि कितनी है?",
        "hinglish": "offer for sale ka amount kitna hai?",
    },
    "ofs_shares": {
        "en": "How many equity shares are offered for sale?",
        "hi": "ऑफर फॉर सेल में कितने शेयर बेचे जा रहे हैं?",
        "hinglish": "offer for sale mein kitne shares hain?",
    },
    "offer_price": {
        "en": "What is the offer price per equity share?",
        "hi": "ऑफर प्राइस कितना है?",
        "hinglish": "ipo ka offer price kya hai?",
    },
    "total_issue_size": {
        "en": "How big is the IPO in total?",
        "hi": "कुल इश्यू साइज़ कितना है?",
        "hinglish": "total issue size kitna hai?",
    },
    "face_value": {
        "en": "What is the face value per equity share?",
        "hi": "प्रत्येक शेयर का फेस वैल्यू क्या है?",
        "hinglish": "face value kya hai?",
    },
    "book_running_lead_managers": {
        "en": "Which banks are the book running lead managers?",
        "hi": "बुक रनिंग लीड मैनेजर कौन हैं?",
        "hinglish": "book running lead managers kaun hain?",
    },
    "registrar": {
        "en": "Who is the registrar to the offer?",
        "hi": "इस ऑफर का रजिस्ट्रार कौन है?",
        "hinglish": "registrar kaun hai?",
    },
    "promoters": {
        "en": "Who are the promoters of the company?",
        "hi": "कंपनी के प्रमोटर कौन हैं?",
        "hinglish": "company ke promoters kaun hain?",
    },
    "objects_of_offer": {
        "en": "How will the money raised in the fresh issue be used?",
        "hi": "फ्रेश इश्यू से मिले पैसे का इस्तेमाल कहाँ होगा?",
        "hinglish": "ipo ke paise ka use kahan hoga?",
    },
}
ABSENT = {  # ipo -> [(language, question)]: outcomes that the offer documents cannot contain
    "ather-energy-2025": [
        ("en", "How many times was the IPO subscribed on the first day?"),
        ("hinglish", "listing day pe closing price kya tha?"),
    ],
    "hexaware-technologies-2025": [
        ("hi", "इस IPO को पहले दिन कितना सब्सक्रिप्शन मिला?"),
        ("en", "What was the closing price on the day of listing?"),
    ],
    "urban-company-2025": [
        ("hinglish", "ipo total kitni baar subscribe hua?"),
        ("hi", "लिस्टिंग के दिन शेयर किस भाव पर बंद हुआ?"),
    ],
}
DOC = {"rhp": "rhp", "prospectus": "pro"}
PER_IPO = 14  # answerable questions per dev IPO: 3 x 14 + 9 unanswerable = 51


def gold_text(value: object) -> str:
    while isinstance(value, list):
        value = value[0] if len(value) == 1 else "; ".join(str(v) for v in value)
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    gold_dir = get_settings().paths.data_dir / "gold"
    path = gold_dir / "questions_dev.jsonl"
    existing = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    seen_q = {q["question"] for q in existing}
    gold = [json.loads(x) for x in (gold_dir / "gold_values.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]  # fmt: skip
    base = {"split": "dev", "label_source": "ai_drafted_claude_code", "review_status": "pending"}
    new: list[dict[str, object]] = []
    for ipo in DEV_IPOS:
        present = [g for g in gold if g["ipo_id"] == ipo and g["status"] == "present"
                   and g["field_id"] in TEMPLATES]  # fmt: skip
        for _ in range(3):  # one more language per field per round, until the IPO has PER_IPO
            for i, g in enumerate(present):
                mine = [q for q in [*existing, *new] if q["ipo_id"] == ipo and q["answerable"]]
                if len(mine) >= PER_IPO:
                    break
                value = gold_text(g["value_raw"])
                # an old question asks for this field when its gold text starts the same; a new
                # one when it was written from this field (two fields may share one value)
                done = {q["language"] for q in existing if q["ipo_id"] == ipo and q["answerable"]
                        and q["answer_gold"][:20] == value[:20]}  # fmt: skip
                done |= {lg for lg, text in TEMPLATES[g["field_id"]].items() if text in seen_q}
                order = [LANGS[(i + k) % 3] for k in range(3)]
                language = next((lg for lg in order if lg not in done), None)
                question = TEMPLATES[g["field_id"]].get(language or "")
                if language is None or question is None or question in seen_q:
                    continue
                seen_q.add(question)
                new.append({"ipo_id": ipo, "question": question, "language": language,
                            "answer_gold": value, "evidence_doc": DOC[g["doc"]],
                            "evidence_page": g["page"], "answerable": True, **base})  # fmt: skip
        for language, question in ABSENT[ipo]:
            if question not in seen_q:
                seen_q.add(question)
                new.append({"ipo_id": ipo, "question": question, "language": language,
                            "answer_gold": "Not in the document (happens after the offer documents)",
                            "evidence_doc": None, "evidence_page": None, "answerable": False,
                            **base})  # fmt: skip
    print(f"{len(existing)} existing + {len(new)} new = {len(existing) + len(new)}")
    if args.dry_run or not new:
        return
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for q in new:
            fh.write(json.dumps(q, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
