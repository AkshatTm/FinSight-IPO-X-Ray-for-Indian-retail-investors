# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` + `docs/phase3/C_EXECUTION_PLAN.md`.
- **MODE: overnight autonomous run** (user asleep): everything on Sonnet, one PR per part, merged by Claude when green. Order: C0.2 ✓ → C1.1 ✓ → C1.2 (code merged; fetch RUNNING) → C1.3 (code; batch parse RUNNING in a loop) → C1.4 real run → C2.1 … C2.8 (code + notebooks only). Stop rules: money/keys/GCP/deploy, same bug twice (write `BLOCKED.md`, move on), all blocked.
- **Background jobs (started by Claude, from the repo root):** `scripts/fetch_offer_docs.py` (log `data/raw/logs/fetch1.log`) and `data/raw/logs/loop.sh` (runs `scripts/batch_parse.py` repeatedly; log `data/raw/logs/batch.log`; writes `LOOP_DONE` at the end). `configs/ipo_universe.csv` is being rewritten by the fetch: do NOT commit it until both finish; then `scripts/batch_parse.py --apply`, `--report`, `uv run poe docs-gen`, commit as "data: fetch + parse status".
- **Last done:** C1.1 merged (289 rows; 2026 count 97 vs ≈ 80 expected: mismatch, reasons in the C1.1 log line). C1.2 code in review/merged.
- **Next:** finish C1.3 code PR (batch runner), wait for jobs, data PR, then C1.4 real run.
- **Pending (Akshat):** vLLM pin test on the L4 (AKSHAT_TODO, C0.2).
- **Opus-marked parts done on Sonnet (review in the morning):** none yet.
- **Open questions:** none.

## Log
- C1.2: polite fetcher (finsight.ingest.fetch), fake-server tests; real fetch running.
- C1.1: IPO universe from SEBI public filings (289 rows), parser + builder + datasheet draft; 2026 count above expectation (see Resume here).
- C0.2 code: Colab helpers (_common, Checkpointer, run_summary), rate-check/vLLM-smoke notebook, compute log, HF upload helper; rates measured by hand, vLLM pin pending on L4.
- C1.4 code (out of order, fixtures only): `finsight.splits` + leakage guard + reference window + universe contract; no other package wired (C2.1/C2.7/C2.8/C3.4 do that).
- C0.1: Phase 3 kickoff review (F1–F40) → fixes in the C-docs; critical path + cut line approved; Phase 2 log moved to `docs/PROGRESS_PHASE2.md`.
- Blockers: none.
