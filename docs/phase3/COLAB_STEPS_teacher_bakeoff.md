# COLAB_STEPS_teacher_bakeoff — teacher candidates on 300 risks (C2.2)

**Job:** every candidate answers the same 300 risks; you then rate a blind sheet. **GPU:** the fastest your plan lists (check H100, then A100-80GB, then A100-40GB); on an L4 the notebook skips models that do not fit. **Expected:** about 1–1.5 h ≈ 7–10 units on an A100 (6.77 units/h), plus a smoke run on a cheap GPU (~0.1–0.3 units). Update after C2.2 step "candidates" fixes the model list. **Notebook:** `notebooks/colab/c2_teacher.ipynb`.

## Before (laptop, Claude)
1. `uv run python scripts/teacher_bakeoff.py sample` → `data/processed/teacher/bakeoff/bakeoff_risks.jsonl` (300 train+dev risks).
2. The **vLLM pin** from the L4 test is written into the notebook's `VLLM_PIN` (`COLAB_STEPS_rate_check.md`).
3. `uv run python scripts/gpu_jobs.py push bakeoff`.

## Run (you, or Claude through colab-mcp)
1. Colab secret `HF_TOKEN` with notebook access on (once). Open `c2_teacher.ipynb`.
2. **Smoke:** cheap GPU (L4 or T4), `PRESET = "bakeoff_smoke"`, type `UNITS_BEFORE`, Run all. Each model that fits prints `TEACHER OK` with 20 written.
3. **Real run:** the fastest GPU, `PRESET = "bakeoff"`, Run all. The notebook picks `awq_marlin` and `GPU_MEM` from the GPU, prints `PROGRESS ... ETA` after every batch, ends with `TEACHER DONE` and disconnects.
4. A disconnect is safe: reconnect, same preset, run all; it resumes from the job repo.

## Bring back (laptop, Claude)
- `uv run python scripts/gpu_jobs.py status bakeoff`, then `... pull bakeoff --units-before <n> --units-after <n>`: raw files and per-model summaries go to `data/processed/teacher/bakeoff/`, the run summary to `eval_results/c/bakeoff_run_summary.json`, and the compute row is logged.
- Tell Claude "bake-off is back". Claude runs `scripts/teacher_bakeoff.py sheet` (blind 100-row CSV).

## Rate the sheet (you, ~30 min)
- Open `data/processed/teacher/bakeoff/bakeoff_sheet.csv`. For each row: `faithful` = `yes` (same meaning, nothing added or lost), `partly`, or `no`; `category_correct` = `yes` / `no`. **Do not open `bakeoff_key.json`** (it names the model of each row).
- Tell Claude "sheet rated". Claude runs `scripts/teacher_bakeoff.py score` → `eval_results/c/teacher_bakeoff.json`, and the pick follows the rule written in C-ADR-05 before any rating existed.

## If it goes wrong
- vLLM import/engine error: paste the last 30 lines to Claude; try the next pin in the L4 test list.
- Out of memory: `MAX_MODEL_LEN = 3072` or `QUANT_OVERRIDE`; models that do not fit are skipped with a message.
