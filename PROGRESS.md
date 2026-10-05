# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` + `docs/phase3/C_EXECUTION_PLAN.md`.
- **MODE: overnight autonomous run** (user asleep): everything on Sonnet, one PR per part, merged by Claude when green. Order: C0.2 ✓ → C1.1 ✓ → C1.2 → C1.3 → C1.4 real run → C2.1 … C2.8 (code + notebooks only). Stop rules: money/keys/GCP/deploy, same bug twice (write `BLOCKED.md`, move on), all blocked.
- **Last done:** C1.1: `configs/ipo_universe.csv` = 289 mainboard rows from SEBI (2024: 94, 2025: 98, 2026: 97). 2024/2025 are inside the pre-approved ranges; **2026 = 97 vs expected ≈ 80 (±10 % = 72–88): mismatch**. Reason: SEBI lists filings, not completed IPOs: ~37 RHPs were filed since 1 Sep (issues not yet open/listed), and some Prospectus-only rows look like SME issues. C1.3 must flag/exclude SME covers and unlisted issues. exchange = `both`, listing_date empty (SEBI doesn't give them).
- **Next:** C1.2 fetch (`scripts/fetch_offer_docs.py`, fake-server tests, then fetch; blocked/multi-part → manual list in AKSHAT_TODO) → C1.3 → C1.4 real run → C2.x.
- **Pending (Akshat):** vLLM pin test on the L4 (AKSHAT_TODO, C0.2).
- **Opus-marked parts done on Sonnet (review in the morning):** none yet.
- **Open questions:** none.
- **Tests:** green at last run (`uv run poe test`).

## Log
- C1.1: IPO universe from SEBI public filings (289 rows), parser + builder + datasheet draft; 2026 count above expectation (see Resume here).
- C0.2 code: Colab helpers (_common, Checkpointer, run_summary), rate-check/vLLM-smoke notebook, compute log, HF upload helper; rates measured by hand, vLLM pin pending on L4.
- C1.4 code (out of order, fixtures only): `finsight.splits` + leakage guard + reference window + universe contract; no other package wired (C2.1/C2.7/C2.8/C3.4 do that).
- C0.1: Phase 3 kickoff review (F1–F40) → fixes in the C-docs; critical path + cut line approved; Phase 2 log moved to `docs/PROGRESS_PHASE2.md`.
- Blockers: none.
