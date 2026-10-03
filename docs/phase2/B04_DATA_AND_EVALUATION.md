# B04 — Data and Evaluation (Big Phase 2)

## 1. Splits (unchanged principle: split by IPO, tune on dev only)

- **Dev IPOs (3):** hexaware-technologies-2025, ather-energy-2025, urban-company-2025.
- **Test IPOs (7):** the other showcase IPOs.
- **Corpus (389, 2009–2023):** training data for the classifier and simplifier, the risk bank, and the reference population for percentiles and risk-level thresholds. Never contains showcase IPOs (exclusion test stays).
- **Unseen upload set (5):** 5 recent RHPs not in any set, downloaded by Akshat in week 3, used only for the robustness/latency test (E23) and a demo of "any PDF".

## 2. New gold data

| Set | Content | Size | Who | When |
|---|---|---|---|---|
| **gold v3** (`data/gold/gold_v3_summary.jsonl`) | Values for red-flag inputs on all 10 IPOs: revenue, PAT and operating cash flow (last 3 fiscals), total borrowings, net worth, WACA per selling shareholder group, litigation counts/amounts (company, promoters, directors; criminal yes/no), RPT total, promoter + group holding post-issue, pledged %, top-1/top-10 customer %, peer P/E list, auditor remarks | ~25 values × 10 IPOs ≈ 250 | Claude (chat) pre-fills from the PDFs with page + quote; Akshat verifies (as gold v1) | B1.3–B1.4 (by Fri 9 Oct) |
| **red-flag status gold** | Status per check per IPO, computed by hand from gold v3 using the documented thresholds | 13 × 10 = 130 | Computed by script from gold v3, spot-checked by Akshat | B1.4 |
| **segmentation gold** | Risk boundaries (title start pages) for the Risk Factors of 3 dev + 2 test IPOs | ~400 risks | Claude (chat) pre-fills; Akshat spot-checks 50 | B2.1 |
| **category gold-150** | 15 risks × 10 IPOs with one category each | 150 | Claude (chat) pre-fills; Akshat verifies | B2.4 |
| **simplification gold-50** | 50 risks (5 per IPO) for human rating of rewrites from 3 systems | 50 × 3 | Akshat rates (blind to system); Claude (chat) may draft notes | B2.5 |
| **novelty spot-check** | 60 (risk, nearest past risk) pairs at several τ | 60 | Akshat + Claude (chat) | B2.2 |
| **teacher quality-100** | 100 teacher outputs rated | 100 | as above | B2.3 |

All AI-assisted sets carry `label_source` and are disclosed in the report.

## 3. Experiments (continue Phase 1 numbering)

| ID | Question | Method | Metric | File |
|---|---|---|---|---|
| E13 | Are risks split correctly? | Compare predicted risk starts with segmentation gold; E13b on 20 corpus IPOs (no font info) | Boundary precision/recall/F1 (exact page+title match; ±1 line tolerance) | `eval_results/b/segmentation.json` |
| E14 | Are red-flag inputs extracted correctly? | Summary extraction vs gold v3 on test IPOs (dev for tuning) | NVM (Phase 1 metric), coverage | `b/summary_extraction.json` |
| E15 | Do red-flag statuses agree with hand-computed ones? | Pipeline status vs status gold | Accuracy, confusion (OK/Watch/Concern/NA) | `b/redflags.json` |
| E16 | How good is the category classifier? | TF-IDF+LR, base (3 seeds), large (1–3 seeds), teacher zero-shot on gold-150 | Macro-F1, per-class F1, confusion | `b/classifier_*.json` |
| E17 | Does the seriousness rule make sense? | Rule seriousness vs teacher seriousness (1–5) on 300 corpus risks | Spearman ρ, confusion | `b/seriousness.json` |
| E18 | Are rewrites faithful? | Human rating on gold-50 for zero-shot base, QLoRA student, teacher (blind, shuffled) | % "same meaning: yes / partly / no" | `b/simplify_human.json` |
| E19 | Are rewrites easier to read? | FKGL and Flesch Reading Ease, original vs rewrite | Mean grade-level drop | `b/readability.json` |
| E20 | Do rewrites keep numbers and certainty? | Verifier + certainty check over all rewrites of the 10 IPOs | % rejected; reasons | `b/simplify_checks.json` |
| E21 | Does the risk level relate to real outcomes? | Compute points/levels for corpus IPOs; compare with listing-day return and later return (if present) and with broker "avoid" share from the dataset Excel | Spearman ρ (points vs outcome), Kruskal–Wallis across levels, mean outcome per level, bootstrap 95 % CIs | `b/risklevel_validation.json` |
| E22 | Is "unusual" meaningful? | Spot-check 60 pairs at τ ∈ {0.75, 0.80, 0.85}; precision of "similar" | Precision@τ | `b/novelty.json` |
| E23 | Speed and robustness on unseen PDFs | 5 unseen + 3 showcase uploads on the cloud | Stage timings p50/p95; stages failed | `b/latency_cloud.json` |
| E24 | Cost | GPU seconds × price per upload | ₹ per upload (mean, max) | `b/cost.json` |

### E21 rules (important)
- Outcome data is used **only to evaluate** the already-defined points system. The thresholds come from points percentiles, **not** from outcomes.
- Report whatever comes out, including "no meaningful relationship". Suggested wording if weak: "The risk level summarises disclosed risk; past outcomes show only a weak link (ρ = …), so it should not be read as a prediction."
- Never show outcome-based statements in the product UI except the Model Lab result itself.

## 4. Result file schema
Same as Phase 1 §5.1 (`experiment`, `name`, `seed`, `git_sha`, `data`, `metrics`, `per_*`, `notes`), stored under `eval_results/b/`. The Model Lab reads them through `/api/lab/b/*` (B06).

## 5. Reporting rules (unchanged + additions)
- Always show n; 3 seeds → mean ± std; bootstrap CIs on small sets.
- Disclose: AI-assisted labels, any test-informed decision, single-seed runs, teacher-generated training data, licences.
- Keep a "where FinSight loses" section (e.g. teacher beats student on faithfulness).
