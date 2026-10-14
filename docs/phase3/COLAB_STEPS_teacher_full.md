# COLAB_STEPS_teacher_full — the teacher over the training risks (C2.3)

**Job:** the chosen teacher, **`google/gemma-4-31B-it` (bf16)** (C-ADR-05), labels and rewrites the 12,000 `train` + `dev` risks. **GPU:** **G4** (RTX PRO 6000 Blackwell, 96 GB, ~8.9 units/h); bf16 Gemma needs ~66 GiB, so an A100-40GB or L4 cannot run it. **Expected:** ~1 h ≈ 8–9 units: ~5 min model download + load, then ~270 risks/min (bake-off rate) → ~45 min for 12,000. **Notebook:** `notebooks/colab/c2_teacher.ipynb` (same notebook as the bake-off; `TEACHER_PICK` defaults to Gemma).

## Before (laptop, Claude)
1. `data/processed/teacher/risks.jsonl` = 12,000 risks (cap 35 per company; manifest `data/manifests/teacher_input.json`).
2. The bake-off is decided (`eval_results/c/teacher_bakeoff.json`, C-ADR-05).
3. `uv run python scripts/gpu_jobs.py push teacher_full`.

## Run (Claude through colab-mcp; you pick the GPU and Connect)
1. Runtime → Change runtime type → **G4** → Connect. Tell Claude the units in the Resources panel.
2. **Smoke:** `PRESET = "teacher_smoke"`, `UNASSIGN = False` (20 risks, must print `TEACHER OK`).
3. **Full run:** `PRESET = "teacher_full"`, `UNASSIGN = True`. Batches of 512 risks, each uploaded to the HF job repo, `PROGRESS ... ETA` after each; ends with `TEACHER DONE` and disconnects (also after a crash).
4. Claude runs `uv run python scripts/gpu_jobs.py status teacher_full --wait` in the background (exit 0 = done, exit 2 = no new rows for 20 min).

## If it stopped (disconnect or crash)
Reconnect a **G4**, open the same Colab tab, set `PRESET = "teacher_full"`, `UNASSIGN = True`, run both cells. It skips every risk already in the job repo (at most one 512-risk batch is redone). Check first with `uv run python scripts/gpu_jobs.py status teacher_full` (rows done so far).

## Bring back (laptop, Claude)
- `uv run python scripts/gpu_jobs.py pull teacher_full --units-before <n> --units-after <n>`: `data/processed/teacher/raw/raw_gemma-4-31b-it.jsonl` and `data/processed/teacher/raw.jsonl`; run summaries to `eval_results/c/`; the compute row is logged.
- `uv run python -m finsight.risks.teacher_data filter` (drop report, `labels.jsonl`, `simplify.jsonl`) and `... sheet` (the quality-100 CSV).

## Rate the quality-100 sheet (you, ~30 min)
- `data/processed/teacher/quality_sheet.csv`: `faithful` = yes / partly / no, `category_correct` = yes / no. 100 rows.
- Tell Claude "quality-100 rated". Claude runs `uv run python -m finsight.risks.teacher_data score` → `eval_results/teacher_quality.json` and the datasheet fills itself.
- **Go** if "same meaning: yes" is at least 85 %. If not: Claude fixes the prompt, re-runs 500 risks and the sheet is rated again (CG2 waits for a go).
