# COLAB_STEPS_teacher_full — the teacher over the training risks (C2.3)

**Job:** the chosen teacher labels and rewrites up to 12,000 `train` risks. **GPU:** the fastest your plan lists (H100 / A100-80GB / A100-40GB; an L4 only if the bake-off chose a 14B model). **Expected:** 2–4 h ≈ 14–27 units on an A100 (6.77 units/h); vLLM is probably faster; re-estimated from the bake-off throughput. **Notebook:** `notebooks/colab/c2_teacher.ipynb` (same notebook as the bake-off).

## Before (laptop, Claude)
1. The split is frozen, the bank is built and `uv run python scripts/export_teacher_input.py` has written `data/processed/teacher/risks.jsonl` (cap 35 per company gives 12,305 achievable, 12,000 written).
2. The bake-off is decided (`eval_results/c/teacher_bakeoff.json`, C-ADR-05 accepted); the chosen model is in the `teacher_smoke` / `teacher_full` presets. The vLLM pin comes from the L4 test.
3. `uv run python scripts/gpu_jobs.py push teacher_full`.

## Run (you, or Claude through colab-mcp)
1. Open `c2_teacher.ipynb`. **Smoke:** `PRESET = "teacher_smoke"` on a cheap GPU (20 risks, must print `TEACHER OK`).
2. **Full run:** the fastest GPU, `PRESET = "teacher_full"`, type `UNITS_BEFORE`, Run all, then leave it. It prints `PROGRESS ... ETA` after every 200 risks, ends with `TEACHER DONE` and disconnects the runtime (also after a crash).
3. A disconnect is safe: reconnect, same preset, run all; it resumes from the job repo (at most 200 risks are redone).

## Bring back (laptop, Claude)
- `uv run python scripts/gpu_jobs.py status teacher_full`, then `... pull teacher_full --units-before <n> --units-after <n>`: the raw file lands in `data/processed/teacher/raw/` and, for one model, as `data/processed/teacher/raw.jsonl`; run summaries go to `eval_results/c/`; the compute row is logged.
- Claude runs `uv run python -m finsight.risks.teacher_data filter` (drop report, `labels.jsonl`, `simplify.jsonl`) and `... sheet` (the quality-100 CSV).

## Rate the quality-100 sheet (you, ~30 min)
- `data/processed/teacher/quality_sheet.csv`: `faithful` = yes / partly / no, `category_correct` = yes / no. 100 rows.
- Tell Claude "quality-100 rated". Claude runs `uv run python -m finsight.risks.teacher_data score` → `eval_results/teacher_quality.json` and the datasheet fills itself.
- **Go** if "same meaning: yes" is at least 85 %. If not: Claude fixes the prompt, re-runs 500 risks and the sheet is rated again (CG2 waits for a go).
