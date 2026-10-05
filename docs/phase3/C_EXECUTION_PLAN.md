# C_EXECUTION_PLAN — Phase 3, part by part (no dates)

Detail for every part in `C05_ROADMAP.md`: issue, branch, model, files, tests, planned commits, hand-work, and "done when". Order and gates come from C05; this file says **how**. If this file and C05 disagree, C05 wins and this file gets fixed in the same PR.

Conventions:
- Branch `<type>/c<x.y>-<slug>`; Conventional Commits with `Refs #<issue>`; rebase-merge; delete branch.
- New code lives in `src/finsight/<package>/`, tests in `tests/<package>/`, scripts in `scripts/`, results in `eval_results/c/` (Phase 3) — written by scripts only.
- Tests that need full documents, the corpus, weights or network are `@pytest.mark.local`; `poe test` and CI skip them.
- Every part ends: C05 box ticked, `PROGRESS.md` "Resume here" (no dates), hand-work in `docs/AKSHAT_TODO.md`, `/clear` message.

New packages in Phase 3 (each with an `__init__` docstring stating its job):
- `finsight.splits` — split manifests, leakage checks, rolling reference window.
- `finsight.bench` — FinSight Bench: build, answer parsing, blind sheets, scoring.
- Additions inside existing packages: `ingest.universe`, `ingest.fetch`, `pipeline.batch`.

---

## C0 — Setup

### C0.1 Phase 3 docs + rules
- **Issue:** "C0.1 Phase 3 docs, CLAUDE.md patch, C-ADRs, issues" · **Branch:** `docs/c0.1-phase3-docs` · **Model:** O (kickoff review) · 💻 L
- **Files:** `docs/phase3/*` (already present; fix anything the review finds), `CLAUDE.md` (C00 §5 patch), `docs/09_DECISIONS.md` + new `docs/phase3/C_DECISIONS.md` (C-ADR-01…11, status *proposed*), `docs/phase2/B07_ROADMAP.md` (absorbed parts → "moved to Phase 3 (Cx.y)"), `PROGRESS.md` (new "Resume here" for Phase 3; Phase 2 log moved to `docs/PROGRESS_PHASE2.md`), `mkdocs.yml` nav (Phase 3 section), `docs/AKSHAT_TODO.md` (Phase 3 section; dropped Phase 2 items closed).
- **Tests:** docs CI (strict build, markdown lint, freshness) green; a test that `docs/phase3/C05_ROADMAP.md` part IDs and `C_EXECUTION_PLAN.md` part IDs match (`tests/docs/test_phase3_ids.py`).
- **Commits:** `docs: add phase 3 plan`, `docs(claude): phase 3 session protocol and rules`, `docs(adr): propose C-ADR-01..11`, `docs(roadmap): mark phase 2 parts moved to phase 3`, `chore(progress): start phase 3 resume note`.
- **Also:** create GitHub issues for C0–C2 with labels `local`, `colab`, `kaggle`, `akshat` (`gh issue create`); milestones per gate (CG0…CG6).
- **Done when:** PR merged; issues and milestones exist.

### C0.2 Colab + HF + compute log
- **Issue:** "C0.2 Colab helpers, HF upload, compute-unit log" · **Branch:** `feat/c0.2-colab-infra` · **Model:** S · 💻 L + 🟠 G
- **Files:** `notebooks/colab/_common.py` (Drive mount, `Checkpointer` for JSONL generation and HF Trainer resume, `run_summary()`), `notebooks/colab/c0_rate_check.ipynb` (prints GPU type, runs a 2-minute matmul, asks for units before/after), `docs/phase3/COLAB_STEPS_template.md`, `docs/phase3/COLAB_STEPS_rate_check.md`, `scripts/log_compute.py` (appends `run_summary.json` files into `eval_results/c/compute_log.jsonl`), `scripts/hf_upload.py` (private repo create + upload folder; token from env; never printed), `.env.example` (`HF_TOKEN`, `HF_USER` names only).
- **Tests:** `_common` checkpointer resume on a temp dir (CPU); `log_compute` schema; `hf_upload` dry-run mode with a fake client.
- **Commits:** `feat(colab): shared drive and checkpoint helpers`, `feat(colab): rate-check notebook and steps`, `feat(scripts): compute-unit log`, `feat(scripts): private HF upload helper`, `docs(c03): compute budget from observed rates`.
- **Hand-work:** Akshat runs the rate-check on T4, L4, A100 and brings back `run_summary.json` files.
- **Done when:** observed units/hour per GPU committed in `compute_log.jsonl`; C03 §4 table rewritten from them (by hand in the doc is fine here: it is a plan, not a result).

**CG0 review** (prompt G in C07): docs merged · rates known · `scripts/hf_upload.py --check` passes · `kaggle kernels list --mine` works.

---

## C1 — Newest-IPO data

### C1.1 IPO universe list
- **Issue:** "C1.1 Mainboard IPO universe 2024 → latest" · **Branch:** `data/c1.1-ipo-universe` · **Model:** S · 💻 L + 👤 A
- **Files:** `src/finsight/ingest/universe.py` (sources adapters → normalised rows; dedupe by company + listing date; mainboard filter), `scripts/build_ipo_universe.py`, `configs/ipo_universe.csv` (schema C02 §2), `docs/phase3/datasheets/new_ipos.md` (draft).
- **Approach:** start from an official listing of public issues (SEBI / NSE / BSE pages). Record the source URL of every row. Mark the 10 showcase IPOs with their existing ids. Skip SME.
- **Tests:** parser tests on saved small HTML fixtures (≤ 50 KB each, committed under `tests/fixtures/web/`); dedupe; showcase-id mapping; CSV schema.
- **Commits:** `feat(ingest): universe sources and normaliser`, `test(ingest): universe parser fixtures`, `data: mainboard IPO universe 2024-latest`.
- **Hand-work:** Akshat reviews the printed table (count by year/type, any odd names) and approves or removes rows.
- **Done when:** approved CSV merged.

### C1.2 Downloader + fetch
- **Issue:** "C1.2 Polite offer-document downloader" · **Branch:** `feat/c1.2-fetch-offer-docs` · **Model:** S · 💻 L
- **Files:** `src/finsight/ingest/fetch.py` (rate limit, User-Agent, resume, sha256, status update, disk check), `scripts/fetch_offer_docs.py`, updates to `configs/ipo_universe.csv` (`status`, `sha256`, `pages` after C1.3).
- **Tests:** against a local fake HTTP server: rate limit respected, resume after interrupt, 4xx retry cap, sha256 written, disk-space stop.
- **Commits:** `feat(ingest): polite offer-document fetcher`, `test(ingest): fetcher against fake server`, `data: fetch status for universe`.
- **Hand-work:** manual downloads for the printed list (same folder `data/raw/offer_docs/`).
- **Done when:** ≥ 90 % `downloaded` or explained.

### C1.3 Batch parse + hardening (was B1.1b)
- **Issue:** "C1.3 Batch parse new documents + fixes" · **Branch:** `fix/c1.3-batch-parse` · **Model:** S · 💻 L
- **Files:** `src/finsight/pipeline/batch.py` (run upload stages per document from a list, resumable, one at a time, per-stage timeout from config), `scripts/batch_parse.py`, `eval_results/c/parse_batch.json`, fixes in `parse`/`ingest`/`risks` with regression tests, new fixture pages via `scripts/export_fixtures.py` if needed (stay ≤ 20 MB).
- **Tests:** batch resume and failure isolation on synthetic PDFs; one regression test per fixed failure.
- **Commits:** `feat(pipeline): resumable batch runner`, `fix(parse): <each real fix>`, `eval: batch parse results for new documents`.
- **Done when:** every document `parsed` or `excluded` with a reason; `parse_batch.json` committed; B07 B1.1b ticked as moved.

### C1.4 ★ Time split + leakage guard + rolling window
- **Issue:** "C1.4 Time split, manifests, leakage test, reference window" · **Branch:** `feat/c1.4-time-split` · **Model:** O · 💻 L + 👤 A
- **Files:** `src/finsight/splits/` (`assign.py` sort-by-date split with showcase overrides, `manifest.py` read/write `<artefact>.manifest.json` with IPO ids, `leakage.py`, `reference.py` window query `ipos_before(date, years)`), `configs/splits.yaml`, `configs/reference.yaml`, `tests/test_split_leakage.py`, wiring: `weaklabel`, `risks` (bank, teacher export), `risklevel`, `compare` write manifests and use `reference`.
- **Tests:** assignment is deterministic; showcase roles kept; leakage test fails on a planted test id (negative test); reference window excludes later and same-split test IPOs; property test: no IPO in two slices.
- **Commits:** `feat(splits): time-based assignment`, `feat(splits): artefact manifests`, `test(splits): leakage guard`, `feat(splits): rolling reference window`, `refactor(risklevel,compare): use reference window`, `data: freeze splits`.
- **Hand-work:** Akshat confirms printed slice counts before `data: freeze splits`.
- **Done when:** frozen; leakage test in `poe test` and green.

### C1.5 BIR link check (optional)
- **Issue:** "C1.5 Check BIR PDF links" · **Branch:** `data/c1.5-bir-links` · **Model:** S · 💻 L
- **Files:** `scripts/check_bir_links.py` (HEAD/range requests only, polite), `eval_results/c/bir_links.json`.
- **Done when:** counts reported; Akshat's backfill decision written in AKSHAT_TODO.

**CG1 review:** split frozen · parse results complete · leakage test green.

---

## C2 — Training

### C2.1 Risk bank + E13 (was B2.1a-left + B2.1b)
- **Branch:** `data/c2.1-risk-bank` · **Model:** S · 💻 L (+ 🔵 K for embeddings if the laptop is slow)
- **Files:** golden tests on real fixture pages (3 dev IPOs) in `tests/risks/`; `scripts/build_risk_bank.py` (train+dev → `risk_bank.parquet` + manifest; test/bench → `risk_eval.parquet`); `scripts/export_teacher_input.py` (C03 §3 C2.3 sampling, weights 2024+); `eval_results/b/segmentation.json` (E13/E13b); datasheet `risk_bank.md`.
- **Tests:** golden boundaries; bank excludes test/bench (leakage manifest); export sampling caps per company.
- **Hand-work:** segmentation spot-check (50) + E13b boundaries before E13 numbers are final.
- **Done when:** bank built, E13 written, teacher input exported.

### C2.2 ★ Teacher bake-off
- **Branch:** `eval/c2.2-teacher-bakeoff` · **Model:** O · 💻 L + 🟠 G + 👤 A
- **Files:** `notebooks/b2_teacher_kaggle.ipynb` generalised (or `notebooks/colab/c2_teacher.ipynb` generated from the same source) with `MODEL` parameter and `_common` checkpointing; `docs/phase3/COLAB_STEPS_teacher_bakeoff.md`; `scripts/teacher_bakeoff_sheet.py` (blind 100 rows) and `scripts/teacher_bakeoff_score.py` → `eval_results/c/teacher_bakeoff.json`; ADR.
- **Tests:** sheet is shuffled and blind (no model column); scoring maps back correctly; notebook smoke on the fake fixture set (CPU tiny model).
- **Hand-work:** run both teachers on Colab; rate the sheet.
- **Done when:** teacher chosen by the recorded rule; ADR accepted by Akshat.

### C2.3 Teacher full run (was B2.3b)
- **Branch:** `data/c2.3-teacher-full` · **Model:** S · 💻 L + 🟠 G + 👤 A
- **Files:** `docs/phase3/COLAB_STEPS_teacher_full.md`; filter run via `python -m finsight.risks.teacher_data filter`; quality-100 sheet; `eval_results/teacher_quality.json` by script; datasheet `teacher_outputs.md` updated (model, counts, drop rates, GPU hours).
- **Hand-work:** run on Colab; rate quality-100; go/no-go.
- **Done when:** go recorded (≥ 85 %), or prompt fixed and a re-run accepted.

### C2.7 Extractor v2 (parallel with C2.2–C2.3)
- **Branch:** `eval/c2.7-extractor-v2` · **Model:** S · 💻 L + 🔵 K
- **Files:** weak labels v3 over `train` (`finsight.weaklabel`, label_version 3, manifest); new Kaggle dataset version; Phase 1 fine-tune notebook with 3 seeds; `eval_results/ladder/qa_finetuned_v2_seed*.json`; ladder table regenerated; model card update.
- **Tests:** weak-label build excludes dev/test/bench (manifest); ladder includes the new row.
- **Done when:** v2 kept or rejected by dev results, recorded.

**CG2 review:** teacher accepted.

### C2.4 Classifier (was B2.4b)
- **Branch:** `eval/c2.4-classifier` · **Model:** S · 💻 L + 🔵 K + 🟠 G + 👤 A
- **Files:** split from teacher labels (`finsight.risks.classify split`, by company, manifest); TF-IDF baseline; base notebook on Kaggle (3 seeds, CLI); large notebook on Colab (`COLAB_STEPS_classifier_large.md`, 3 seeds); `scripts/export_onnx_classifier.py`; `eval_results/b/classifier_*.json` (E16); model card `risk_classifier.md`; ADR for base vs large.
- **Hand-work:** verify gold-150 (pre-filled; drawn from dev/test showcase + new test IPOs); run large on Colab.
- **Done when:** chosen model exported to ONNX; ONNX vs PyTorch dev check passes; E16 written.

### C2.5 Student simplifier (was B2.5b)
- **Branch:** `eval/c2.5-simplifier` · **Model:** S · 💻 L + 🟠 G + 👤 A
- **Files:** zero-shot bake-off script on 30 dev risks; SFT split; `notebooks/colab/c2_student_qlora.ipynb` (from the Kaggle notebook, `BASE_SIZE` 4b/8b, bf16, GGUF export); `COLAB_STEPS_student.md`; `eval_results/b/{readability,simplify_checks,simplify_human}.json`; gold-50 blind sheet; model card `simplifier.md`; ADR.
- **Hand-work:** run on Colab; rate gold-50 blind.
- **Done when:** student GGUF in `models/simplifier/` + HF private repo; E18–E20 and CPU seconds per rewrite written.

### C2.6 Novelty τ + E22 (was B2.2b)
- **Branch:** `eval/c2.6-novelty` · **Model:** S · 💻 L + 👤 A
- **Files:** `scripts/novelty_pairs.py` (dev IPOs vs bank within the reference window), `data/gold/novelty_pairs.csv`, `eval_results/b/novelty.json`, `configs/risks.yaml` τ, ADR.
- **Done when:** τ chosen by precision on rated pairs.

### C2.8 Risk-level thresholds + E17/E21 + E8r (was B2.6b)
- **Branch:** `eval/c2.8-risklevel` · **Model:** S · 💻 L
- **Files:** `scripts/corpus_points.py` (rolling window for new IPOs; corpus years for E21), `configs/risklevel.yaml` (`provisional: false`, `corpus_n`, `computed_on` as a git sha, not a date), `src/finsight/evaluate/outcomes.py` + import-guard test, `eval_results/b/{seriousness,risklevel_validation}.json`, `eval_results/guard_b.json`, explained-doc section.
- **Done when:** thresholds from data; E21 reported honestly whatever it shows.

**CG3 review:** classifier + student exported and evaluated; τ and thresholds set; extractor v2 decided.

---

## C3 — Product on real data

### C3.1 ★ Summary + financial extraction + E14 (was B1.3)
- **Branch:** `feat/c3.1-summary-extraction` · **Model:** O · 💻 L + 👤 A
- **Files:** `src/finsight/summary/` extractors per B02 (financial tables, litigation, holdings, customers, peers, auditor), `financials` stage in `upload_stages`, `summary.json` per `FinancialSummary`; tuning on dev IPOs and new `dev` slice only; `eval_results/b/summary_extraction.json` (E14) when gold v3 is verified.
- **Tests:** fixture-pack tests per field; stage wiring test; NVM scorer test.
- **Hand-work:** verify gold v3 (can happen while the code is built).
- **Done when:** `summary.json` produced for every parsed document; E14 written.

### C3.2 Red flags wired + E15 (was B1.4-left)
- **Branch:** `feat/c3.2-redflags-wired` · **Model:** S · 💻 L
- **Files:** `redflags` stage after `financials`; `scripts/redflag_status_gold.py` run → `data/gold/redflag_status_gold.jsonl`; pinned tests on 3 dev IPOs; `eval_results/b/redflags.json`.
- **Done when:** every upload gets red flags with pages; E15 written.

### C3.3 Trained models into the upload pipeline
- **Branch:** `feat/c3.3-models-in-pipeline` · **Model:** S · 💻 L
- **Files:** classifier ONNX + student GGUF loading in the worker profile; `risk_features`, `classify`, `risklevel`, `simplify` stages; priority queue (top 15 automatic, rest on click); profile config for model paths.
- **Tests:** stage graph with tiny fake models; failure paths keep the rest of the report.
- **Done when:** a new RHP upload on the laptop produces the full report.

### C3.4 Compare on the rolling window (was B3.2b, cuttable)
- **Branch:** `feat/c3.4-compare-window` · **Model:** S · 💻 L
- **Files:** `scripts/compare_reference.py` via `splits.reference`; `configs/compare.yaml` from data; peer-table parser fixes with fixture tests; compare stage wired.

### C3.5 Newest-IPO showcase
- **Branch:** `feat/c3.5-newest-showcase` · **Model:** S · 💻 L + 👤 A
- **Files:** `configs/demo_ipos.yaml` (+ the `demo` slice IPOs, picked by Akshat), X-Ray + report built for them, demo cache recorded (`poe record-demo`), landing stats from real files, library cards.
- **Done when:** the newest IPOs open instantly in the library with reports and X-Rays.

### C3.6 Report UI + Lab on the real API (was B3.1b + B3.4b)
- **Branch:** `feat/c3.6-report-lab-real` · **Model:** S · 💻 L
- **Files:** mocks regenerated from real files by script (`frontend/mocks/report.ts`, header without "synthetic"); Lab sections for E13–E24 and a **Bench** section (reads `eval_results/c/bench_*.json` through a new `/api/lab/c/bench` route, OpenAPI regenerated, TS types regenerated).
- **Done when:** every Lab section shows real files or is hidden with a reason.

### C3.7 Chat fixes
- **Branch:** `fix/c3.7-chat` · **Model:** S · 💻 L + 👤 A
- **Files:** latency profiling script and fix (reranker device / `rerank_top_n`), `eval_results/latency.json` refreshed; guard change per Akshat's decision + E8r; E7 sample hand-check recorded.

### C3.8 Hardening sweep (was B3.5b, local)
- **Branch:** `test/c3.8-sweep` · **Model:** S · 💻 L
- **Files:** Playwright suite against the real local API; fixes with tests; `docs/security_review.md` local items updated.

**CG4 review:** new RHP upload → full report on the laptop; sweep green.

---

## C4 — FinSight Bench

### C4.1 ★ Bench v1 build
- **Branch:** `feat/c4.1-bench-v1` · **Model:** O · 💻 L + 👤 A
- **Files:** `src/finsight/bench/` (`build.py`, `templates.py`, `parse_answers.py`, `blind.py`, `score.py`, `stats.py`), `bench/v1/manifest.yaml` (documents, slices, systems, task list, `frozen: false`), `bench/v1/prompts/task_{a,b,c,d}.md`, `bench/v1/questions.jsonl`, `bench/v1/rewrite_risks.jsonl`, `bench/v1/keys/` (answer keys), `bench/v1/answers/{finsight,opus,chatgpt_go}/<ipo_id>.md` templates, `data/gold/gold_v4_template.jsonl` + verify sheet, `bench/README.md` (how Akshat runs a document).
- **Tests:** template round-trip (fill a template → parser reads it back); parser flags unparseable replies; blind sheet hides systems; stats on toy data (paired bootstrap, McNemar); freeze guard test (files under a frozen manifest unchanged vs a recorded hash).
- **Hand-work:** verify gold v4 + answer keys; then Claude Code sets `frozen: true` and records hashes.
- **Done when:** `bench/v1` frozen and merged.

### C4.3 Frontier runs (Akshat)
- No branch for the runs themselves; Akshat pastes replies into the templates, then a small PR `data/c4.3-frontier-answers` commits them (they are evaluation data, not PDFs).

### C4.2 FinSight bench answers
- **Branch:** `eval/c4.2-finsight-bench` · **Model:** S · 💻 L
- **Files:** `scripts/run_bench_finsight.py` → `bench/v1/answers/finsight/*.jsonl` (+ git sha, profile, timings).

### C4.4 Scoring + blind rating + tables
- **Branch:** `eval/c4.4-bench-score` · **Model:** S · 💻 L + 👤 A
- **Files:** blind sheets for Tasks C/D → Akshat rates → `bench/score.py` → `eval_results/c/bench_v1.json`, report table generator (`poe docs-gen` block), "where FinSight loses" list.

**CG5 review:** bench v1 scored with CIs.

### C4.5 Improvement loop + bench v2
- **Branch:** `fix/c4.5-bench-loop-<topic>` (one branch per fix topic) · **Model:** O (diagnosis), S (fixes) · 💻 L
- **Files:** error analysis note `docs/phase3/bench_error_analysis.md` (bench-dev only), fixes with tests, `eval_results/c/bench_v2.json`, list of test-informed changes.

**CG6 review = FEATURE FREEZE.**

---

## C5 — Finish
- **C5.1** deploy parts per C08 (added to C05 when reached).
- **C5.2** `docs/c5.2-results`: model cards, datasheets, report §7 and abstract from `eval_results/`, explained-doc sections, README results + live link (after C5.1).
- **C5.3** tag `v2.0.0` with release notes from CHANGELOG.
- **C5.4** Akshat: report voice, slides, video, viva.
