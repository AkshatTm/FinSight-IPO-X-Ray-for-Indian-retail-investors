# COLAB_STEPS_teacher_bakeoff — teacher candidates on 300 risks (C2.2)

**Job:** the three C-ADR-05 candidates (Qwen3.8-27B-FP8, Gemma-4-31B-it bf16, Qwen3-32B-AWQ) answer the same 300 train+dev risks; you then rate a blind 150-row sheet. **GPU:** **G4** (RTX PRO 6000 Blackwell, 96 GB, ~8.9 units/h); all three fit. On an A100-40GB or smaller the notebook skips models that do not fit (bf16 Gemma needs ~66 GiB). **Expected:** one G4 session of ~45 min ≈ 6–7 units: smoke (20 risks per model, downloads the three models) then the real run (reuses the downloaded weights). **Notebook:** `notebooks/colab/c2_teacher.ipynb`.

## Before (laptop, Claude)
1. `uv run python scripts/teacher_bakeoff.py sample` → `data/processed/teacher/bakeoff/bakeoff_risks.jsonl` (300 train+dev risks, manifest `data/manifests/teacher_bakeoff_input.json`).
2. `VLLM_PIN = "vllm==0.31.0"` (C0.2) is the notebook default.
3. `uv run python scripts/gpu_jobs.py push bakeoff`.

## Run (Claude through colab-mcp; you choose the GPU and Connect)
1. Colab secret `HF_TOKEN` with notebook access on. Runtime → Change runtime type → **G4** → Connect. Tell Claude the units in the Resources panel.
2. **Smoke:** `PRESET = "bakeoff_smoke"`, `UNASSIGN = False` (the same runtime runs the real job next). Each model prints `TEACHER OK` with 20 written.
3. **Real run:** `PRESET = "bakeoff"`, `UNASSIGN = True`. On the G4 the notebook sends 512 risks per checkpointed batch (all 300 at once) with `max_num_seqs` 256, prints `PROGRESS ... ETA`, ends with `TEACHER DONE` and disconnects.
4. A disconnect is safe: reconnect, same preset, run all; every risk already in the job repo is skipped (the 20 smoke rows count towards the 300).

## Bring back (laptop, Claude)
- `uv run python scripts/gpu_jobs.py status bakeoff --wait` (background) then `... pull bakeoff --units-before <n> --units-after <n>`: raw files and per-model summaries go to `data/processed/teacher/bakeoff/`, the run summary to `eval_results/c/bakeoff_run_summary.json`, and the compute row is logged.
- Claude runs `scripts/teacher_bakeoff.py sheet` (blind 150-row CSV: 50 risks × 3 models).

## Rate the sheet (you, ~45 min)
- Open `data/processed/teacher/bakeoff/bakeoff_sheet.csv`. For each row: `faithful` = `yes` (same meaning, nothing added or lost), `partly`, or `no`; `category_correct` = `yes` / `no`. **Do not open `bakeoff_key.json`** (it names the model of each row).
- Tell Claude "sheet rated". Claude runs `scripts/teacher_bakeoff.py score` → `eval_results/c/teacher_bakeoff.json`; the pick follows C-ADR-05 (best `faithful = yes` share, models within 0.05 tied → lowest `number_mismatch` + `certainty_changed` drop rate → faster).

## If it goes wrong
- vLLM import/engine error: Claude reads the cell output; same error twice → stop and report.
- Out of memory: `MAX_MODEL_LEN = 3072`; models that do not fit are skipped with a message.
