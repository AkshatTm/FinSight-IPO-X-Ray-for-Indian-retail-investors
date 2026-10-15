# C_DECISIONS — Phase 3 decisions (C-ADRs)

Full text of the Phase 3 decisions. `docs/09_DECISIONS.md` lists them in its index. Status **proposed** until Akshat marks one accepted; C-ADR-12 was approved by Akshat at the kickoff review.

Each ADR follows the template in `docs/09_DECISIONS.md`. Where a decision came from the kickoff review, the finding number (F1–F40) is given.

## C-ADR-01 Gate-driven plan, no dates — proposed

**Context:** Phase 2 plans carried calendar dates that went stale whenever work moved.
**Decision:** Phase 3 parts are ordered by dependencies and gates (CG0–CG6), not dates. The course deadline is written in exactly one place, the CLAUDE.md header. Evaluation records (bench answers, run summaries, compute logs) keep their timestamps, because the report must say when each frontier answer set was collected (F3).
**Consequences:** `PROGRESS.md` "next" lines and C-docs carry no dates. Slack is managed by the critical path and cut line (C05 §6), not by a calendar.

## C-ADR-02 Strict time split — proposed

**Context:** Users upload new offer documents; the showcase IPOs are dated across 2025, so a percentage split would put IPOs filed after test showcase IPOs into training (F9).
**Decision:** split by offer-document date and by IPO. Every `train` document is dated before every `test` document; the cut is the earliest test-slice document. Showcase roles come from `configs/demo_ipos.yaml` (F10). Leakage is checked on committed manifests in `data/manifests/` by `ipo_id` and company key (F11, F12).
**Consequences:** train gets the corpus plus roughly 2024 and early 2025; fewer fresh training documents than a 70 % split, in exchange for a real time split. `tests/test_split_leakage.py` runs in `poe test`.

## C-ADR-03 Rolling reference window — proposed

**Context:** the code compares against a fixed 2018–2023 corpus (`risks/bank.py`, `configs/risklevel.yaml`, `configs/compare.yaml`), which is stale for 2026 documents (F15).
**Decision:** "compared with past IPOs" means IPOs dated before the document, within 4 years; corpus rows count by close year. Two references: *eval* (as of each test IPO, train + dev only, never stored in configs) and *product* (all collected IPOs before today, `product_reference` manifest, never an input to threshold fitting) (F13). Window n is reported per as-of date (F17).
**Consequences:** the bank gains `ipo_id`, `doc_date`, `split`; deciles come from a per-IPO `reference_scores` table. The corpus has no financial tables, so risk-level references come from new PDFs only, and E21 uses a risk-points-only variant (F16).

## C-ADR-04 Compute: Colab for heavy jobs, Kaggle for small ones, laptop never trains — proposed

**Context:** Google AI Pro gives 200 Colab compute units (expiring 90 days after purchase) and 2 TB Drive; Kaggle gives a free T4; the laptop has an RTX 2050 with 4 GB.
**Decision:** Colab runs the teacher and the student (Akshat starts every run from a `COLAB_STEPS_<job>.md`); Kaggle runs the base classifier and extractor v2 (CLI from a local session); the laptop parses, embeds, evaluates and serves, and never trains. Checkpoints go to local disk and sync to Drive; HF gets adapters, GGUF and ONNX only (F19, F24).
**Consequences:** the budget is planned in compute units (C03 §4) with a large reserve; C0.2 measures real rates and pins a working vLLM (F18).

## C-ADR-05 Teacher chosen by a blind bake-off — accepted (Akshat, with edits); winner Gemma-4-31B-it

**Context:** the teacher is the ceiling for both the classifier and the simplifier.
**Decision (as accepted):** three candidates, all with licences that allow training a student on their outputs: **Qwen3.8-27B-FP8** (Apache-2.0, Aug 2026), **Gemma-4-31B-it in bf16** (Apache-2.0, Jul 2026) and the baseline **Qwen3-32B-AWQ** (Apache-2.0). All run on the Colab **G4** (RTX PRO 6000 Blackwell, 96 GB) with vLLM 0.31.0, thinking off, the same prompt and JSON schema, on the same 300 train+dev risks; the filters run on every output. Akshat rates a blind, shuffled sheet of **50 risks × 3 models = 150 rows** (only risks every model kept; no model column; the key is a separate file he does not open).
**Pick rule (written as code before any rating):** highest `faithful = yes` share among the rated outputs; every model within **0.05** of the best share is tied with it; among tied models, the lowest **critical drop rate** on all 300 risks (`number_mismatch` + `certainty_changed`); if still tied, the faster run on the G4 (generation seconds). The overall drop rate, `category_correct` and 95 % Wilson intervals are reported, not used.
**Candidates considered and not taken:** Mistral-Small-4-119B NVFP4 (its own card puts no-reasoning mode at Mistral-Small-3.2 level; post-training 4-bit), gpt-oss-120b (older, always reasons), GLM-5.3-Flash and DeepSeek-V4.1-Flash (too large for 96 GB), Nemotron-3-Super (custom licence). Evidence: model cards (Qwen3.8-27B IFBench 79.5, GPQA-D 89.2; Gemma-4-31B MMLU-Pro 85.2, GPQA-D 84.3) and the C0.2 G4 timing (Qwen3.8-27B-FP8: 280 risks/min, 50/50 valid JSON on the teacher prompt).
**Consequences:** bake-off ≈ 6–7 G4 units; the full run costs ~6–7 (Qwen3.8) to ~12–13 (Gemma bf16) units. If the G4 is unavailable, an A100-80GB runs all three (slower; FP8 there is weight-only).
**Implementation (C2.2):** `finsight.risks.bakeoff` (`pick`, `critical_drop_rate`, `TIE = 0.05`) and `scripts/teacher_bakeoff.py` (`sample`, `sheet`, `score`); tests in `tests/risks/test_bakeoff.py`. Ratings by a blind AI rater (Claude, in a separate session; it never saw the key), reviewed and accepted by Akshat (`rater: ai_blind` in the result); teacher outputs are AI labels.
**Result (`eval_results/c/teacher_bakeoff.json`, 150 rows, G4, vLLM 0.31.0):** **Gemma-4-31B-it (bf16) wins on quality alone**: faithful = yes 49/50 = 0.98 (95 % CI 0.90–1.00) vs Qwen3-32B-AWQ 45/50 = 0.90 (0.79–0.96) and Qwen3.8-27B-FP8 44/50 = 0.88 (0.76–0.94); the gap 0.08 is above the 0.05 tie margin, so the tie-breaks were not needed. They point the same way: critical drop rate (`number_mismatch` + `certainty_changed`, 300 risks) Gemma 0.037, Qwen3.8 0.050, Qwen3-32B 0.087; overall drop rate 0.043 / 0.053 / 0.087; category correct 0.96 / 0.96 / 0.90 (Gemma / Qwen3.8 / Qwen3-32B). Generation for 280 risks on the G4: Gemma 62 s (~270 risks/min), Qwen3.8 41 s, Qwen3-32B 33 s. Caveats: 50 risks per model, the intervals overlap, and the rater is one AI model; the margin was fixed before rating, so the pick follows the rule. The smoke + bake-off G4 session took ~25 min (units in `eval_results/c/compute_log.jsonl`).

## C-ADR-06 FinSight Bench is pre-registered and frozen — proposed

**Context:** a "better than" claim is only credible if the test was fixed before anyone looked at results.
**Decision:** `bench/v1/manifest.yaml` lists `frozen_files` with sha256 and pins `redflags_version`; once `frozen: true`, those files never change, and a test checks the hashes. Answers and rating sheets are outputs, not frozen inputs (F31, F34).
**Consequences:** fixes after the freeze are scored on the same items as bench v2; any change motivated by a bench (test) item is disclosed as test-informed.

## C-ADR-07 Frontier systems — proposed

**Context:** the comparison should reflect what a retail investor actually uses.
**Decision:** Claude Opus in the Claude.ai app on a paid plan, and ChatGPT Go in the ChatGPT app; a new chat per document; memory and web search off; plan, exact model string, input condition and timestamp recorded per run (F37). Input ladder: full PDF, else fixed page ranges from the RHP's own table of contents, verified by Akshat, the same for both apps (F27).
**Consequences:** results describe these apps at collection time, not the underlying models in general.

## C-ADR-08 Downloader policy — proposed

**Decision:** official sources only (SEBI first, then exchange and company pages), polite rate, honest User-Agent, no scraping around bot protection (manual-download list instead), multi-part filings merged or excluded with a reason, never re-hosted (F38).

## C-ADR-09 SME IPOs excluded — proposed

**Decision:** mainboard only in Phase 3; SME offer documents have a different format and rules. Future work.

## C-ADR-10 Google Cloud trial used only at deploy — proposed

**Context:** B-ADR-16 removed the cloud code on the premise that the credit was used up; a new Google Cloud free trial is now active (F1).
**Decision:** the code stays local-only until C5.1. The trial is used only at C5.1, after a budget alert, and only on Akshat's explicit "go". No upgrade, no paid resource, no GPU quota request without that "go". Deploy code is restored path by path from `458207c^`, not by reverting the commit (F7).
**Consequences:** corrects B-ADR-16's premise; B-ADR-16's local-only rule stands for everything before C5.1.

## C-ADR-11 Bias rule for gold — proposed

**Context:** the gold scores Claude, ChatGPT and FinSight; pre-fill from any one of them could anchor the verifier (F28).
**Decision:** every gold value is verified by Akshat on the PDF page. Pre-fill mixes FinSight and Claude-chat values with the source hidden; each field records whether it was changed; the source key is applied by script afterwards to report change rates per source. Gold v4 covers Task A fields and every red-flag input (F33).
**Consequences:** more verification time (C06); AI-assisted pre-fill is disclosed (`label_source`).

## C-ADR-12 Kickoff scope: cuts 1–5, critical path and cut line — accepted

**Context:** the course deadline (CLAUDE.md header) leaves about 19 build days for about 30 parts, ~31 h of Akshat's hand-work and ~15 A100 hours (F2).
**Decision:** cuts 1–5 of C05 §5 are applied now: 8B student, BIR backfill (C1.5), large classifier, Compare-window rework (C3.4), bench Task E. The bench is 6 documents + 2 bench-dev. The critical path and the ranked cut line in C05 §6 decide any further cut. Approved by Akshat at the kickoff review.
**Consequences:** the large classifier and 8B student are not reported; the Compare tab keeps provisional, labelled data; consistency is stated as a property of a deterministic pipeline, not measured against frontier apps.

## C-ADR-13 Colab jobs exchange files through a private HF dataset repo — accepted (Akshat)

**Context:** Drive copying made every Colab run a manual relay and lost progress when a runtime died overnight.
**Decision:** inputs, per-batch checkpoints and outputs of Colab jobs live in the private dataset repo `AkshatTm/finsight-gpu-jobs` (`<job>/in/`, `<job>/out/`), moved by `scripts/gpu_jobs.py push|status|pull`; `HF_TOKEN` is a Colab secret. Notebooks resume from the repo, release the GPU when they end or crash, and take a preset plus the GPU's own quantisation kernel. Drive mode stays as a fallback. The repo is private because the corpus terms are non-commercial.
**Consequences:** a fresh runtime can resume with no manual copying; an HF token is needed in Colab; each batch is one repo commit.

## C-ADR-14 Novelty tau 0.71 from 60 rated pairs — proposed

**Context:** tau (when a past risk counts as "the same risk") was a 0.80 placeholder. The rule (lowest similarity with >= 90 % "same" and >= 10 pairs at or above it, unsure left out) was fixed in `finsight.risks.novelty_tau` before rating.
**Decision:** tau = 0.71 (rule picks 0.7103; precision 0.911 on 45 pairs, 95 % Wilson CI 0.793–0.965). Pairs are dev IPOs against their reference window; one rater (Akshat), similarity hidden. Record: `eval_results/b/novelty.json`.
**Consequences:** more risks count as "common" than under 0.80; the CI lower bound is below 0.90, so tau is stated with its interval and the single-rater caveat. `seriousness.boilerplate_novelty` (0.80) is a separate heuristic and is not changed.

## C-ADR-15 Category remap v2 from the gold-150 review; classifier gets a band head and gold-150 as test — proposed

**Context:** remap-v1 moved 799 teacher labels; the gold-150 review found its brand/reputation rule fired on consequence clauses ("… may adversely affect our business, reputation …", e.g. an IP risk) and listed tie-breaks the teacher applied unevenly (statutory dues, filing delays, pre-emptive rights, auditor modifications, offer mechanics, non-GAAP).
**Decision:** remap-v2 (`configs/category_remap.yaml`): brand/reputation fires only on the subject of the title (`subject_only`, IP titles excluded); new rules statutory dues → financial, filing delays (RoC/GST returns) → regulatory, pre-emptive rights → regulatory, auditor modifications → financial, offer mechanics → market_macro, non-GAAP → financial, listed-company compliance → regulatory; key personnel stays operations but not for titles about KMP interests, pay or cases. 502 labels change (v1: 799); `category_teacher` keeps the original. The C2.4 classifier trains a second model per seed on seriousness bands (1, 2, 3, 4 = severe) and is scored on gold-150 as a held-out test set, once, at the epoch dev chose.
**Consequences:** the rules were tightened after reading gold-150 (test slice), so the remapped-teacher agreement (93.3 % vs 88.0 % raw) and every classifier score on gold-150 are **test-informed** and reported as such. Gold-150 has no human seriousness label: band scores on it are agreement with the teacher, and its 4 severe rows make severe recall there indicative only. From here on nothing (rules, remaps, thresholds, prompts, epochs) is tuned on gold-150; it is scored only.

## C-ADR-16 Financial values: last three full fiscal years, read from the page geometry — proposed

**Context:** C3.1a reads revenue, profit after tax, operating cash flow, total borrowings and net worth. RHP summary tables are mostly unruled, their text comes out column by column, and they mix part-year (stub) columns with full years; gold v3 asks for `latest`, `latest-1`, `latest-2`.
**Decision:** `finsight.summary` rebuilds tables from word boxes and reads, in order, the SEBI restated financial summary (Summary of the Offer Document; the 40 pages before Risk Factors when that section is not detected), the Summary Financial Information statements, then the restated cash-flow pages. Yearly values are the last three **full fiscal years**; stub columns are never ranked. Net worth and borrowings are primary at the latest full fiscal year end (same column as `latest`); when the same table prints a newer part-year column, that balance is also stored as a secondary value (`net_worth_stub`, `total_borrowings_stub`, `period` = the printed date), and the evidence sentence says which is primary and which is the stub. The red-flag checks read the primary values. A printed dash or "Nil" gets its own status `stated_zero` (value 0, shown apart from a printed number) only when its row or column otherwise prints figures; otherwise it is not read; `[●]` is `placeholder`; a table without a stated unit is not read. "Total equity" stands in for "Net worth" only when no "Net worth" row exists, and the evidence names the row used. A table is not ranked at all when a year column has no readable year, a header shows two different years, or a newer column is left out without naming itself a part-year period; ranked years must be consecutive. Tuned on `dev` IPOs only (`scripts/summary_coverage.py` refuses `test` and `bench`).
**Consequences:** fewer values are found than a looser reader would claim, but a found value is tied to a page, a box and a column header. E14 scores the primary value against gold v3 `latest`; the stub value is reported alongside so either reading of "latest" can be checked. (Revised after Akshat's review: stub balances kept as secondary; `stated_zero` added.) Coverage and a cross-source agreement check are in `eval_results/c/summary_coverage_dev.json`; E14 (accuracy against gold v3 on test IPOs) runs once gold v3 is verified.
**C3.1b additions (same principle, tuned on dev):** a header above the "(₹ in million)" line is still read as the column header (Canara HSBC Life); a "year/period ended" or "Fiscal/ period ended" header counts as a date only, so the fiscal month decides whether it is a year; "twelve months ended" beside "Financial Year" columns is a trailing period (a stub) unless it ends in the fiscal month; a part-year column ending in the fiscal month after `latest` means a header bled from its neighbour, and the table is not ranked. Banks, NBFCs and insurers (C-ADR-17) also match "Total income", "Revenue", "premiums earned" and "shareholders' funds" rows when the standard rows are missing.

## C-ADR-17 Other red-flag inputs: header-anchored tables, printed values only, computed values labelled — proposed

**Context:** C3.1b reads the inputs of RF04–RF13 that are not financial-statement rows: litigation, promoter holdings and pledges, WACA, customer concentration, objects of the offer, related-party total, peers, auditor remarks and whether the issuer is a financial company. These tables are full of "Nil", "N.A." and `[●]`, and their cells hold text such as "USD 2 million" or "9^^"; PyMuPDF finds ruled tables for few of them (none of the dev peer tables).
**Decision:** a second word-box reader (`summary.anchored`) starts a table at a header word the caller names, splits each line at its first value cell, builds columns from the overlapping x-ranges of the cells and names them from the header words above; a table runs on to the next page with the same columns. On top of it: **litigation** sums the criminal-proceedings column and the "aggregate amount involved" column in rupees (a printed "Total" row is used as printed; foreign-currency amounts, footnote marks and "Not quantifiable" are left out and named in the evidence); **promoter post-offer holding** is the rightmost post-offer % column over the Promoter and Promoter Group rows of the Summary table — an RHP prints `[●]` there, which is a `placeholder`; **pledged %** is column XIII(b) of row (A) in the shareholding pattern (SEBI Table I), else a "none of the shares held by our Promoters are pledged" sentence (`stated_zero`); **identifiable promoter** is false only when the document says so; **WACA** (changed in C3.2, decided by Akshat): the red flag uses the share-weighted average over the **promoters** only (`waca_promoters`; rows before the "Selling Shareholders" heading), the Selling Shareholders' average is a separate figure (`waca_selling_shareholders`), and one `waca_holder` value per holder is kept ("Nil" counts as zero, "Negligible" and "N.A." holders are left out and named; the 1/2/3-year average rows below the table are not holders); **customers** take a printed "Top 10 customers" / "largest customer" percentage in the latest full fiscal year column; **general corporate purposes** is the printed row (`placeholder` while `[●]`), as a share of Gross Proceeds (else Net Proceeds) when both are printed, the denominator named; **related-party total** is a printed "Total" row only (nothing is added up); **peers** use `compare.peers_from_table` on ruled tables and the anchored reader otherwise; **auditor remarks** are the Summary's qualifications statement as printed plus the first Emphasis of Matter paragraph and any non-negated CARO qualification on the examination-report pages; **financial company** is a sentence saying the company is an NBFC / housing finance company, a bank or an insurer. Every computed value (a sum, an average, a share) says so in its evidence sentence; each reader runs under a guard, so one failing leaves only its field empty.
**Consequences:** RHPs leave post-offer holdings and general corporate purposes as `[●]`; the final Prospectus fills them, and gold v3 takes those rows from the Prospectus, so E14 reads the Prospectus for them when it was parsed. Related-party totals and customer shares are often not printed and stay `not_found` rather than being computed. Gold v3 carries `waca_promoters` (RF05) and `waca_selling_shareholders` (informational); the first gold template used one combined key, so verify that row set before the E14/E15 runs. Coverage per field on the dev slice is in `eval_results/c/summary_coverage_dev.json` (`share_c3_1b`); E14 (`scripts/summary_eval.py` → `eval_results/b/summary_extraction.json`) scores blanks by status and values by numeric match, and runs on test IPOs once, after gold v3 is verified.

## C-ADR-18 The 8B student is not adopted; the 4B stays the product model — proposed

**Context:** the 8B variant (`Qwen/Qwen3-8B`, hybrid thinking, chat template rendered with `enable_thinking=False`, same 10,307 / 527 pairs, LoRA r=16, bf16, 2 epochs on a G4, 1 h 46 m, 16.4 units) reached dev loss 0.342 against the 4B's 0.353.
**Decision:** keep the Qwen3-4B-Instruct-2507 student (C2.5) as the product model. On gold-50 (test slice, product post-checks, single seed) the 8B passes 30/50 against 49/50: 17 too long, 2 number mismatches, 1 certainty change; 35 of 50 rewrites exceed 60 words (mean 68.7 words against 43.2). No human sheet was made for it. It also needs about 2x the memory (5.0 GB GGUF) and CPU time.
**Checked:** the Ollama template was not the cause: the exact training format through the raw endpoint gave the same lengths (75 vs 76 words on 10 risks).
**Not investigated:** why the lower dev loss did not give shorter outputs (one seed; Q4_K_M of the merged weights; the hybrid base's non-thinking mode). A second seed or a length-aware loss would be the next step if the 8B is wanted.
**Consequences:** C3.3 loads the 4B GGUF. The 8B adapter and GGUF stay in the private job repo (`student_8b/out/`) and `models/student_8b/` (gitignored).

## C-ADR-19 Severe overrides: sentence-level facts force the high band — proposed

**Context:** C3.2 needs rule-based flags (going concern, default / loan recall, SEBI/RBI/ED orders, fraud, qualified audit) that decide the risk level regardless of the model (roadmap C3.2).
**Decision:** `redflags/severe.py` scans pages from the Summary on (minus definitions, general information and offer-procedure sections) sentence by sentence; a sentence counts when a kind's pattern matches and it holds no negation or hedge, and default / recall also needs a debt word (statutory-dues delays do not count). One override per kind, with page, the document's sentence and a mention count. `risklevel.compute(overrides=...)` sets `high`, adds the reasons first (`source: override`, `forced_by`) and leaves points, score and percentile unchanged. A qualified-opinion remark in the summary counts for `qualified_audit`.
**Consequences:** On the 55 dev RHPs about one in five documents has an override (hand-read precision looked good, recall unmeasured). A fact about a promoter-group company or a director's other company also counts, because the document states it in the same place; the sentence shown lets the reader judge. E15 does not score the overrides (gold v3 has no row for them); a hand check of the dev hits is in the PR.
