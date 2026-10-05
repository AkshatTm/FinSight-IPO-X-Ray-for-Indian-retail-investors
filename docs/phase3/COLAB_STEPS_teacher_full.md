# COLAB_STEPS_teacher_full — the teacher over the training risks (C2.3)

**Job:** the chosen teacher labels and rewrites up to 12,000 `train` risks. **GPU:** A100 (or L4 if the bake-off chose the 14B). **Expected:** 2–4 h ≈ 14–27 units on an A100 (6.77 units/h); vLLM is probably faster than that. **Notebook:** `notebooks/colab/c2_teacher.ipynb` (same notebook as the bake-off).

## Before (laptop, Claude)
1. The split is frozen, the bank is built and `uv run python scripts/export_teacher_input.py` has written `data/processed/teacher/risks.jsonl` (it prints how many risks are achievable; the cap of 25 per company may keep it under 12,000).
2. The bake-off is decided (`eval_results/c/teacher_bakeoff.json`, C-ADR-05 accepted) or the 14B is used directly. Use the vLLM pin from the L4 test.

## Run (you)
1. Drive: create `MyDrive/FinSight/teacher_full/` and copy `risks.jsonl` into it. `_common.py` must be in `MyDrive/FinSight/`.
2. Upload `notebooks/colab/c2_teacher.ipynb`. Parameters: `JOB = "teacher_full"`, `INPUT_FILE = "risks.jsonl"`, `MODELS = [<the chosen model>]` (one model only), `EVERY = 200`, `VLLM_PIN` as recorded, `QUANT = "awq_marlin"`. First a smoke run (`SMOKE = True`, 20 risks, T4 or L4, `QUANT = "awq"` on a T4), then `SMOKE = False` on the A100.
3. Type `UNITS_BEFORE`. Run all. A disconnect is safe: reconnect, run all, it resumes from `MyDrive/FinSight/teacher_full/out/` (at most 200 risks are redone).
4. When it ends type `UNITS_AFTER`, re-run the last cell, disconnect the runtime.

## Bring back
- `MyDrive/FinSight/teacher_full/out/raw_<model>.jsonl` → `data/processed/teacher/raw.jsonl`; `run_summary_<model>.json` and `run_summary.json` → `eval_results/c/` (then `scripts/log_compute.py` on the run summary).
- Tell Claude "teacher run is back". Claude runs `uv run python -m finsight.risks.teacher_data filter` (drop report, `labels.jsonl`, `simplify.jsonl`) and `... sheet` (the quality-100 CSV).

## Rate the quality-100 sheet (you, ~30 min)
- `data/processed/teacher/quality_sheet.csv`: `faithful` = yes / partly / no, `category_correct` = yes / no. 100 rows.
- Tell Claude "quality-100 rated". Claude runs `uv run python -m finsight.risks.teacher_data score` → `eval_results/teacher_quality.json` and the datasheet fills itself.
- **Go** if "same meaning: yes" is at least 85 %. If not: Claude fixes the prompt, re-runs 500 risks and the sheet is rated again (CG2 waits for a go).
