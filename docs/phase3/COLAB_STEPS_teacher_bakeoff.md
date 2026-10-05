# COLAB_STEPS_teacher_bakeoff — Qwen3-14B-AWQ vs Qwen3-32B-AWQ on 300 risks (C2.2)

**Job:** both teachers answer the same 300 risks; you then rate a blind sheet. **GPU:** **A100** (the 32B model needs ~40 GB; on an L4 the notebook skips it and only the 14B runs, and then Claude records "14B used directly" as an ADR). **Expected:** ~1–1.5 h ≈ 7–10 units (A100 ~6.77 units/h) plus a smoke run on a T4 (~0.1 units). **Notebook:** `notebooks/colab/c2_teacher.ipynb`.

## Before (on the laptop, Claude does this)
1. `uv run python scripts/teacher_bakeoff.py sample` → `data/processed/teacher/bakeoff/bakeoff_risks.jsonl` (300 train+dev risks).
2. You need the **vLLM pin** from the L4 test (`COLAB_STEPS_rate_check.md`). If you have not run that yet, run it first (~15 min).

## Run (you)
1. Google Drive: create `MyDrive/FinSight/teacher_bakeoff/` and copy `bakeoff_risks.jsonl` into it. Make sure `MyDrive/FinSight/_common.py` exists (copy `notebooks/colab/_common.py`).
2. Upload `notebooks/colab/c2_teacher.ipynb` to Colab. Runtime → **T4 GPU** for the smoke run.
3. Parameter cell: `VLLM_PIN` = the pin from the L4 test, `QUANT = "awq"` on a T4 (T4 cannot use `awq_marlin`), `MODELS = ["Qwen/Qwen3-14B-AWQ"]`, `SMOKE = True`. Type `UNITS_BEFORE`. Run all. It must print `TEACHER OK` with 20 written. (If the 14B does not fit the T4 with `MAX_MODEL_LEN = 2048`, skip the smoke on T4 and smoke on the L4 instead.)
4. **Real run:** Runtime → **A100 GPU**. Parameters: `QUANT = "awq_marlin"`, `MODELS` as in the file (both), `SMOKE = False`, `EVERY = 100`. Run all. The 14B runs first, then the 32B.
5. If the runtime disconnects: reconnect, run all again. It resumes from `MyDrive/FinSight/teacher_bakeoff/out/` (you lose at most one batch of 100).
6. At the end type `UNITS_AFTER`, re-run the last cell, then disconnect the runtime (`UNASSIGN = True`).

## Bring back
- Copy `MyDrive/FinSight/teacher_bakeoff/out/raw_qwen3-14b-awq.jsonl`, `raw_qwen3-32b-awq.jsonl`, `run_summary_*.json` into `data/processed/teacher/bakeoff/`, and `MyDrive/FinSight/teacher_bakeoff/run_summary.json` to `eval_results/c/bakeoff_run_summary.json`; then `uv run python scripts/log_compute.py eval_results/c/bakeoff_run_summary.json`.
- Tell Claude "bake-off is back". Claude runs `scripts/teacher_bakeoff.py sheet` (blind 100-row CSV).

## Rate the sheet (you, ~30 min)
- Open `data/processed/teacher/bakeoff/bakeoff_sheet.csv`. For each row: `faithful` = `yes` (same meaning, nothing added or lost), `partly`, or `no`; `category_correct` = `yes` / `no`. **Do not open `bakeoff_key.json`** (it names the model of each row).
- Tell Claude "sheet rated". Claude runs `scripts/teacher_bakeoff.py score` → `eval_results/c/teacher_bakeoff.json`, and the pick follows the rule written in C-ADR-05 before any rating existed.

## If it goes wrong
- vLLM import/engine error: paste the last 30 lines to Claude; try the next pin in the L4 test list.
- Out of memory on the A100: lower `GPU_MEM` to 0.85 or `MAX_MODEL_LEN` to 3072.
