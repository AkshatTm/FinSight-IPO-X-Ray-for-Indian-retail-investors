# Evaluation and results

Every number on this page is generated from `eval_results/` by `scripts/docs_gen.py`; nothing is typed by hand (B09 §1.3). The plans behind each experiment are in [Data and evaluation, Phase 1](05_DATA_AND_EVALUATION.md) (E1–E12) and [Phase 2](phase2/B04_DATA_AND_EVALUATION.md) (E13–E24).

## Headline results

Test-set figures, one row per experiment that has run. Read the intervals in the files, not only the point scores.

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

The registry is read from the two plan tables. "Not run yet" means no result file exists: Phase 2 experiments run in local sessions on real documents and Kaggle (see the roadmap), and no number is shown until a file exists.

<!-- generated:registry start -->

| ID | Question | Result files |
| --- | --- | --- |
| E1 | How good are auto-labels? | `weaklabel_audit.json` |
| E2 | Rules baseline | `ladder_table.json` |
| E3 | Does fine-tuning on weak labels help? | `extractor_metrics-13.json`, `extractor_metrics-2026.json`, `extractor_metrics-42.json`, `ladder_table.json` |
| E4 | Ablations | not run yet |
| E5 | Does the verifier catch errors? | `verifier.json` |
| E6 | Retrieval quality | `retrieval.json` |
| E7 | Answer quality | `e7.json` |
| E8 | Guard | `guard.json`, `guard_clf.json`, `guard_compare.json` |
| E9 | Frontier comparison | not run yet |
| E10 | Latency + memory | `latency.json` |
| E11 | BiLSTM-CRF rung (P1) | `bilstm_metrics-13.json`, `bilstm_metrics-2026.json`, `bilstm_metrics-42.json` |
| E12 | ASR | `asr.json` |
| E13 | Are risks split correctly? | `b/segmentation.json` |
| E14 | Are red-flag inputs extracted correctly? | not run yet |
| E15 | Do red-flag statuses agree with hand-computed ones? | not run yet |
| E16 | How good is the category classifier? | not run yet |
| E17 | Does the seriousness rule make sense? | not run yet |
| E18 | Are rewrites faithful? | not run yet |
| E19 | Are rewrites easier to read? | not run yet |
| E20 | Do rewrites keep numbers and certainty? | not run yet |
| E21 | Does the risk level relate to real outcomes? | not run yet |
| E22 | Is "unusual" meaningful? | not run yet |
| E23 | Speed and robustness on unseen PDFs | not run yet |
| E24 | Cost | not run yet |
| E8r | Does the guard still behave after allowing risk-level questions? | not run yet |
| E7c | Chat answers on the deployed `cloud` profile (BM25, Q4) | not run yet |

<!-- generated:registry end -->

## Caveats

- **Small test sets.** The extractor ladder is scored on 7 test IPOs (56 facts), the chat on 67 test questions and the held-out guard test on 18 questions. Intervals are wide; differences are reported as paired bootstrap differences over the same IPOs.
- **AI-assisted gold.** Gold v1 values were pre-filled with AI help and then checked by Akshat against the page (ADR-035). Agreement with gold means agreement with AI-read, human-checked values. Files mark this with `label_source`.
- **Single runs.** Chat answer quality (E7) is one run of a sampling model; the fine-tuned extractor and BiLSTM-CRF are 3 seeds; the guard classifier is 3 seeds on a very small set.
- **Test-informed decisions.** The per-field extractor choice was made on dev (ADR-018); the name-matching fix (ADR-045) was decided after the first test run, and the first run is kept under `strict_metric` in `ladder_table.json`.
- **Weak-label audit is on an older version.** E1 measured labels v1; the misses were fixed in v2, which is not re-audited.
- **Not advice.** No experiment predicts listing gains or returns. E21 compares the risk level with past outcomes only to check that it behaves sensibly; it is reported as a correlation, never as a forecast.

## Notes stored with the results

<!-- generated:notes start -->

- `guard.json`: Keyword/regex guard (ADR-046). Set drafted by Claude chat, not yet reviewed by Akshat (0/120 rows reviewed); rules were tuned after reading it, so these numbers are in-sample. fresh_probes_first_run is the unseen estimate. The MuRIL classifier row of E8 uses a 70/15/15 split of the same set (later).
- `guard_compare.json`: Held-out 15 % (seed 2026 split, stratified by language and label) of the AI-drafted E8 set, not reviewed by Akshat. The keyword rules were tuned on the whole set, so their number is in-sample; MuRIL never saw these questions. The test part is tiny: read the intervals, not the point estimates.
- `ladder_table.json`: NVM on gold v1. Headline = test IPOs, bootstrap over IPOs (1,000 resamples), paired differences with the same IPOs drawn for both rungs. Fine-tuned = mean over 3 seeds per row. body_only blanks pages 1-15 and is scored on rows whose value is still stated in the searched pages (registrar, managers and promoters are read from the cover only, so they have no body-only rows). Per-field numbers are descriptive. Dev is used only to choose the extractor per field (ADR-018). Names are compared ignoring case, punctuation and spacing (ADR-045); `strict_metric` holds the first run, which only ignored case.
- `verifier.json`: E5 is a unit-level benchmark: errors are built by known rules on templated answers, so high recall is expected by design; it says nothing about free LLM text (E7, E9). Quote the held-out figures in `headline`: scale-mismatch recall 35/40 with rules frozen on the dev IPOs. `metrics`, `by_split` and `by_language` are the current rules, after one rule fix made on seeing test-IPO misses: 40/40, not held-out (ADR-044).
- `weaklabel_audit.json`: Measured on v1 labels; the misses were fixed in v2, which is not re-audited.
- `xray_accuracy.json`: System accuracy: the X-Ray's chosen value per ladder field against gold, NVM. rules_first = fields.yaml as shipped (G2 decision, informed by test results); dev_choice = the dev-only choice of ADR-018 (fine-tuned model primary for fresh and total issue size). Same saved candidates for both. Clean re-check on gold v2 in P5.1.

<!-- generated:notes end -->
