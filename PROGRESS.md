# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` + `docs/phase3/C_EXECUTION_PLAN.md`.
- **MODE: overnight autonomous run** (user asleep): everything on Sonnet, one PR per part, merged by Claude when green. Order: C0.2 ✓ → C1.1 ✓ → C1.2 (code ✓, fetch RUNNING) → C1.3 (code ✓, batch parse RUNNING) → C1.4 real run → C2.1 … C2.8 (code + notebooks only). Stop rules: money/keys/GCP/deploy, same bug twice (write `BLOCKED.md`, move on), all blocked.
- **Background jobs (started by Claude, repo root):** `scripts/fetch_offer_docs.py` (log `data/raw/logs/fetch1.log`) and `data/raw/logs/loop.sh` (repeats `scripts/batch_parse.py`; log `data/raw/logs/batch.log`; appends `LOOP_DONE` at the end). `configs/ipo_universe.csv` is rewritten by the fetch: do NOT commit it until both finish; then `batch_parse.py --apply`, `--report`, fix repeated failures (regression tests), `uv run poe docs-gen`, commit "data: fetch + parse status" (closes #175/#176).
- **Last done:** C2.1, C2.2, C2.3, C2.5 merged (code + notebooks + steps); C2.4 classifier runner (`scripts/classifier_kaggle.py`, `finsight.risks.clf_runs`, model card) on branch `model/c2.4-classifier`. C2.6, C2.7, C2.8 still to do (code against fixtures).
- **Next:** C2.6 novelty pair sheet/scoring, C2.8 thresholds against fixtures, C2.7 only if worthwhile; then the C1.2/C1.3 data commit and the C1.4 real run when both background jobs finish.
- **Pending (Akshat):** vLLM pin test on the L4 (AKSHAT_TODO, C0.2).
- **Opus-marked parts done on Sonnet (review in the morning):** C2.2 (pick rule in `src/finsight/risks/bakeoff.py`, C-ADR-05).
- **Open questions:** none.

## Log
- C2.4 code: classifier Kaggle runner, split manifests, E16 summary, model card; real runs in AKSHAT_TODO
- C2.5 code: student Colab notebook (bf16/nf4 LoRA, GGUF, resume) + steps; real run in AKSHAT_TODO
- C1.3 code: resumable batch runner + cover date/exchange/SME detection; real parse running.
- C1.2: polite fetcher (finsight.ingest.fetch), fake-server tests; real fetch running.
- C1.1: IPO universe from SEBI public filings (289 rows), parser + builder + datasheet draft; 2026 count above expectation (see Resume here).
- C0.2 code: Colab helpers (_common, Checkpointer, run_summary), rate-check/vLLM-smoke notebook, compute log, HF upload helper; rates measured by hand, vLLM pin pending on L4.
- C1.4 code (out of order, fixtures only): `finsight.splits` + leakage guard + reference window + universe contract; no other package wired (C2.1/C2.7/C2.8/C3.4 do that).
- C0.1: Phase 3 kickoff review (F1–F40) → fixes in the C-docs; critical path + cut line approved; Phase 2 log moved to `docs/PROGRESS_PHASE2.md`.
- Blockers: none.
