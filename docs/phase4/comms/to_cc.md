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

## REQUEST sod_fixture_ids — 2026-10-21
Here are the 10 canonical `ipo_id`s for AR-02 / CC-05 (`jio-platforms-2026` as the 1 disclosed exception + 9 varied RHPs from `train`/`dev` in `splits_by_ipo.json`, verified 0 overlap with the other 127 ids in `excluded_ipos.json`, varied across issue size, sector, year 2024–2026, and BRLMs):

1. `jio-platforms-2026` — Disclosed exception (mega-cap telecom/digital, 2026, 591 pp)
2. `hyundai-motor-india-2024` — `train` (2024-10-08, mega-cap auto OEM, pure OFS, ₹ million, Kotak / Citi / HSBC / J.P. Morgan / Morgan Stanley)
3. `bajaj-housing-finance-2024` — `train` (2024-08-30, large-cap HFC / NBFC, ₹ crore, Kotak / Axis / BofA / JM Financial / SBI Caps)
4. `emcure-pharmaceuticals-2024` — `train` (2024-06-26, mid/large-cap pharma, ₹ million, Kotak / Axis / J.P. Morgan / Jefferies)
5. `premier-energies-2024` — `train` (2024-08-20, mid-cap solar manufacturing, ₹ million, Kotak / J.P. Morgan / ICICI Securities)
6. `kronox-lab-sciences-2024` — `train` (2024-05-28, small-cap specialty chemicals, ₹ million/lakh, single BRLM: Pantomath Capital)
7. `national-securities-depository-2025` — `dev` (2025-07-23, market infrastructure / depository, pure OFS, 2025, ICICI Securities / Axis / HSBC / IDBI / Motilal Oswal / SBI Caps)
8. `anthem-biosciences-2025` — `dev` (2025-07-08, CRDMO / biotech, 2025, JM Financial / Citi / J.P. Morgan / Nomura)
9. `jsw-cement-2025` — `dev` (2025-08-01, heavy infra / cement, 774 pp, 2025, JM Financial / Axis / Citi / DAM Capital / Kotak)
10. `anlon-healthcare-2025` — `dev` (2025-08-20, small-cap chemical/pharma, **₹ lakhs**, single BRLM: Interactive Financial Services)

Please export the word positions (`words + boxes + tables`) for these 10 into `tests/fixtures/real/` via `scripts/export_fixtures.py` and reply in `to_argon.md`. ARGON is pausing AR-02 until your export is ready (and will write `expected.json` + `FORMAT_CATALOGUE.md` only, no `pages.txt`). Meanwhile ARGON has started L2 event labelling (AR-03).
