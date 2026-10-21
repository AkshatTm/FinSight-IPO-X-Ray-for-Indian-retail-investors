# Phase 4 — Model and label specs (ARGON)

Every model: split by IPO (reuse `ml/handoff/data/splits_by_ipo.json`), never train on `excluded_ipos.json`,
3 seeds for M2–M4, notebook debugged on a tiny slice on T4 before G4, checkpoint to Drive every epoch, resume flag.
ARGON writes notebooks and scripts; **Akshat runs them on Colab** and drops the outputs where the notebook says.
ARGON then reads the outputs and iterates.

---

## Labels first (ARGON reads PDFs; Akshat verifies)

ARGON may read RHP PDFs in `data/raw/` (CC is not allowed to; this is why labelling is ARGON's).
Every label row carries `ipo_id`, `page`, `evidence_quote` (≤ 25 words from the RHP), `label_source: "ai"`,
and becomes `human_verified_ai` once Akshat checks it.

### L1 — SOD fixtures (AR-02, **first priority: unblocks CC-05**)
For 10 RHPs: **Jio** (the single disclosed exception to the exclusion rule; note it in FORMAT_CATALOGUE.md) + **9 varied RHPs from `train`/`dev` slices only** (`ml/handoff/data/splits_by_ipo.json`; large/small, different lead managers, years 2024–2026). Never pick a test-slice, bench, demo or excluded IPO.

**Flow:** (1) ARGON proposes the 10 ids in `comms/to_cc.md` (`## REQUEST sod_fixture_ids`) and waits; (2) CC exports word positions (words + boxes + tables) for those 10 into `tests/fixtures/real/` via `scripts/export_fixtures.py` and replies in `to_argon.md`; (3) ARGON writes `expected.json` and `FORMAT_CATALOGUE.md` only. CC's reader works from word boxes, so `pages.txt` is optional reading context, not the test input.
- Locate "Summary of the Offer Document" (also titled "Summary of Offer Document", sometimes inside "Section II").
- Optional: `data/gold/sod_fixtures/<ipo_id>/pages.txt` — extracted text of the SOD pages (PyMuPDF, markers `=== page N ===`) as reading context. The parser is tested on CC's word-box fixtures, not on this.
- Write `data/gold/sod_fixtures/<ipo_id>/expected.json`:
  - `summary_financials`: per period (`FY24`, `FY25`, `FY26`, stub) → equity share capital, net worth, revenue from operations, total income, PAT (restated), EPS basic/diluted, NAV per share, total borrowings; with unit as printed (`₹ million` / `₹ lakh` / `₹ crore`) and page.
  - `promoter_holding`: pre-offer %, (post-offer % if printed), page.
  - `litigation_summary`: table rows (entity × category: criminal, statutory/regulatory, disciplinary, material civil, tax) → count + amount, page.
  - `related_party_summary`: total RPT amount per period or "as % of revenue" if printed, page.
  - `auditor_qualifications`: list or "none", page.
  - `weighted_avg_cost_of_acquisition`: per promoter/selling shareholder if printed, page.
  - `objects_of_offer`: rows (purpose, amount, unit), page.
  - `format_notes`: free text describing layout quirks (multi-page tables, footnotes, units in headers).
- Write `data/gold/sod_fixtures/FORMAT_CATALOGUE.md`: the variations across the 10 docs (headings, table orders, unit placement, what's sometimes missing). This is CC's parser spec.

### L2 — Event labels (AR-03, for M3)
`check_id` is the severe kind from `redflags/severe.py` (going_concern, default_or_recall, regulator_order, fraud, qualified_audit), not an RF id.
Source: `ml/handoff/data/serious_finding_hits.jsonl` + more negatives/hypotheticals mined from risk factors.
Label each sentence: `actual_event` (it happened: "the lender recalled the facility on…"), `hypothetical`
("any default could…"), `negated` ("no wilful defaulter…", "has not been…"), `not_relevant`.
Target ~800 sentences, ≥150 per class where possible, from ≥60 IPOs. Akshat verifies a random 100 + every
`actual_event` row (those are what force Risk = High).

### L3 — Gold v4 for the 30 bench IPOs (AR-05)
Ids in `data/platform_bench/` (Akshat's sheet, IPOs tab). Per IPO, from the RHP only:
facts (same field list as the bench sheet's Facts tab), financials (3 FY + stub), use of proceeds, strengths
(as the RHP's "Our Strengths" lists them, paraphrased ≤ 30 words each + page), top 7 risks a retail investor
must know (risk_id from the risk bank if matched, else text + page), and the 13 red-flag inputs.
Write to `data/gold/v4/<ipo_id>.json` + `LABELS_CARD.md`. Akshat verifies facts and financials fully, risks by spot-check.

### L4 — Top-risk labels for training M2 (AR-06)
On **training-split IPOs only** (~60 IPOs): top 7 risks per IPO, chosen from that IPO's risk bank rows, with a
one-line reason. Use the RHP's own "Summary of risk factors"/top-10 risks section as the main signal where present.

---

## M1 — Student v2 (chat + plain-English rewrites)
- **Two frozen prompt templates** (both in `ml/handoff/data/`): `student_chat_template.txt` (chat answers, `generate/prompts.py: build_prompt`) and `student_prompt_template.txt` (risk rewrite, `risks/simplify.py: student_prompt`, `student-v1`). **Chat is M1's primary target** (that is where the 0.333 comes from); the rewrite side must not regress (gold-50 gates below).
- **Problem:** 0.333 hallucinated numbers on unanswerable questions (Bench v1 Task C); weaker than rules on Task A.
- **Base:** same 4B base as student v1 (Qwen3-4B-Instruct-2507, LoRA r=16; 10,362 train / 529 dev rewrite pairs (exact counts in ml/handoff/README.md); see `phase3_models.md`), LoRA → merged → GGUF q4_K_M. Serving stays 4B (16 GB laptop).
- **Data (teacher = Gemma-4-31B-it on G4, as in phase 3):**
  1. Keep the v1 SFT set (10,892 rows).
  2. +~2,000 **unanswerable** examples: question whose answer is not in the given passages → target = the app's exact "not found in the document" response. Mix: near-miss passages (same section, different metric), wrong period, wrong entity.
  3. +~1,000 **answerable numeric** examples where the target copies numbers exactly as written and cites `[n]`.
  4. **Number-keeping filter:** drop any teacher output containing a number not present in its passages (reuse the product's normalizer via the handoff `eval/` helpers, which wrap it — don't import product code directly).
- **Train:** 2 epochs, same LoRA config as v1 unless ARGON justifies a change in the plan; checkpoint each epoch.
- **Targets:** Bench Task C hallucinated ≤ 0.10, Task C correct-answerable ≥ 0.49, gold-50 faithful ≥ 0.92, plain-English ≥ 4.5, post-checks ≥ 49/50.
- **Notebooks:** `ml/notebooks/m1_teacher_gen.ipynb`, `ml/notebooks/m1_student_train.ipynb`, `ml/notebooks/m1_export_gguf.ipynb`.

## M2 — Risk salience ranker (Top 7)
- **Problem:** Risks tab shows 100+ cards. Brokers show 5–7.
- **Model:** DeBERTa-v3-base (large if units allow) cross-encoder: input = `[company + sector] [SEP] risk text`, pointwise regression/ranking loss (listwise if time). Features allowed: category, severity, section position.
- **Labels:** L4 (train), L3 top risks (test, bench IPOs never trained on).
- **Baseline:** current "Five things to know" selection (`five_things_selection.jsonl`).
- **Metrics:** NDCG@7 and Recall@7 vs gold v4 top risks; **broker overlap@7** (share of each broker's risks covered by our top 7, matched by M5 judge).
- **Target:** beats baseline on NDCG@7 and broker overlap.

## M3 — Event classifier (kills false serious findings)
- **Model:** DeBERTa-v3-base, 4 classes, input = context_before + `[SEP]` sentence + `[SEP]` context_after.
- **Baseline:** CC's negation/hypothetical rules (CC-07 exports their predictions on the same test set to `eval_results/p4/cc/event_rules_preds.jsonl`).
- **Metrics:** macro-F1; **precision on `actual_event` ≥ 0.90** (a false actual_event wrongly forces High); recall on `actual_event` ≥ 0.80.
- **Deliver:** ONNX fp32 + `predict.py` per contract.

## M4 — Severity v2
- **Problem:** severe-band recall 0.56. Measured on the dev split, seriousness bands 1–4 (4 = severe; levels 4 and 5 merged, `risks/clf_metrics.py: SEVERE_BAND`), mean of 3 seeds. The exact numbers are in `ml/handoff/eval/baselines.json`.
- **Guardrail:** category macro-F1 (0.892 on dev) must not drop by more than 0.01. It is not the severity target.
- **Approach:** same DeBERTa-v3-base classifier; class-weighted loss and/or focal loss; add severe examples from L2 `actual_event` rows and gold-150; threshold tuning on dev for severe.
- **Target:** severe-band recall ≥ 0.70, with the category macro-F1 guardrail held (drop ≤ 0.01 vs 0.892).

## M5 — Evaluation + Platform Bench judge
- For each delivery: run its eval, fill `metrics.json`, verdict BEATS/TIES/LOSES vs `baselines.json`.
- **Platform Bench risk judge:** for each bench IPO, compare FinSight's top 7 risks vs each broker's risk list (from Akshat's sheet): match risks semantically (same underlying risk), score specificity (has a number / named counterparty), and pairwise preference on a fixed rubric. Blind: platform names replaced with A/B/C/D, order shuffled. Output `eval_results/p4/argon/platform_bench_judge.jsonl` + summary. Akshat spot-checks 20%.
- Write `eval_results/p4/argon/P4_MODEL_RESULTS.md`: one table, every model, baseline vs new, verdict.

## Report-ready honesty rules
- Label sources disclosed per set. AI-drafted labels never called "human".
- Single-seed numbers marked as such. Small n stated.
- A model that loses is reported, not hidden.
