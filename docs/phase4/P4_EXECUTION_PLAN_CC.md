# P4 execution plan — CC
Status: **approved by Akshat (all six decisions yes, see §6).** Gates only, no dates (C-ADR-01); P4_PLAN keeps its own schedule.
Baseline at kickstart: `uv run poe test` 2093 passed, 3 failed (docs page, 2× `test_gold_v3_template.py`).

## 1. Conflicts between Phase 3 and Phase 4, and how I resolve them
| # | Phase 3 says | Phase 4 says | Resolution |
|---|---|---|---|
| 1 | C-ADR-02: no `test`-slice doc (110 IPOs) enters training, thresholds or prompt tuning | `excluded_ipos.json` = bench + demo + Bench v1 only | **Keep the stricter rule (flag).** Excluded = test slice + SME-excluded + showcase + Bench v1 + Platform Bench. ARGON trains on `train`, selects on `dev`. |
| 2 | C-ADR-02 again | AR-02 SOD fixtures: Jio + 9 RHPs, any year | **Flag.** Parser tuning on test docs is leakage. Ask ARGON to pick the 9 from `train`/`dev` 2024–26 docs; Jio is the one declared test-informed exception. |
| 3 | `finsight.summary` already reads the SOD from word boxes (C-ADR-16/17: financial tables, litigation, holdings, WACA, objects, RPT, auditor, peers) | CC-05 builds a "new SOD engine" from `pages.txt` text | CC-05 = a `SODResult` adapter + gap-filling on top of `summary`, keeping C-ADR-16/17 rules (printed values only, `stated_zero`, `placeholder`, 3 full FY + stub as secondary). **`pages.txt` can't test word-box readers**, so CC exports word boxes for the 10 fixture IPOs via `scripts/export_fixtures.py` (B-ADR-15 limits) and ARGON writes only `expected.json`. |
| 4 | C-ADR-19: any non-negated severe sentence forces High | Forces High only when M3/rules say `actual_event` | Phase 4 wins (refines the ADR; safer). New C-ADR-26 in CC-07. |
| 5 | C-ADR-25 / B-ADR-11: score = red-flag points + ≤4 rare high-seriousness risk points ÷ (2×checks+4); 165 train+dev refs | Severity-weighted, length-normalised, refit on 165 refs | Phase 4 wins; refit uses train+dev only (C-ADR-25 population); B-ADR-03 kept (no outcomes in fitting). |
| 6 | CLAUDE.md git: PR → CI → rebase-merge | `git merge --no-ff` straight into main | **Flag.** p4/argon → p4/cc by `--no-ff` (keeps ARGON's SHAs). p4/cc → main by PR with a merge commit (`gh pr merge --merge`), so CI runs. |
| 7 | One part per session | CC-01 + CC-02 in one session | Phase 4 wins for the kickstart only. |
| 8 | C-ADR-06 bench freeze | Platform Bench is new | Not a FinSight Bench version: it's scored under `eval_results/p4/`, `bench/v1` stays frozen. |
| 9 | Compare reference provisional, n=40 (C-ADR-21) | "Against past IPOs uses the reference set" | Keep the provisional label and min-n rule. No number gets estimated. |

## 2. Things in the Phase 4 files that are wrong for this repo
- **Bench sheet ids use underscores** (`jio_platforms_2026`). Repo ids are hyphen slugs (`jio-platforms-2026`). Ingest maps them. Better: Akshat uses hyphens.
- **The bench sheet has only the example row** (Jio, `upcoming`). Excluded/bench lists get re-exported once the sheet has its 30 IPOs.
- **Jio isn't in `configs/splits.yaml`** (it's an upload). The same probably holds for most bench IPOs, so exclusion goes by sheet id + company key.
- **"Five things to know"** is really `reports.TOP_RISKS = 5`: top 5 risks by `importance`, from stored `risks.json` (`src/finsight/reports/__init__.py`).
- **Student facts:** base Qwen3-4B-Instruct-2507, LoRA r=16, SFT split **10,307 train / 527 dev** chat rows (10,892 is the kept-teacher count), Ollama tag `finsight-student:q4`. The student also answers chat, so there are **two** prompt templates: the rewrite one (`risks/simplify.py: student_prompt`, `PROMPT_VERSION student-v1`) and the chat one (`generate/prompts.py: build_prompt`; Bench Task C uses `bench/v1/prompts/task_c.md`).
- **M4 interface mismatch:** severity today is a seriousness **band 1–4** (4 = severe; 4 and 5 merged) from a band head on the same DeBERTa. **0.892 is the category macro-F1.** Proposal: `predict_severity` returns `{"band": 1-4, "label": low/medium/high/severe, "probs"}`, and M4 must not drop category macro-F1 by more than 0.01.
- **M3 `check_id`** should be the severe kinds in `redflags/severe.py` (going concern, default/recall, regulator order, fraud, qualified audit), not RF ids.
- **`label_source`** needs a fifth value, `model`, for classifier-predicted bank columns.
- **`classifier_test.jsonl`** = gold-150 (human, C-ADR-15), not a held-out split. Bench v1 = 7 test-slice showcase IPOs (C-ADR-24).
- **Cache:** `doc_id` = sha256 prefix (B-ADR-14) stays the URL key. The new analysis key sits beside it. There is no `pipeline_version` today.
- **Paths:** CC-03 code goes in `src/finsight/bench/platform.py`; top-level `bench/` holds only frozen bench data. Docs regen is `scripts/docs_gen.py`. `tests/ml/` is ARGON's except `test_no_leakage.py` (AGENTS.md wins over the P4_GIT table).
- **Git state:** `train/c2.5-student` (not on origin) is 5 commits ahead of `origin/main`. Local `main` is 49 behind origin. Stale worktrees sit under `.claude/worktrees/`; I leave them alone.
- **Large handoff files won't reach ARGON.** Gitignored files don't cross clones/worktrees or reach Colab. Plan: commit gzip JSONL ≤ 5 MB. Larger (risk bank, SFT set) go to the existing private HF dataset repo (C-ADR-13), path in README. **Needs your OK.**

## 3. Per task
| ID | Touches | Tests added | Model | Sessions |
|---|---|---|---|---|
| CC-01 | git (PR `train/c2.5-student`→main, tag `v1.0`, `p4/cc` + `p4/argon`), `.gitignore`, `data/gold/`, `docs/reference/` via `docs_gen.py`, CLAUDE.md + addendum, `BLOCKED.md` (delete) | none (3 red → green) | Sonnet | 0.5 |
| CC-02 | new `src/finsight/handoff/` (export, baselines), `scripts/export_handoff.py`, `ml/handoff/**` | `tests/handoff/test_export.py` (tiny fixtures), `tests/ml/test_no_leakage.py` | Sonnet | 1 |
| CC-03 | `src/finsight/bench/platform.py`, `scripts/platform_bench.py` | `tests/bench/test_platform.py` (synthetic xlsx: ids, units, bad rows, scorer) | Sonnet | 1 |
| CC-04 | `jobs/` (new `preflight.py`, `pipeline.py`, `runner.py`, `model_stages.py`), `storage/`, `db/` + Alembic (status, `degraded_reasons`, fingerprint), `api/routes_uploads.py` + `ipos.py` (DELETE, re-analyse), `configs/config.yaml` `pipeline_version`, `scripts/purge_degraded.py` | `tests/jobs/test_preflight.py`, `test_cache_key.py`, `tests/api/test_delete_reanalyse.py` | Sonnet | 1.5 |
| CC-05 | `summary/sod.py` (`SODResult`), section patterns in `parse/` | `tests/summary/test_sod_fixtures.py` (one case per fixture, gate ≥8/10) | **Opus** | 2 |
| CC-06 | `summary/financials.py` (+EPS, NAV, total income, equity capital), new `summary/strengths.py`, `summary/derived.py` (growth, PAT margin, D/E, CFO), `holdings.py` pre-offer | per-module unit + `tests/fixtures/real` cases | Sonnet | 1 |
| CC-07 | `redflags/` (`rules.py`, `inputs.py`, new `events.py` negation rules, 7 insight checks), `configs/redflags.yaml`, `risklevel/` + `configs/risklevel.yaml`, refit via `scripts/score_reference_ipos.py`, C-ADR-26 | event-rule table tests, Jio-style negation cases, risk-level property tests (no length monotonicity) | **Opus** | 2 |
| CC-08 | `frontend/` (Risks, Financials, Overview, Red flags v2, Compare, cache UI), `compare/` (company name, `−₹`, RoNW/P/E from Basis), `openapi.json`, types, MSW, Playwright | Vitest per component, Playwright flow, `tests/compare/` | Sonnet | 2 |
| CC-09 | loaders behind `risks/classify.py` (M4), `redflags/events.py` (M3), reports ranking (M2), `configs` `models.<id>.version`, Ollama tag switch (M1) | integration test per delivery with a stub `predict.py`, fallback test | Sonnet | 1.5 |
| CC-10 | `scripts/p4_rerun.py`, `eval_results/p4/P4_SCORECARD.md` (generated) | scorecard generator test | Sonnet | 1 |
Total about 13.5 sessions. Every task ships docs in the same PR, ticks `PROGRESS_CC.md`, and posts to `to_argon.md`.

## 4. CC-02 handoff exports (source → `ml/handoff/...`)
- `data/splits_by_ipo.json` ← `configs/splits.yaml` (ipo_id, company_key, slice, source, doc_date) + roles from `configs/demo_ipos.yaml`.
- `data/excluded_ipos.json` ← test slice + `excluded` from `splits.yaml`, `configs/demo_ipos.yaml`, `bench/v1/manifest.yaml` IPOs, `data/gold/excluded_ipos.txt`, Platform Bench sheet `IPOs` tab. Each id carries a `reason`.
- `data/risk_bank.parquet` ← `data/processed/bank/risk_bank.parquet` (train+dev, 29,677 rows), joined with teacher labels `data/processed/teacher/labels.clean.jsonl` (`ai`) and classifier category/band where there's no teacher row (`model`). `risk_eval.parquet` is **not** exported.
- `data/classifier_{train,dev,test}.jsonl` + `labels.json` ← `data/processed/kaggle/risk-classifier/`.
- `data/student_v1_train.jsonl` / `student_v1_dev.jsonl` ← `data/processed/kaggle/simplify/{train,dev}.jsonl` (made by `python -m finsight.risks.simplify split` from `teacher/simplify.clean.jsonl`).
- `data/student_prompt_template.txt` (rewrite) + `student_chat_template.txt` ← rendered by code from `student_prompt()` and `build_prompt()`, with one example each.
- `data/serious_finding_hits.jsonl` ← new export running `redflags.severe.detect` over every parsed doc (`data/processed/<id>/`, `batch/`). Fields: id, ipo_id, slice, kind, page, sentence, 2 sentences of context each side.
- `data/five_things_selection.jsonl` ← stored `risks.json` → top 5 by `importance` (method recorded). Bank IPOs without stored risks are listed as a gap.
- `data/bench_v1/` ← copies of `bench/v1/{manifest.yaml,scoring.yaml,items,keys,prompts,inputs}`, for eval only, never training.
- `data/gold/` ← `gold150.jsonl`, `simplify_gold50_sheet.csv` + `_ratings.csv`, `gold_v3_summary.jsonl`, `gold_v3_1_summary.jsonl`.
- `eval/run_bench.py` → `scripts/bench_run.py` + `bench_score.py` for an Ollama tag. `eval/run_classifier_eval.py` → `risks/clf_metrics.py` on prediction files, 3-seed mean ± sd.
- `eval/baselines.json` ← re-scored from saved outputs: `eval_results/c4/bench_summary.json` (Tasks A/B/C), `models/risk_classifier/metrics*-{13,42,2026}.json` (macro-F1 0.892, severe recall 0.56), the gold-50 student eval in `eval_results/c/`. Event-rules and M2 baselines start `null` (filled in CC-07 / by M5).
- `context/*.md` (summary, phase3 models with ADR refs, `interfaces.md` = contract §C + the fixes in §2), `colab/setup_cell.py` + `requirements_colab.txt` from the pins in `scripts/make_student_notebook.py` / `make_teacher_notebook.py`.
- **CC-01 data cleanup:** restore the committed empty `gold_v3_template.jsonl` and move the working copy to `gold_v3_labelled.jsonl`. Commit `gold_v3_summary`, `gold_v3_1_*`, `gold_v3_review.csv`, `redflag_status_gold*.jsonl`, `e7_handcheck.csv`, `apply_gold_v3_prefill.py`, `gold_v3_prefill_part1.jsonl`. Drop the `.bak`. Check the `asr_references.csv` / `simplify_gold50_sheet.csv` diffs: if they're line-ending only, revert; otherwise commit as your edits. Gitignore the run logs and `data/platform_bench/*` except `README.md` (the xlsx example row may hold platform text, so no template gets committed unless you say so).

## 5. Risks, and what I cut first if behind (follows P4 gates)
- **ARGON's SOD fixtures arrive late → CC-05 stalls.** Meanwhile I build `SODResult` over `summary` on dev docs. G1 fail → SOD scope = financials + litigation + promoter holding.
- **Bench sheet / gold v4 not ready → no scorecard.** The CC-03 scorer runs on synthetic data, and G3 reports what exists.
- **Laptop re-run of 30 IPOs is slow** (CPU reranker, student). Runs overnight, resumable per IPO.
- **Cut order:**
  1. Student rewrite of strengths
  2. Financials chart + unit toggle (table stays)
  3. Insight checks beyond contingent liabilities / negative CFO / OFS share
  4. M2 integration (top 7 by `importance`)
  5. SOD scope (G1 rule)
  6. M3 → rules only (G2 rule)
- **Never cut:** preflight + degraded status, event rules, leakage test.

## 6. Decisions (Akshat, approved)
1. Exclusion = all 110 test-slice IPOs + SME + demo + Bench v1 + Platform Bench (Jio included). `excluded_ipos.json` and the leakage test follow.
2. ARGON picks 9 SOD fixtures from train/dev; Jio is the one disclosed exception. Flow: ARGON proposes ids, CC exports word boxes, ARGON writes `expected.json` only.
3. Phase 4 merges are PRs with a merge commit (no rebase-merge).
4. Large handoff files via the private HF dataset repo; small gzips + SHA256 + HF path/revision in `ml/handoff/README.md`.
5. M4 returns `{band 1-4, label, probs}`; `label_source: model` added; `baselines.json` carries real severity metrics, 0.892 category macro-F1 is a guardrail.
6. Platform Bench sheet stays out of git. Ids normalised to hyphen slugs (`jio-platforms-2026`).
Extra: M1 has two frozen templates (chat primary, rewrite no-regress). CC-05 starts with a Jio diagnosis report.
