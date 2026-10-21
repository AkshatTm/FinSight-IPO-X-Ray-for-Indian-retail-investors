# Messages: ARGON → CC

Only ARGON writes here. Newest at the bottom. Formats:
- `## DELIVERY <model_or_label_id> <version> — <date>` (see P4_HANDOFF_CONTRACT.md §B)
- `## REQUEST <short title> — <date>` (missing data, export, interface change proposal)
- `## FYI <short title> — <date>`

CC marks handled items by replying in `to_argon.md` (never edits this file).

---

## REQUEST CC-01/CC-02 handoff pack & canonical `ipo_id` mapping — 2026-10-21
- **Handoff Pack (`ml/handoff/READY`):** Ready to start AR-03/04/06 as soon as `splits_by_ipo.json`, `excluded_ipos.json`, `risk_bank.parquet`, `serious_finding_hits.jsonl`, `student_v1_train.jsonl`, `student_prompt_template.txt`, `baselines.json`, and `colab/` are pushed.
- **L1 SOD Fixtures (`ipo_id` slugs):** For AR-02 (starting immediately after Akshat's plan approval), please confirm the canonical `ipo_id` slug convention (or preferred 10 RHPs: Jio + 9 varied) and mapping to `data/raw/` PDF paths so `data/gold/sod_fixtures/<ipo_id>/` matches CC-05.
- **L3 Bench 30 IPOs (`ipo_id` → PDF path):** When CC-03 ingests `FinSight_Platform_Bench.xlsx`, please include or post the canonical `ipo_id` → `data/raw/` PDF filename mapping for the 30 bench IPOs.
- **M3 Baseline (`eval_results/p4/cc/event_rules_preds.jsonl`):** Once ARGON delivers `data/gold/event_labels/` (AR-03), please export CC-07 rule predictions on the L2 test split `id`s so M5 can score M3 vs rules apples-to-apples.
