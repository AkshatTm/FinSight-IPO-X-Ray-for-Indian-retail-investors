# Akshat's to-do

## Phase 3 (now): in critical-path order (C05 §6, C06)

Every Claude Code part starts with the Phase 3 resume prompt R (`docs/phase3/C07_PROMPTS.md`) plus the part line. Hours are estimates (C06).

### Before C0.2 (setup, ~1 h, C06 §1)
- [ ] Colab: create `MyDrive/FinSight/` in Google Drive; connect and disconnect once each on T4, L4 and A100 to see they are offered.
- [ ] Hugging Face: create a **write** token; put it in `.env` as `HF_TOKEN=` and `HF_USER=AkshatTm` (never paste it in chat); add the same token as a Colab secret named `HF_TOKEN` (Colab → key icon → Add secret, notebook access on).
- [ ] Kaggle: run `kaggle kernels list --mine` on the laptop; it must list your kernels without an error (phone-verified account, GPU on).
- [ ] Laptop: at least **15 GB** free disk.
- [ ] Frontier apps: Claude.ai paid plan with Opus; ChatGPT Go active. In both, turn **memory/personalisation off** and **web search off**; write the plan names into `bench/README.md` when C4.1 creates it.
- [ ] Google Cloud: open the console once and note the remaining trial credit (don't create anything).

### C0.2 (merged): vLLM smoke on the L4, ~15 min
- [ ] Rates are already logged (T4 1.07, L4 1.54, A100 6.77 units/h). Only the **vLLM pin** is pending: follow `docs/phase3/COLAB_STEPS_rate_check.md` on the **L4** (`RUN_VLLM = True`), then tell Claude "vLLM pin is back" with the `vllm_pin` value. Until then C2.2/C2.3 notebooks keep `VLLM_PIN` as a parameter.
- [ ] Check `uv run python scripts/hf_upload.py --check` passes (needs `HF_TOKEN` in `.env`) and `kaggle kernels list --mine` works (CG0).

### C1.1 (merged): IPO list, ~5 min, optional
- [ ] Skim `docs/datasheets/new_ipos.md` and `configs/ipo_universe.csv` (289 rows: 2024 = 94, 2025 = 98, 2026 = 97). The overnight run pre-approved it; 2026 is above your ~80 estimate (many RHPs filed in September for issues not open yet, plus some SME-looking Prospectus-only rows that C1.3 will flag). Drop rows you dislike by setting `status` to `excluded` with a `reason`.

### C2.2 teacher bake-off (code merged; needs the frozen split + the vLLM pin first), ~1 h + 30 min rating
- [ ] After C1.4 is frozen and the bank is built: `uv run python scripts/teacher_bakeoff.py sample`, then follow `docs/phase3/COLAB_STEPS_teacher_bakeoff.md` (A100, ~7–10 units), then rate the blind sheet. Note: C2.2 is an Opus-marked part that was done on Sonnet overnight — review `src/finsight/risks/bakeoff.py` (the pick rule) and C-ADR-05 before you rely on it.

### C1.4 confirm the split, then freeze (~5 min) — NOT frozen overnight
- [ ] The overnight run did a dry run only. Reason: the pre-confirmed checks require `bench` non-empty, but `bench` is a subset of `test` that C4.1 sets (C02 §4), so it is empty by design at this point. Everything else held: train cut 2025-06-19 (earliest test document); train 499 (110 new + 389 corpus), dev 55, test 110 (103 new + 7 showcase), all test dates after the cut, 14 excluded; eval window 256-317 IPOs per test IPO; demo IPOs nityas-gems-and-jewellery-india-2026, srit-india-2026, shah-investor-s-home-2026. If you agree, run `uv run python -m finsight.splits build --freeze`, commit `data: freeze splits`, then the real C2.1 (`scripts/build_risk_bank.py`, `scripts/export_teacher_input.py`).

### C1.2 / C1.3 data results (skim, ~10 min)
- [ ] Fetch finished: 289 universe rows, all PDFs downloaded (no manual downloads needed; 6 network errors succeeded on retry). Parsed 275; excluded 14: 12 SME covers (C-ADR-09) and 2 whose risk factors are unnumbered (`priority-jewels-2026`, `kanohar-electricals-2026`; the segmenter needs numbered headings). Skim `configs/ipo_universe.csv` (2026 has more rows than expected: SEBI lists filings, not completed IPOs) and `eval_results/c/parse_batch.json`. `patel-retail-2025` yielded only 18 risks: worth a look.

### C2.3 teacher full run (code and steps merged), ~2–4 h Colab + 30 min rating
- [ ] After the bake-off pick: `uv run python scripts/export_teacher_input.py`, then `docs/phase3/COLAB_STEPS_teacher_full.md` (A100, ~14–27 units), rate the quality-100 sheet, go/no-go (≥ 85 %).

### C2.5 student (notebook and steps merged), ~1–2 h Colab
- [ ] After CG2: `uv run python -m finsight.risks.simplify split`, then `docs/phase3/COLAB_STEPS_student.md` (smoke on a T4 with `nf4`, then the real run on an L4/A100); rate the gold-50 sheet for the zero-shot bake-off first.

### C2.4 classifier (code merged), ~30 min rating + 3 Kaggle runs
- [ ] After CG2: `uv run python -m finsight.risks.classify split`, `uv run python scripts/classifier_kaggle.py manifests`, `... dataset --username <you>`, then `push smoke`, `status`, `fetch`; if it is green, `push 13`, `42`, `2026` and `fetch` each (Claude can run these); `summary` writes E16 (must beat TF-IDF on dev).
- [ ] Verify the pre-filled gold-150 (drawn from dev/test showcase + new test IPOs) so E16 can also report gold; then export ONNX (`scripts/export_onnx_classifier.py`).

### C2.6 novelty threshold (code merged), ~30–40 min rating
- [ ] After the C1.4 freeze and the real bank build (`scripts/build_risk_bank.py`): `uv run python scripts/novelty_pairs.py sheet`, rate `data/gold/novelty_pairs.csv` (column `same_risk` = yes / no / unsure; is it the same risk, ignoring company names and numbers?), tell Claude "novelty pairs rated". Claude runs `score`, sets `novelty.tau` in `configs/risks.yaml` from `eval_results/b/novelty.json` and writes the ADR.

### C2.8 risk-level thresholds (code merged), needs C2.4, C3.2, C3.3 outputs
- [ ] After the trained models are wired into the upload pipeline (C3.3) and every IPO has `<ipo_id>.json` (and `.flags.json`) in `data/processed/risk_bank/scored/`: `uv run python scripts/corpus_points.py scores`, then `... fit` (needs at least 30 train + dev scores); check `configs/risklevel.yaml` is no longer provisional.
- [ ] For E21 put a measured-outcome column in `data/gold/outcomes.csv` (`ipo_id,listing_gain_pct`; your own source, check it) and run `uv run python scripts/validate_risklevel.py --outcomes data/gold/outcomes.csv` with `scores --points-only` first. The result is reported whatever it shows.

### Later (prepared by each part when it is reached)
- C1.1 approve the IPO list (~15 min) · C1.2 manual downloads (list printed by the script) · C1.4 confirm split counts (~5 min).
- After CG1, start at once (biggest time risk): C4.1 verify gold v4 + answer keys + TOC page ranges (~8.5 h), then C4.3 frontier runs (~9 h).
- gold v3 verification (~1.5 h) for C3.1/C3.2; segmentation spot-check (~40 min) for C2.1.

### Phase 2 decisions still open
- Accept or change B-ADR-01..15 and the new C-ADR-01..11 in `docs/09_DECISIONS.md` (C-ADR-12 is accepted).
- "Red flags in chat" guard question (C3.7) and the copy items under "Copy to approve (Phase 2)" below.

## Needs a LOCAL session (Big Phase 2, history: open items moved to Phase 3)

> **4 Oct 2026 (B-ADR-16):** Google Cloud is gone and every part now runs locally. Items about a deploy are dropped (marked below); "after B1.3a/B1.4 merged" no longer waits for a cloud half: the next local session builds the fixture-tested code and runs it on real data in one go. Ignore the "cloud sessions merge PRs" phrase in the old prompts.

Start each with prompt L1 from `docs/phase2/B10_PROMPTS.md` (after `/clear`, `git pull` first). Tick the box when the PR is merged.

- [x] **B0.1 workspace bug (#121)** — Sun 4 Oct, Sonnet.
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull` (cloud sessions merge PRs on GitHub). Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md and the "needs a LOCAL session" list in docs/AKSHAT_TODO.md. Do part B0.1 (#121) only. Run the tests (including @pytest.mark.local ones relevant to this part) and report in one line. Do the model check (both directions). Keep the session short and specific: real documents / corpus / models / Kaggle launches / evaluation / deploy steps, one heavy job at a time, Ollama only if needed. Never deploy or spend cloud credits without my explicit "go" in chat. End with the PR merged, the AKSHAT_TODO item ticked, PROGRESS.md updated, and the /clear message (B07 §0). Bug details: <describe the click and the error here, or "unknown: reproduce by opening all 10 workspaces on the real API">.
  ```
- [x] **B0.4 fixture pack (#123)** — done 3 Oct (15 MB, 10 IPOs; gaps in `tests/fixtures/real/README.md`). Unblocks cloud B1.3a, B1.4, B2.1a.
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull` (cloud sessions merge PRs on GitHub). Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md and the "needs a LOCAL session" list in docs/AKSHAT_TODO.md. Do part B0.4 (#123) only. Run the tests (including @pytest.mark.local ones relevant to this part) and report in one line. Do the model check (both directions). Keep the session short and specific: real documents / corpus / models / Kaggle launches / evaluation / deploy steps, one heavy job at a time, Ollama only if needed. Never deploy or spend cloud credits without my explicit "go" in chat. End with the PR merged, the AKSHAT_TODO item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B1.1b harden upload checks on real PDFs (#126)**~~ — **moved to Phase 3 (C1.3)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull` (cloud sessions merge PRs on GitHub). Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md and the "needs a LOCAL session" list in docs/AKSHAT_TODO.md. Do part B1.1b (#126) only: run `finsight.ingest.validate_pdf` on the 20 showcase PDFs and the 5 unseen RHPs (type, code, pages, seconds each; print a table, never PDF text beyond 40 lines), fix detection or thresholds that fail with a regression test each (synthetic or fixture-pack based), and record the timings. Run the tests (including @pytest.mark.local ones relevant to this part) and report in one line. Do the model check (both directions). Never deploy or spend cloud credits without my explicit "go" in chat. End with the PR merged, the AKSHAT_TODO item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] **B1.2 local check: one showcase doc end to end (~5 min)** — done 3 Oct on LG Electronics (502 pages, `ready`; parse 11.8 s, risks_split 10 s; two bad risk titles fixed). Sonnet.
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md and docs/AKSHAT_TODO.md. Do only the B1.2 local check: with FINSIGHT_PROFILE=dev_light start `uv run poe api`, then upload one showcase RHP through the API (POST /api/uploads/init → POST the file → /complete, using the real sha256 from configs/demo_ipos.yaml), follow GET /api/docs/<doc_id>/events until `done`, and confirm doc_type/pages match demo_ipos.yaml, `sections.json` has `risk_factors` and `risks.json` has a plausible number of risks (print the first 5 titles only). Report per-stage timings (`progress.timings_s`) in one line; fix anything that breaks with a regression test. Never deploy. End with any PR merged, this item ticked and PROGRESS.md updated.
  ```
- [ ] **B1.5 local check: real sign-in and upload (~15 min)** — after B1.5 merged and HOSTING_SETUP_STEPS part A (Supabase Google provider) is done. Sonnet.
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md and docs/AKSHAT_TODO.md. Do only the B1.5 local check: put NEXT_PUBLIC_SUPABASE_URL/ANON_KEY in frontend/.env.local and FINSIGHT_AUTH__* in .env (never print them), run the API with auth.mode supabase (FINSIGHT_AUTH__MODE=supabase) and `pnpm dev`, sign in with Google, upload one showcase RHP and follow the processing screen to the end; then sign out and check /me/uploads asks to sign in. Fix anything that breaks with a test. Never deploy. End with any PR merged, this item ticked and PROGRESS.md updated.
  ```
- [x] ~~**B2.3b teacher run: smoke → pilot 500 → quality-100 → full (#133 follow-up)**~~ — **moved to Phase 3 (C2.3)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull` (cloud sessions merge PRs on GitHub). Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md, docs/phase2/datasheets/teacher_outputs.md and the "needs a LOCAL session" list in docs/AKSHAT_TODO.md. Do part B2.3b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) upload `data/processed/teacher/risks.jsonl` as the private Kaggle dataset `finsight-teacher-risks` with the official kaggle CLI (never print the token); (2) `uv run python scripts/make_teacher_notebook.py kernel smoke --username <kaggle user>` then `kaggle kernels push -p data/processed/kaggle/kernels/finsight-teacher-smoke`, poll status, download `raw.jsonl` + `run_summary.json` into data/processed/teacher/; if vLLM 0.8.5 or the AWQ model fails on the T4, try the fallback model in the parameters cell once, then write BLOCKED.md; (3) `uv run python -m finsight.risks.teacher_data filter` and report the drop rates; (4) the pilot (`kernel pilot`, attach the smoke raw.jsonl to resume), filter again, `teacher_data sheet` → data/processed/teacher/quality_sheet.csv for my rating (stop here and wait for my go/no-go); (5) after my go: `kernel full`, filter, write eval_results/teacher_quality.json from the rated sheet with a script (never by hand), fill the datasheet numbers, record GPU hours in PROGRESS.md. Never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B2.4b classifier training + E16 (#134 follow-up)**~~ — **moved to Phase 3 (C2.4)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B2.4b), docs/phase2/B03_MODELS_AND_TRAINING.md §4 and docs/AKSHAT_TODO.md. Do part B2.4b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) `uv run python -m finsight.risks.classify split` → upload data/processed/kaggle/risk-classifier as the private Kaggle dataset `finsight-risk-classifier` (official kaggle CLI, never print the token); (2) `uv run python -m finsight.risks.classify baseline --gold <gold-150 jsonl>` (laptop CPU) → eval_results/b/classifier_tfidf.json; (3) push notebooks/b2_classifier_base_kaggle.ipynb with SMOKE = True first (kernel-metadata like finsight.weaklabel.kaggle: GPU + internet on, the dataset attached), then the full 3 seeds, then the large notebook (1 seed); download outputs into models/risk_classifier/; (4) pick base or large by DEV macro-F1 only and record it as a proposed ADR; it must beat the TF-IDF dev macro-F1, else report that honestly; (5) `uv run --group ml --group onnx python scripts/export_onnx_classifier.py --model <chosen>/final --dev data/processed/kaggle/risk-classifier/dev.jsonl`; (6) E16 on gold-150 for every rung with a script → eval_results/b/classifier_*.json (seed count and label_source in each file, never typed by hand); (7) model card docs/model_cards/risk_classifier.md. Never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B2.5b student training + E18–E20 (#135 follow-up)**~~ — **moved to Phase 3 (C2.5)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B2.5b), docs/phase2/B03_MODELS_AND_TRAINING.md §5 and docs/AKSHAT_TODO.md. Do part B2.5b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) bake-off: zero-shot `Qwen/Qwen3-4B-Instruct-2507` vs `Qwen/Qwen3.5-4B` (both as GGUF Q4 via llama.cpp, Ollama stopped) on 30 dev risks with `finsight.risks.simplify.Simplifier`; report pass rate of the post-checks and CPU seconds per rewrite; record the pick as a proposed ADR; (2) `uv run python -m finsight.risks.simplify split` → upload data/processed/kaggle/simplify as the private Kaggle dataset `finsight-simplify` (official kaggle CLI, never print the token); (3) push notebooks/b2_student_qlora_kaggle.ipynb with SMOKE = True first (GPU + internet on, dataset attached), then the full run; download `simplifier-q4_k_m.gguf` + metrics.json into models/simplifier/ (never commit weights; private HF repo only); (4) E19/E20 on the 10 IPOs and the blind gold-50 sheet for E18 (zero-shot base vs student vs teacher, shuffled) with scripts → eval_results/b/{readability,simplify_checks}.json and data/gold/simplify_gold50.csv; stop and wait for my ratings; (5) after my ratings: eval_results/b/simplify_human.json by script, model card docs/model_cards/simplifier.md. Never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B2.2b novelty threshold + E22 (#144 follow-up)**~~ — **moved to Phase 3 (C2.6)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B2.2b), docs/phase2/B02_ARCHITECTURE.md §7.1 and docs/AKSHAT_TODO.md. Do part B2.2b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) write scripts/novelty_pairs.py: for risks of the dev showcase IPOs, embed with bge-m3 (Ollama stopped) and sample 60 (risk, nearest bank risk) pairs, 20 each with similarity near τ = 0.75, 0.80, 0.85, into data/gold/novelty_pairs.csv with blank `same_risk` (yes/no) and label_source; stop and wait for my ratings (Claude chat may pre-fill; count the values I change); (2) after my ratings, compute precision@τ with a script → eval_results/b/novelty.json, choose τ by precision on these pairs, update configs/risks.yaml and record a proposed ADR; (3) run `finsight.risks.add_features` with the real bank on the 10 showcase IPOs and report the novelty distribution. Never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B2.6b risk-level thresholds + E17/E21 + E8 re-run (#146 follow-up)**~~ — **moved to Phase 3 (C2.8)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B2.6b), docs/phase2/B02_ARCHITECTURE.md §7.3–7.4, docs/phase2/B04_EVALUATION.md (E8, E17, E21) and docs/AKSHAT_TODO.md. Do part B2.6b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) write scripts/corpus_points.py: run red flags + risk features + `finsight.risklevel.compute` over every 2018–2023 corpus IPO, write the score distribution and 11 reference quantiles to configs/risklevel.yaml with `computed_on`, `corpus_n` and `provisional: false` (thresholds: bottom third / top third of scores unless the distribution says otherwise; record a proposed ADR); (2) E17 seriousness vs the teacher's 1–5 on dev → eval_results/b/seriousness.json; (3) add src/finsight/evaluate/outcomes.py (the only module allowed to read listing-day outcomes; a test asserts nothing else imports it) and run E21 with an honest write-up in docs/10_FINSIGHT_EXPLAINED.md C29 → eval_results/b/risklevel_validation.json; (4) re-run E8 on both question sets after the risk-level guard change → eval_results/guard_b.json. Never hand-edit results; never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] **B2.7 smoke deploy — dropped: no cloud — (#148 follow-up)** — **only after GCP billing is on and you say "go"**. Sonnet.
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B2.7), docs/runbooks/DEPLOY_RUNBOOK.md, deploy/gcp/README.md and docs/AKSHAT_TODO.md. Do part B2.7 only, and only because I said "go" in this chat. Run the tests and report in one line. Do the model check (both directions). Steps: (1) check `uv run python scripts/check_env.py --profile cloud` (names only, never print values); (2) follow DEPLOY_RUNBOOK steps 2–6 for the CPU path only (no GPU job): I run every gcloud command that creates or changes a paid resource myself after you show it; (3) run scripts/cloud_smoke.py with one small offer document and write eval_results/b/smoke_deploy.json (cold start, stage timings); (4) scale to zero and confirm no instance is running. Never print secrets. End with the PR merged, B2.7 ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B3.2b compare reference + real peer tables (#150 follow-up)**~~ — **moved to Phase 3 (C3.4, cut)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B3.2), docs/phase2/B05_UI_SPEC.md §5.6 and docs/AKSHAT_TODO.md. Do part B3.2b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) write scripts/compare_reference.py: over the 2018–2023 corpus IPOs compute issue size, OFS share, insider price gap and P/E (from the facts and red-flag numbers), write 11 quantiles per metric with computed_on, corpus_n and provisional: false into configs/compare.yaml (never hand-type numbers); (2) run `finsight.compare.peers_from_table` on the Basis for Offer Price tables of the 10 showcase IPOs and the fixture pack; fix the parser for any header it misses and add those tables as tests (`tests/fixtures/real/`, via scripts/export_fixtures.py only); (3) wire the `compare` stage into the worker pipeline once B1.4 facts exist; (4) refresh frontend/mocks/report.ts from a fixture report. Never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B3.1b report page against the real local API (#151 follow-up)**~~ — **moved to Phase 3 (C3.6)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B05_UI_SPEC.md §5–6 and docs/AKSHAT_TODO.md. Do part B3.1b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) build one showcase IPO end to end with the upload pipeline (`uv run poe api` + `cd frontend && pnpm dev` without mocks); (2) open `/reports/<doc_id>` and check each tab against B05 §5–6: offer line, risk-level card with the disclaimer always visible, red flags order, risks sort/search/filter, "Explain this" (needs the student GGUF or the fallback), Compare; (3) regenerate `frontend/mocks/report.ts` from that real `report.json`, `redflags.json` and `risks.json` (a script, never hand-typed numbers) and remove "synthetic" from its header; (4) fix any UI bug found, with a test. Never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
- [ ] **Docs site publish — optional, needs your go (GitHub Pages is free) — (#153 follow-up, needs your go)** — the MkDocs site builds in CI but is not published. When you want it live, say "go" in a cloud or local session: it adds a GitHub Pages deploy job to `.github/workflows/docs.yml` (Settings → Pages → Source: GitHub Actions). Free; nothing else is needed.
- [x] **B4.1 runbook check — dropped: runbooks for deploy were removed — (#153 follow-up)** — after the first deploy (B2.7, needs your go). Sonnet. ~45 min.
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md and docs/runbooks/. Do the B4.1 runbook check only. Run the tests and report in one line. Do the model check (both directions). Walk through docs/runbooks/DEPLOY_RUNBOOK.md, ROLLBACK.md, MONITORING.md and ROTATE_SECRETS.md once against the deployed project with Akshat watching (no new paid resources; stop and ask before any step that costs money), fix every step that is wrong or unclear, fill each runbook's "Last tested" line, and check the README quickstart from a clean clone on Windows. Never print or commit secrets. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
- [x] ~~**B3.5b Playwright sweep on the real API~~ — **moved to Phase 3 (C3.8)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B3.5), docs/security_review.md and docs/AKSHAT_TODO.md. Do part B3.5b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) run the Playwright suite against the real API (`uv run poe api` + `cd frontend && pnpm dev` without mocks) and then against the deployed site, fixing each failure with a test; (2) on the deployed stack, log the X-Forwarded-For header the API receives behind the Vercel rewrite and Cloud Run, set `uploads.trusted_proxy_hops` in the cloud profiles to match, and test that two browsers get separate simplify limits; (3) try an upload over 50 MB through the signed URL and check that `complete` refuses it with `too_large`; (4) check that a non-admin account gets 403 on /admin/costs and the admin sees today's jobs; (5) replace the Tier 1 rates in `costs.rates_usd` with the asia-southeast1 Cloud Run job rates from Google's pricing page (and the L4 GPU rate), then set `costs.provisional: false`; (6) update the "Verify on the deployed stack" list in docs/security_review.md. Never spend credits beyond the deployed project's normal use, never print secrets. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B3.4b E23/E24 and E7 on the cloud profile~~ — **moved to Phase 3 (C3.6)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B3.4), docs/phase2/B04_DATA_AND_EVALUATION.md (E7, E23, E24), docs/phase2/B06_API_CONTRACT.md §5 (Lab file shapes) and docs/AKSHAT_TODO.md. Do part B3.4b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) upload 5 unseen offer documents and the 3 showcase ones to the deployed stack; (2) write a script that reads the job rows (`progress.timings_s`, `progress.cost_estimate`) and writes eval_results/b/latency_cloud.json and eval_results/b/cost.json in the B06 §5 shapes (never hand-typed numbers; cost in ₹ with the exchange rate and its date recorded in the file); (3) re-run E7 against the `cloud` profile into eval_results/b/e7_cloud.json; (4) check that the Model Lab "Speed and cost" section appears and matches the files; (5) `uv run poe docs-gen` so the evaluation page picks up the new files. Never spend credits beyond the deployed project's normal use. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B1.4 local follow-up: status gold + E15 (#130)**~~ — **moved to Phase 3 (C3.2)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B1.4), docs/phase2/B04_DATA_AND_EVALUATION.md (E15) and docs/AKSHAT_TODO.md. Do only the B1.4 local follow-up. Run the tests and report in one line. Do the model check (both directions). Steps: (1) check every row of data/gold/gold_v3_summary.jsonl has `label_source` containing `akshat_verified`, then `uv run python scripts/redflag_status_gold.py` and commit data/gold/redflag_status_gold.jsonl; (2) add tests that run the gold v3 values of 3 dev IPOs through `finsight.redflags.evaluate` and pin their statuses; (3) wire `redflags.build` into the upload stages after `financials` if B1.3a has not; (4) run the pipeline on the 20 showcase documents and write eval_results/b/redflags.json (E15: status accuracy per check vs the status gold, n and 95 % intervals) with a script, never by hand; (5) `uv run poe docs-gen`. Never tune thresholds on test IPOs. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- [x] ~~**B2.1b risk bank + E13/E13b + teacher input (#132 follow-up)**~~ — **moved to Phase 3 (C2.1)**; the prompt below is history, use the Phase 3 resume prompt (C07 R).
  ```text
  Resume FinSight Big Phase 2 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md (B2.1b), docs/phase2/B02_ARCHITECTURE.md §6–7.1, docs/phase2/B04_DATA_AND_EVALUATION.md (E13, E13b) and docs/AKSHAT_TODO.md. Do part B2.1b only. Run the tests and report in one line. Do the model check (both directions). Steps: (1) segment the Risk Factors of every corpus IPO with `finsight.risks.segment_text` (PDF pages with `segment_pages` where the corpus has them) and print counts per year, never risk text beyond 40 lines; (2) `scripts/build_risk_bank.py` → data/processed/bank/risk_bank.parquet with bge-m3 embeddings of title + first 2 sentences (showcase and gold IPOs excluded, with a test); (3) E13 on the spot-check and E13b on data/gold/segmentation_gold.jsonl → eval_results/b/segmentation.json by script; (4) `scripts/export_teacher_input.py` (5,000 risks, 40–600 words, ≤ 20 per company, stratified) and upload it as the private Kaggle dataset `finsight-teacher-risks` (official kaggle CLI, never print the token); (5) `uv run poe docs-gen`. Never deploy or spend cloud credits. End with the PR merged, this item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
  ```
- Later local parts ( B1.3b, B1.4 E15, B2.1b, B2.3b …) are added here by the cloud session that unblocks them, each with its prompt.

## Phase 2 hand-work (history; superseded by the Phase 3 section above)
- Sat 3 Oct: approve the B0.2 PR; say whether Colab Pro is bought (the plan is Kaggle-first either way).
- Sun 4: claim the $100 cloud credit (deadline Wed 7 Oct, 23:59 PT); describe the B0.1 bug if you can.
- Mon 5: follow `docs/phase2/HOSTING_SETUP_STEPS.md` part A (Supabase, Vercel, Kaggle); part B (Google Cloud billing) later, when you're ready.
- Wed 7: 5 unseen RHPs → `data/raw/unseen/`.
- Thu 8 – Fri 9: gold v3 pre-fill (Claude chat) from `data/gold/gold_v3_template.jsonl` + verify.
- Accept or change B-ADR-01..15 in `docs/09_DECISIONS.md`.

## Copy to approve (Phase 2)
- Hindi drafts for every upload, processing and My uploads string (`frontend/lib/content/upload.ts`; B05 gives English only).
- Processing "Details" lines (not in B05): "Something went wrong in this step. The rest of the report is not affected." and "This step needs an earlier step that didn't finish." (`proc.reason.*`).
- Hindi short label "डीआरएचपी" for DRHP (`doc.drhpShort` in `frontend/lib/i18n.ts`, B1.1a builder draft).
- B05 lines marked `[copy: Akshat to approve]`: uploads-paused line, `hash_mismatch` rejection, About "unusual means rare among 2018–2023 IPOs".
- Red-flag sentence templates missing in B05 §5.4 (RF02 NA, RF04 NA for a DRHP, RF06/RF09/RF12/RF13 NA) use the default "FinSight couldn't find this in the document."; confirm or write specific ones.
- Red-flag drafts (B1.4a, `DRAFT_SENTENCES` in `src/finsight/redflags/rules.py`): "Made a profit of ₹{pat} in the latest year." (RF01 OK when an earlier year was a loss), "There are criminal cases involving the company, promoters or directors." (RF08 Watch when no count is given), "The top customer brings in {t1}% of revenue{t10_part}." (RF10 OK) and "The top 10 customers bring in {t10}% of revenue." (RF10 when only the top 10 is given).
- The 13 "How this check works" texts (`rule:` in `configs/redflags.yaml`, shown on `docs/reference/redflags.md`): builder drafts.

## Phase 1 leftovers (after BG1 unless they block)
- Review ADR-022 (now the fallback), ADR-053, ADR-054; hand-check the E7 samples; Hindi strings; ASR references (details in the sections below).

---

# Phase 1 to-do (collected during the overnight frontend run)


## Needs your decision
- About "Known limits" still says "Covers 10 IPOs, not every IPO." (Phase 1 copy). With uploads that is no longer true for reports; it still holds for chat. Keep, reword (e.g. "Chat covers 10 IPOs; reports work for any uploaded offer document.") or drop? (B3.4a left it as is.)
- **Questions about "red flags" in chat (B2.6a).** The guard still refuses "does this IPO have red flags?" as a rating question (it was written before the Red Flags tab existed). I left it blocked tonight because unblocking changes the E8 results. Options: (a) allow it and answer with the Red Flags tab's facts, re-checked in the B2.6b E8 re-run; (b) keep it refused with a pointer to the tab. Recommendation: (a).
- **Risk-level placeholders.** `configs/risklevel.yaml` holds made-up thresholds (`provisional: true`, `corpus_n: 0`) until B2.6b. The UI must show "provisional" while that flag is on.

## Hindi strings to review (`[HI review]` in docs/12_FRONTEND_SPEC.md, plus builder-drafted)
- Every `[HI review]` string in docs/12_FRONTEND_SPEC.md is used verbatim in frontend/lib/i18n.ts (nav, footer, library). Landing, Lab and About Hindi get added with their steps.

## New copy to review (strings the spec did not provide)
- Site copy (B3.4a): Hindi for every new B05 §2 / §8 line (`land.sub`, `land.cta`, `land.sample`, `land.free`, `land.get.*`, `land.no.1`–`3`, `land.stat.risks`, `land.stat.corpus`, `how.row3`, `how.r*`, `about.limits.6`–`8`), plus the English fallback "Compare each risk with past IPOs" (`how.r6.h0`) shown while `corpus_n` is 0.
- Model Lab Phase 2 (B3.4a, `frontend/lib/content/lab.ts`): every `labb.*` line except the headings, the two quoted "What this shows" lines (§7.1, §7.2) and the rewrite honesty line, which are B05 verbatim; all Hindi.
- Admin costs page (B3.5a, `frontend/lib/content/admin.ts`; not in B05): every `admin.*` line in English and Hindi, and the API's 403 message "This page is only for the FinSight admin." (`err.forbidden`). Admin-only, so low priority.
- Compare tab (B3.2, `frontend/lib/content/report.ts`): issuer chip "This IPO"; "Provisional: the past-IPO figures are placeholders until they are computed from 2018–2023 IPOs."; the English twin of B05's Hindi note, "This risk report is in English only for now." (only the Hindi line is shown).
- Report page (B3.1, `frontend/lib/content/report.ts`; B05 gave no copy): "Link copied" (`rep.copied`), "{n} pages" (`rep.pages`), "This part isn't ready yet." (`rep.notReady`), "Provisional: the thresholds are placeholders until they are computed from 2018–2023 IPOs." (`rl.provisional`), "Not applicable" (`rf.not_applicable`), "page {p}" (`rf.page`), "No risks match." (`rk.none`), and "This risk report is in English only for now." (`rep.englishOnly`, English twin of B05's Hindi note). "Show in document" and the Ask/Facts/Document tabs for uploaded documents are not built yet.
- API `worker_unavailable` (B3.3a, 503 when Cloud Run cannot start the worker): "We couldn't start processing. Please try again later." The upload page shows its generic error for this code.
- Library: HI for the buttons/links the spec gave only in English: "Clear search" -> "खोज हटाएँ"; "Open Ather Energy" -> "Ather Energy खोलें"; filter group and sort labels (sr-only) "Sort" -> "क्रम".
- Keyboard shortcuts dialog (spec 17 asks for it, gives no copy): `keys.*` in frontend/lib/i18n.ts, EN and HI both drafted by the builder.
- Facts pane: Hindi tooltips for every field (spec 12 gave English only), `facts.chip` ("{doc} पन्ना {n}"), "Show fewer" / "+{n} और", "Details" label, `lib/content/fields.ts` and `facts.*`/`pop.*`/`split.*` in i18n.ts are builder drafts where the spec had no Hindi.
- Hindi unit words after amounts in the Hindi UI (`₹2,626.00 करोड़`): spec 15 only shows English; used करोड़ / मिलियन / लाख from the unit toggle labels.

- Inspector (7.7) and glossary drawer: Hindi for the three column tooltips (`insp.help.*`) and the glossary search placeholder / "no match" line are builder drafts; the glossary shows the 17-term short definitions only, since the spec has no long ones.
- Voice: mic opens a glass-style button in CSS mode (not the library) so the composer layout stays intact. Real ASR needs P4.1 `/api/voice`; the mock returns one Hindi sentence.
- Fact labels keep the dotted underline but do not open the glossary popover (a button inside the fact-row button is invalid HTML); the Glossary button and the advice card link open the drawer instead.

- Landing: hero image is a drawn stand-in (public/landing/rhp-cover.svg), not the real Ather RHP page 3 (I may not read PDFs). Replace it with a WebP of the real page if you want; the lens position constants are in components/landing/Hero.tsx. The lens is CSS glass, not liquid-glass-react (the library element positions itself fixed and cannot be pinned over an image), see ADR-050 note. Spec 5.7 asks for the real demo-cache answer under the Hindi question: not available until P4.1, so only the question and the play button show. The spec 5.11 friend test is yours: does a newcomer get it after the first three sections? The humanizer pass changed nothing on Landing because the spec copy is fixed verbatim. Landing stats "detection" and "robust" need `/api/lab/verifier` and `/api/lab/ladder` (P4.1); until then they are hidden outside mock mode.

- How it works: spec 9 says each box opens a real example (recorded trace or screenshot). None exists yet, so the boxes are static. Add them after P4.1 records the demo cache. About Hindi (spec 10 has English only) is a builder draft: every `about.*` string. Humanizer pass: no change, copy is fixed verbatim.

- Model Lab (F7): every `lab.*` Hindi string is a builder draft except none from the spec (the spec gives Hindi only for page-level lines); headings and column names the spec names only in English are mine. The spec asks for "5 examples per heatmap cell": the lab payload carries no examples, so the grid shows numbers only. E7 answer accuracy is not measured, the retrieval note says so. The frontier section (spec 8.6) is hidden: no E9 result file. Hindi section states that the ASR references are unreviewed.

- Demo mode (F8): the step indicator Hindi (`demo.step`) is a builder draft. Before the demo run `uv run poe record-demo` (cache is not committed) and preferably with the `full` profile; v0.4.0 is yours to tag.

- Polish pass: the impeccable critique command was not run (its launcher downloads a binary on first run); I did the layout, overflow and tap-target checks by script and by eye instead. Humanizer pass on Landing, How it works and About changed nothing: the copy is the spec's, verbatim. On a phone the document toolbar still takes three rows; a one-row toolbar is a design call for you.

## Data and evaluation
- X-Ray boxes: the extractors do not store a bbox for any value (found in F6). The API now locates boxes by matching text on the page (ADR-052), which is good for numbers and names but not for every list value. Consider storing the box in the extract stage in the next pipeline pass.
- `configs/ipo_meta.yaml` (sector and listing date for the 10 IPOs) was typed from memory of public listing dates: please verify each line.
- Demo cache: `data/demo_cache/` is empty until you run `ollama serve` and `uv run poe record-demo` (about 8 questions per IPO; slow on this laptop). The Landing page and demo mode (F8) use it.
- Approve or reject ADR-052 (page addressing, `not_available`, hand-entered sector/date).
- E7 (answers on dev questions through the real orchestrator): script is ready (`uv run python -m finsight.evaluate.answers --limit 20 --profile dev_light` with `ollama serve` running). I ran only one live smoke question (Ather, "How will the money be used?", qwen3.5:0.8b: right section, no numbers in the answer). The full run and the hand-check of `eval_results/e7_sample.jsonl` are not done.
- Approve or reject ADR-051 (`forecast` guard reason; objects-of-the-offer retrieval nudge).
- `data/gold/asr_references.csv`: references are now the script you read aloud; `reviewed_by_akshat` is empty. Confirm them, then re-score ASR CER (ADR-021's 0.06 for turbo was measured on the old machine-drafted references).
- Rate `data/gold/hindi_fluency_sheet.csv`; review `advice_guard_set.csv` and `questions_*.jsonl` (from earlier PROGRESS entries).

## Backend notes the frontend found
- Thumbnails reuse the full page endpoint (`/pages/{n}`); a `?w=` or `/thumb` variant would cut payload. Decide in P4.1 (needs your review of the contract).

- The API X-Ray field has no source sentence. The popover rebuilds it from `/pages/{n}/words` around the field bbox. If P4.1 adds a `sentence` field it would be exact; for now it is derived.

- Chat: inline verdict marks show the icon with the word as tooltip and screen-reader text (spec 2.4 allows hiding the word only in dense tables; running text is treated the same). Say if you want the word printed beside each mark.
- Chat: `ask.*`, `ev.*`, `mark.open`, `cite.jump` strings and the HI forms of "In ₹ crore" / "In ₹ million" / "Reason" / "Source" are builder drafts.
- Guard reason: the contract lists `advice_intent | privacy` but the guard has forecast/rating/GMP categories (ADR-046). The UI maps any reason that is not privacy or forecast to the advice card; P3.6 should send `forecast` for the forecast rule.

## Skills and tooling notes
- impeccable's launcher (`scripts/impeccable`) downloads a self-contained binary on first run (SKILL.md Setup). I did not run it unattended; design process steps are followed from its reference/*.md instead. Say if you want the detector binary installed.
- Only humanizer ships a LICENSE (MIT). The other three skills have no licence file, so `.claude/skills/` is git-ignored; `skills-lock.json` (names, sources, hashes) is committed.
- Landing check (spec 5.11): ask a friend who has never heard of an RHP what FinSight does after the first three sections.

## Run 2 (overnight, 2 Oct)
- **Confirm the Hindi fluency scores** in `data/gold/hindi_fluency_sheet_rated.csv`. They are Claude drafts; ADR-020 now says "pending your confirmation" (an earlier line said confirmed).
- **Review ADR-053, ADR-054 and the proposed ADR-022** (deployment: Docker Space, BM25 only, 4-bit GGUF, Vercel rewrite).
- **Hand-check the E7 samples** (`eval_results/e7_sample_dev.jsonl`, `e7_sample_test.jsonl`, 20 answers each; fill `reviewed_by_akshat`). E7 is one run.
- **Review the Hindi strings** added in run 2: `land.lang.cap`, `how.link.ather`, `how.link.lenskart`, plus the glossary "i" button label and the toolbar menu strings.
- **Review the AI-drafted sets**: advice-guard set (0/120 reviewed), question sets, weak-label audit, gold v1 corrections log. The report discloses all of them (`report/README.md`).
- **Hindi use-of-money for LG still says "not found"** (weak 2B Hindi; LG is a pure offer for sale with no objects table). Decide whether to show the retrieved passages instead for Hindi (ADR-020 fallback).
- **Full-profile latency is 32 s median on this laptop** (17 s in retrieval with the LLM resident, against 0.7 s measured alone). Not investigated; worth a look before the demo (try the reranker on CPU or a smaller `rerank_top_n`).
- **Model Lab text says "Answer accuracy on real model answers is not measured yet"**: E7 now exists (`e7.json`); decide whether the lab shows it (needs a lab route and copy).
- **Frontier comparison (E9, P5.2)** is still yours; `/api/lab/frontier` returns 404 until `eval_results/frontier.json` exists (the lab hides the section).
- **Deploy** (P6): follow `docs/DEPLOY_STEPS.md`. I did not create accounts or upload anything, and I did **not** build the Docker image (Docker Desktop was off and free RAM was about 3 GB). Build it once locally before the Space.
- **Vercel rewrite and slow live answers**: a long CPU answer may be cut by the proxy limit; the fix is a CORS rule and a direct call (see DEPLOY_STEPS).
- **Report**: every file in `report/` is a draft to rewrite in your voice; sections 1, 2, 9, 10 are not drafted. Check each `[verify]` citation. README "What I learned" is yours.
