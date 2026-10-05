# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` + `docs/phase3/C_EXECUTION_PLAN.md`; critical path and cut line in C05 §6 (C-ADR-12, approved).
- **Last done:** C1.4 **code only**, done early on fixtures. `finsight.splits` covers:
  - the strict split (train cut = earliest test document; showcase roles from `demo_ipos.yaml`; same-company exclusion);
  - `configs/splits.yaml` with a freeze guard (a frozen split changes only with `--adr C-ADR-NN`);
  - manifests in `data/manifests/` (kinds `train`, `fit`, `eval_reference`, `product_reference`, `eval`) and retro manifests for the Phase 1 weak labels, extractor, BiLSTM-CRF and guard;
  - the leakage check (by `ipo_id` and company key), the 4-year reference window (`configs/reference.yaml`, corpus by close year, eval vs product, window n);
  - the `configs/ipo_universe.csv` contract (`UNIVERSE_COLUMNS`, no `split` column);
  - CLI `python -m finsight.splits build [--freeze]` / `check`;
  - `tests/test_split_leakage.py`: 3 checks skip until the split is frozen.

  Before that C0.1 (#198): Phase 3 docs + review fixes, rules, C-ADRs, issues #172–#197.
- **Next (critical path, Sonnet):** C0.2 Colab helpers + rate-check/vLLM smoke notebook → C1.1 universe (must pass `finsight.splits.load_universe`) → C1.2 fetch → C1.3 batch parse → **C1.4 real-data run** = `uv run python -m finsight.splits build` (dry run), Akshat confirms counts, then `build --freeze`, commit `data: freeze splits` ═ CG1. After CG1: bench lane C4.1 at once (biggest time risk).
- **Hand-work (Akshat):** C06 §1 setup (Drive folder, HF token in `.env` + Colab secret, Kaggle CLI check, frontier apps memory/search off, GCP trial credit check, 15 GB free disk); then the C0.2 rate-check run. See `docs/AKSHAT_TODO.md` → Phase 3.
- **Open questions:** none.
- **Tests:** 1625 passed, 3 skipped (split not frozen yet), 16 deselected (`uv run poe test`, after C1.4 code).

## Log
- C1.4 code (out of order, fixtures only): `finsight.splits` + leakage guard + reference window + universe contract; no other package wired (C2.1/C2.7/C2.8/C3.4 do that).
- C0.1: Phase 3 kickoff review (F1–F40) → fixes in the C-docs; critical path + cut line approved; Phase 2 log moved to `docs/PROGRESS_PHASE2.md`.
- Blockers: none.
