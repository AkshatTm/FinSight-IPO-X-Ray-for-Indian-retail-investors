# Results and experiments

Every number on this page is generated from `eval_results/` by `scripts/docs_gen.py`; nothing is typed
by hand. Each row says whether it was **re-measured** for v1.1 (3 Nov 2026, pipeline version 4.2) or
**carried** from the last Phase 3 / Phase 4 run. Runs are single runs unless the row gives seeds. The
plans behind each experiment are in the Phase 1 and Phase 2 data-and-evaluation documents
([05](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/docs/05_DATA_AND_EVALUATION.md),
[B04](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/docs/phase2/B04_DATA_AND_EVALUATION.md))
and the Phase 3 benchmark plan
([C04](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/docs/phase3/C04_BENCHMARK.md)).
How to re-run each one: [Reproduce the numbers](evaluation/reproduce.md).

## v1.1 scorecard

<!-- generated:scorecard start -->

Copied from [`eval_results/final/FINAL_SCORECARD.md`](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/final/FINAL_SCORECARD.md); file paths in the tables are relative to the repository root.

Every number is copied from a result file named in the row. **Re-measured today** = run on
3 Nov 2026 on this laptop at commit `57bb013` or later (pipeline_version 4.2). **Carried** = the
last Phase 3 / Phase 4 measurement, not re-run (GPU or a long CPU job). No estimates.
All runs are single runs unless the row says seeds. Test-slice documents were scored, never tuned on (C-ADR-02).

### Extraction

| Metric | Value | Status | Source |
|---|---|---|---|
| E14 summary extraction, numeric value match (NVM), gold v3, all 10 showcase IPOs | **0.774** (195 valued rows) | re-measured today | `eval_results/final/e14_today.json` |
| E14 status accuracy on blank gold rows | 0.704 (54 rows) | re-measured today | same |
| E14 page agreement | 0.747 (158 pages) | re-measured today | same |
| E14, extractor v1 (frozen) → v2 → v2 + SOD engine | 0.682 → 0.769 → 0.774 | v1, v2 carried; 0.774 today | `eval_results/c/e14_e15_versions.json`, `e14_today.json` |
| Field extractor v1, dev EM / F1 (3 seeds) | 0.936 ± 0.002 / 0.949 ± 0.002 | carried | `eval_results/c/extractor_v1_on_v3dev.json` |
| Bench v1 Task A (rules), NVM | 0.724 [0.636, 0.816] | carried | `eval_results/c4/bench_summary.json` |

### Red flags

| Metric | Value | Status | Source |
|---|---|---|---|
| E15 red-flag status accuracy, 13 checks × 10 IPOs | **0.769** (130 statuses) | re-measured today | `eval_results/final/e15_today.json` |
| E15 accuracy where gold has a value | 0.725 (80) | re-measured today | same |
| E15 serious disagreements (OK vs Concern) | 2 | re-measured today | same |
| E15 history: v1 → v1 + offer wiring → v2 → today | 0.646 → 0.731 → 0.762 → 0.769 | carried / today | `e14_e15_versions.json`, `e15_today.json` |
| Decided checks over 289 RHPs (rules only) | 1,561 → **1,714** | carried (CC-05) | `docs/phase4/PROGRESS_CC.md` |
| Jio Platforms: checks decided from the RHP | **7 / 13** (RF05/06/07/11 need the price band) | re-measured today (live upload) | `GET /api/docs/doc_72480c2e249eb8da/redflags` |
| Jio: severe findings that force High | **0** (was 1: SEBI order on the Promoter, p.472, now shown as a promoter finding, C-ADR-26) | re-measured today | same |
| Jio risk level | Low (was High, forced by the promoter order) | re-measured today | `.../report` |
| Bench v1 Task B (rules), status accuracy | 0.703 [0.582, 0.824] | carried | `bench_summary.json` |

**C-ADR-26 on the 10 showcase IPOs** (re-measured today, rules only, 46 s, `eval_results/final/severe_about.jsonl`):
forced High **6 / 10 before → 4 / 10 now**. Ather Energy (SEBI order, p.360) and Lenskart (fraud
case, p.955) drop out: the subject is a director. Groww, HDB Financial, PhysicsWallah and Tata
Capital stay High on findings about the company itself. The `about` labels are the rule's output,
not checked by a person; 8 of the 10 are test-slice IPOs, described here, never tuned on.

### Risk classifier and seriousness

| Metric | Value | Status | Source |
|---|---|---|---|
| Category classifier (DeBERTa-v3-base), dev macro-F1, 3 seeds | **0.892 ± 0.006** (TF-IDF 0.862) | carried | `eval_results/b/classifier_base.json` |
| Same, gold-150 (human-verified test labels), mean of 3 seeds | 0.899 | carried | same |
| DeBERTa-v3-large, dev / gold-150 | 0.894 ± 0.007 / 0.875 (not adopted) | carried | `eval_results/c/classifier_large.json` |
| Seriousness severe recall, dev / gold-150 best seed | 0.56 / 0.75 (4 severe rows) | carried | `docs/phase3/C05_ROADMAP.md` C2.4 |
| gold-150 labels: model pre-fill agreement with Akshat | 0.88 (132/150), 18 changed | carried | `eval_results/c/gold150_verification.json` |

### Plain-English rewrites (student, Qwen3-4B LoRA, GGUF Q4_K_M)

| Metric (gold-50, test slice, Akshat's blind ratings) | base / student / teacher | Status | Source |
|---|---|---|---|
| Faithful = yes | 0.84 / **0.92** / 0.98 | carried | `eval_results/c/simplify_gold50.json` |
| Plain English (1–5) | 3.00 / **4.64** / 4.80 | carried | same |
| Product post-checks passed | student **49 / 50** (8B variant 30 / 50, not adopted) | carried | `eval_results/c/student_vs_base_gold50.json` |

### FinSight Bench v1 (7 test IPOs, frozen inputs, single run)

| Task | rules_v1 | student | Status |
|---|---|---|---|
| A key facts, NVM | 0.724 | 0.340 | carried |
| B red flags, status accuracy | 0.703 | 0.473 | carried |
| C questions, correct (answerable) | 0.327 | 0.490 | carried |
| C abstains on unanswerable | 0.857 | 0.333 | carried |
| C hallucinated number on unanswerable | 0.048 | 0.333 | carried |
| G advice probes refused | 1.000 | 0.429 | carried |

Source: `eval_results/c4/bench_summary.json`. In the product, the guard refuses advice before the
model runs, so G is a model-only probe.

### Laptop timings (RTX 2050 4 GB, 16 GB RAM, profile `local`)

Jio Platforms RHP, 591 pages, one upload, **re-measured today** (`data/preload_log.csv`),
seconds from start to the end of each stage:

| received | validated | parsed | sections | facts | financials | red flags | compare | sod | risks split | risks scored | risk level | simplify | index (done) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 6 | 23 | 23 | 25 | 29 | 32 | 32 | 33 | 46 | 148 | 149 | 149 | **258** |

Total 264 s (4.4 min) including upload. The slow parts are risk scoring (classifier + novelty,
~100 s) and the retrieval index (~110 s).

### Corpus and splits (carried)

| Item | Value | Source |
|---|---|---|
| Corpus IPOs (2009–2023, page text) | 389 (279 prospectus, 110 RHP; median 450 pages) | `eval_results/corpus_stats.json` |
| Recent universe (2021–2026 RHPs) | 289; 275 parsed, 14 excluded with reasons (12 SME, 2 unnumbered risks) | `docs/phase3/C05_ROADMAP.md` C1 |
| Splits (frozen, strict time split) | train 389 corpus + 110 new; dev 52 + 3 showcase; test 103 + 7 showcase; 14 excluded | `configs/splits.yaml` |
| Risk bank used for the reference scores | 440 IPOs, 29,677 risks | `docs/phase3/C_DECISIONS.md` C-ADR-25 |
| Risk-level reference (full documents) | 165 train + dev IPOs | `configs/risklevel.yaml` |

<!-- generated:scorecard end -->

!!! note "Correction to one label"
    The scorecard row "Recent universe (2021–2026 RHPs)" has the wrong years: the 289 rows of
    `configs/ipo_universe.csv` are dated 2024 (94), 2025 (98) and 2026 (97) by SEBI posting date
    ([datasheet](datasheets/new_ipos.md)). The counts are right. The scorecard file is left as written.

## Phase 1 results (fact sheet and chat)

Test-set figures of the Phase 1 experiments. The chat rows (E7) were measured with the Phase 1 profile
`full` (`qwen3.5:2b`), not with the v1.1 student; the student's chat behaviour is measured by Vidura
Bench Task C above.

<!-- generated:results start -->

| Experiment | Metric | Result | File |
| --- | --- | --- | --- |
| Extractor ladder, Rung 1: rules | NVM, 7 test IPOs | full 0.86, body-only 0.23 | `ladder_table.json` |
| Extractor ladder, Rung 2: pretrained QA | NVM, 7 test IPOs | full 0.36, body-only 0.37 | `ladder_table.json` |
| Extractor ladder, Rung 3: fine-tuned QA | NVM, 7 test IPOs | full 0.74, body-only 0.85 | `ladder_table.json` |
| Extractor ladder, Rung 4: BiLSTM-CRF | NVM, 7 test IPOs | full 0.49, body-only 0.28 | `ladder_table.json` |
| Number verifier, seeded errors | scale-mismatch recall, held out | 35/40 [0.74, 0.95] | `verifier.json` |
| Advice guard (keyword), in-sample | block / false-block | 60/60 / 0/60 | `guard.json` |
| Retrieval, bm25 | recall@1 / recall@5, 56 test questions | 0.30 / 0.62 | `retrieval.json` |
| Retrieval, hybrid+rerank | recall@1 / recall@5, 56 test questions | 0.46 / 0.61 | `retrieval.json` |
| Chat answers (E7, dev), one run | numbers marked ✅ | 0.76 of 68 | `e7.json` |
| Chat answers (E7, test), one run | numbers marked ✅ | 0.69 of 86 | `e7.json` |

<!-- generated:results end -->

## Every experiment

One row per planned experiment (E1–E24 from the plan tables), with every result file that exists for
it and what happened to it. "No result file" means the experiment was not run.

<!-- generated:registry start -->

| ID | Question | Result files | Note |
| --- | --- | --- | --- |
| E1 | How good are auto-labels? | `weaklabel_audit.json` |  |
| E2 | Rules baseline | `ladder_table.json` |  |
| E3 | Does fine-tuning on weak labels help? | `extractor_metrics-13.json`, `extractor_metrics-2026.json`, `extractor_metrics-42.json`, `ladder_table.json` |  |
| E4 | Ablations | no result file |  |
| E5 | Does the verifier catch errors? | `verifier.json` |  |
| E6 | Retrieval quality | `retrieval.json` |  |
| E7 | Answer quality | `e7.json` |  |
| E8 | Guard | `guard.json`, `guard_clf.json`, `guard_compare.json` |  |
| E9 | Frontier comparison | no result file | frontier answers were not collected; Vidura Bench v1 compares rules and the student |
| E10 | Latency + memory | `latency.json` |  |
| E11 | BiLSTM-CRF rung (P1) | `bilstm_metrics-13.json`, `bilstm_metrics-2026.json`, `bilstm_metrics-42.json` |  |
| E12 | ASR | `asr.json` | speech input removed in v1.1 (English-only); the file is history |
| E13 | Are risks split correctly? | `b/segmentation.json` |  |
| E14 | Are red-flag inputs extracted correctly? | `b/summary_extraction.json`, `b/summary_extraction_v2.json`, `b/summary_extraction_v2_on_v31.json`, `c/e14_e15_versions.json`, `final/e14_today.json` |  |
| E15 | Do red-flag statuses agree with hand-computed ones? | `b/redflags.json`, `b/redflags_v1_wired.json`, `b/redflags_v2.json`, `b/redflags_v2_on_v31.json`, `c/e14_e15_versions.json`, `final/e15_today.json` |  |
| E16 | How good is the category classifier? | `b/classifier_base.json`, `b/classifier_tfidf.json`, `c/classifier_large.json`, `c/classifier_onnx_check.json` |  |
| E17 | Does the seriousness rule make sense? | no result file |  |
| E18 | Are rewrites faithful? | `c/simplify_gold50.json`, `c/student_vs_base_gold50.json` |  |
| E19 | Are rewrites easier to read? | `c/student_eval.json` |  |
| E20 | Do rewrites keep numbers and certainty? | `c/student_eval.json`, `c/student_vs_base_gold50.json` |  |
| E21 | Does the risk level relate to real outcomes? | `b/risklevel_fit.json`, `c/risklevel_scoring.json` | thresholds fitted (C-ADR-25); the outcome comparison waits for `data/gold/outcomes.csv` |
| E22 | Is "unusual" meaningful? | `b/novelty.json` |  |
| E23 | Speed and robustness on unseen PDFs | no result file | cut: no hosting (B-ADR-16); laptop timings are in FINAL_SCORECARD |
| E24 | Cost | no result file | cut: no hosting, no cost |
| E8r | Does the guard still behave after allowing risk-level questions? | no result file |  |
| E7c | Chat answers on the deployed `cloud` profile (BM25, Q4) | no result file | cut: no `cloud` profile |

<!-- generated:registry end -->

## Caveats

- **Small test sets.** E14 / E15 are scored on the 10 showcase IPOs (195 valued rows, 130 statuses),
  Vidura Bench on 7 test IPOs, the extractor ladder on 7 test IPOs (56 facts), the chat on 67 test
  questions and the held-out guard test on 18 questions. Intervals are wide.
- **AI-assisted gold.** Gold values were pre-filled with AI help and checked by Akshat against the page
  (ADR-035). Gold-150 categories started from model labels (Akshat changed 18 of 150). The bake-off
  ratings were made by a blind AI rater and accepted by Akshat. Files mark this with `label_source`.
- **Single runs and seeds.** E14, E15, Bench v1 and E7 are single runs; the field extractor, the
  classifier (base and large) and the BiLSTM-CRF are 3 seeds; the student is one seed.
- **Test-informed decisions.** Gold v3.1 fixed conventions after reading test results (C-ADR-22); the
  extractor v2 gold ladder row is a reporting row; the X-Ray's rules-first choice and the name-matching
  fix (ADR-045) were made after a first test run, which is kept under `strict_metric`.
- **8 of the 10 showcase IPOs are test-slice IPOs.** The C-ADR-26 counts on them are described, never
  tuned on.
- **Not advice.** No experiment predicts listing gains or returns. E21 compares the risk level with
  past outcomes only to check that it behaves sensibly; it has not been run.

## Notes stored with the results

<!-- generated:notes start -->

- `guard.json`: Keyword/regex guard (ADR-046). Set drafted by Claude chat, not yet reviewed by Akshat (0/120 rows reviewed); rules were tuned after reading it, so these numbers are in-sample. fresh_probes_first_run is the unseen estimate. The MuRIL classifier row of E8 uses a 70/15/15 split of the same set (later).
- `guard_compare.json`: Held-out 15 % (seed 2026 split, stratified by language and label) of the AI-drafted E8 set, not reviewed by Akshat. The keyword rules were tuned on the whole set, so their number is in-sample; MuRIL never saw these questions. The test part is tiny: read the intervals, not the point estimates.
- `ladder_table.json`: NVM on gold v1. Headline = test IPOs, bootstrap over IPOs (1,000 resamples), paired differences with the same IPOs drawn for both rungs. Fine-tuned = mean over 3 seeds per row. body_only blanks pages 1-15 and is scored on rows whose value is still stated in the searched pages (registrar, managers and promoters are read from the cover only, so they have no body-only rows). Per-field numbers are descriptive. Dev is used only to choose the extractor per field (ADR-018). Names are compared ignoring case, punctuation and spacing (ADR-045); `strict_metric` holds the first run, which only ignored case.
- `verifier.json`: E5 is a unit-level benchmark: errors are built by known rules on templated answers, so high recall is expected by design; it says nothing about free LLM text (E7, E9). Quote the held-out figures in `headline`: scale-mismatch recall 35/40 with rules frozen on the dev IPOs. `metrics`, `by_split` and `by_language` are the current rules, after one rule fix made on seeing test-IPO misses: 40/40, not held-out (ADR-044).
- `weaklabel_audit.json`: Measured on v1 labels; the misses were fixed in v2, which is not re-audited.
- `xray_accuracy.json`: System accuracy: the X-Ray's chosen value per ladder field against gold, NVM. rules_first = fields.yaml as shipped (G2 decision, informed by test results); dev_choice = the dev-only choice of ADR-018 (fine-tuned model primary for fresh and total issue size). Same saved candidates for both. Clean re-check on gold v2 in P5.1.

<!-- generated:notes end -->
