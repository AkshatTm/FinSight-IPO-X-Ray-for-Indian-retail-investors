# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` + `docs/phase3/C_EXECUTION_PLAN.md`.
- **MODE: overnight autonomous run** (user asleep): everything on Sonnet, one PR per part, merged by Claude when green. Order: C0.2 → C1.1 → C1.2 → C1.3 → C1.4 real run → C2.1 … C2.8 (code + notebooks only). Stop rules: money/keys/GCP/deploy, same bug twice (write `BLOCKED.md`, move on), all blocked.
- **Last done:** C0.2 code (`notebooks/colab/_common.py`, `c0_rate_check.ipynb` via `scripts/make_colab_notebooks.py`, `scripts/log_compute.py`, `scripts/hf_upload.py`, COLAB_STEPS template + rate_check). Measured rates logged (T4 1.07, L4 1.54, A100 6.77 units/h); C03 §4 re-planned. **Pending (Akshat):** vLLM pin test on the L4 (AKSHAT_TODO).
- **Next:** C1.1 universe → C1.2 fetch → C1.3 batch parse → C1.4 real-data run (`build --freeze` only if the pre-confirmed checks pass) → C2.x.
- **Opus-marked parts done on Sonnet (review in the morning):** C1.4 real run is Sonnet-fine; C2.2 (★ O) pending.
- **Open questions:** none.
- **Tests:** 1637 passed expected (`uv run poe test`).

## Log
- C0.2 code: Colab helpers (_common, Checkpointer, run_summary), rate-check/vLLM-smoke notebook, compute log, HF upload helper; rates measured by hand, vLLM pin pending on L4.
- C1.4 code (out of order, fixtures only): `finsight.splits` + leakage guard + reference window + universe contract; no other package wired (C2.1/C2.7/C2.8/C3.4 do that).
- C0.1: Phase 3 kickoff review (F1–F40) → fixes in the C-docs; critical path + cut line approved; Phase 2 log moved to `docs/PROGRESS_PHASE2.md`.
- Blockers: none.
