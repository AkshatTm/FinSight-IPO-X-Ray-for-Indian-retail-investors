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
**Consequences:** the rules were tightened after reading gold-150 (test slice), so the remapped-teacher agreement (93.3 % vs 88.0 % raw) and every classifier score on gold-150 are **test-informed** and reported as such. Gold-150 has no human seriousness label: band scores on it are agreement with the teacher, and its 4 severe rows make severe recall there indicative only.
