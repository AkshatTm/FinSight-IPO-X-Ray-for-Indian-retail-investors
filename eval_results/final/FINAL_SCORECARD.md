# FinSight — final scorecard (v1.1, branch `final`)

Every number is copied from a result file named in the row. **Re-measured today** = run on
3 Nov 2026 on this laptop at commit `57bb013` or later (pipeline_version 4.2). **Carried** = the
last Phase 3 / Phase 4 measurement, not re-run (GPU or a long CPU job). No estimates.
All runs are single runs unless the row says seeds. Test-slice documents were scored, never tuned on (C-ADR-02).

## Extraction

| Metric | Value | Status | Source |
|---|---|---|---|
| E14 summary extraction, numeric value match (NVM), gold v3, all 10 showcase IPOs | **0.774** (195 valued rows) | re-measured today | `eval_results/final/e14_today.json` |
| E14 status accuracy on blank gold rows | 0.704 (54 rows) | re-measured today | same |
| E14 page agreement | 0.747 (158 pages) | re-measured today | same |
| E14, extractor v1 (frozen) → v2 → v2 + SOD engine | 0.682 → 0.769 → 0.774 | v1, v2 carried; 0.774 today | `eval_results/c/e14_e15_versions.json`, `e14_today.json` |
| Field extractor v1, dev EM / F1 (3 seeds) | 0.936 ± 0.002 / 0.949 ± 0.002 | carried | `eval_results/c/extractor_v1_on_v3dev.json` |
| Bench v1 Task A (rules), NVM | 0.724 [0.636, 0.816] | carried | `eval_results/c4/bench_summary.json` |

## Red flags

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

Not measured: how many of the 6 showcase IPOs with a severe finding would still be forced High
under C-ADR-26 (today's E15 file lists findings by kind only).

## Risk classifier and seriousness

| Metric | Value | Status | Source |
|---|---|---|---|
| Category classifier (DeBERTa-v3-base), dev macro-F1, 3 seeds | **0.892 ± 0.006** (TF-IDF 0.862) | carried | `eval_results/b/classifier_base.json` |
| Same, gold-150 (human-verified test labels), mean of 3 seeds | 0.899 | carried | same |
| DeBERTa-v3-large, dev / gold-150 | 0.894 ± 0.007 / 0.875 (not adopted) | carried | `eval_results/c/classifier_large.json` |
| Seriousness severe recall, dev / gold-150 best seed | 0.56 / 0.75 (4 severe rows) | carried | `docs/phase3/C05_ROADMAP.md` C2.4 |
| gold-150 labels: model pre-fill agreement with Akshat | 0.88 (132/150), 18 changed | carried | `eval_results/c/gold150_verification.json` |

## Plain-English rewrites (student, Qwen3-4B LoRA, GGUF Q4_K_M)

| Metric (gold-50, test slice, Akshat's blind ratings) | base / student / teacher | Status | Source |
|---|---|---|---|
| Faithful = yes | 0.84 / **0.92** / 0.98 | carried | `eval_results/c/simplify_gold50.json` |
| Plain English (1–5) | 3.00 / **4.64** / 4.80 | carried | same |
| Product post-checks passed | student **49 / 50** (8B variant 30 / 50, not adopted) | carried | `eval_results/c/student_vs_base_gold50.json` |

## FinSight Bench v1 (7 test IPOs, frozen inputs, single run)

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

## Laptop timings (RTX 2050 4 GB, 16 GB RAM, profile `local`)

Jio Platforms RHP, 591 pages, one upload, **re-measured today** (`data/preload_log.csv`),
seconds from start to the end of each stage:

| received | validated | parsed | sections | facts | financials | red flags | compare | sod | risks split | risks scored | risk level | simplify | index (done) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 6 | 23 | 23 | 25 | 29 | 32 | 32 | 33 | 46 | 148 | 149 | 149 | **258** |

Total 264 s (4.4 min) including upload. The slow parts are risk scoring (classifier + novelty,
~100 s) and the retrieval index (~110 s).

## Corpus and splits (carried)

| Item | Value | Source |
|---|---|---|
| Corpus IPOs (2009–2023, page text) | 389 (279 prospectus, 110 RHP; median 450 pages) | `eval_results/corpus_stats.json` |
| Recent universe (2021–2026 RHPs) | 289; 275 parsed, 14 excluded with reasons (12 SME, 2 unnumbered risks) | `docs/phase3/C05_ROADMAP.md` C1 |
| Splits (frozen, strict time split) | train 389 corpus + 110 new; dev 52 + 3 showcase; test 103 + 7 showcase; 14 excluded | `configs/splits.yaml` |
| Risk bank used for the reference scores | 440 IPOs, 29,677 risks | `docs/phase3/C_DECISIONS.md` C-ADR-25 |
| Risk-level reference (full documents) | 165 train + dev IPOs | `configs/risklevel.yaml` |

## What changed since v1.0 (for the talk)

1. **Summary of the Offer Document engine:** reads the RHP's own summary, or the chapters it summarises when there is none (Jio); decided red-flag checks across 289 RHPs went from 1,561 to 1,714.
2. **New Financials data in every report:** 3 fiscal years + the stub period, EPS, NAV, PAT margin, debt/equity, the company's own strengths, promoter holding before and after.
3. **Fairer risk level:** a regulator order on the *promoter* or a group company is shown but no longer forces "High"; only events about the company itself do (Jio: High → Low).
4. **No misleading percentile:** "riskier than 95% of past IPOs" tracked document length, so it is hidden with a reason; Low / Medium / High stays.
5. **Compare** names the company instead of "The Company".
6. **Cache v2:** every report is tied to the PDF hash, the pipeline version and the model fingerprint; a report from an older version is re-run when opened, and a degraded one is never cached.
7. **English only:** Hindi chat and voice input were removed to keep one well-tested path; old clients still work.
8. **Clean library:** blank and outdated analyses were purged (with a backup); reports are rebuilt on pipeline 4.2 by the preload.
9. **Measured, not claimed:** E14 0.774 and E15 0.769 re-measured today on the same gold; everything else is marked as carried.
10. **Cut on purpose:** Phase 4 model training (M1–M5), Platform Bench and gold v4 were dropped; the product keeps the Phase 3 models (classifier 0.892 macro-F1, student 0.92 faithful).
