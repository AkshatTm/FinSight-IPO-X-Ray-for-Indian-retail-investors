# COLAB_STEPS_student — the plain-English student (C2.5)

**Job:** LoRA fine-tune of `Qwen/Qwen3-4B-Instruct-2507` on the filtered teacher rewrites, then a GGUF Q4_K_M. **GPU:** L4 (bf16) or A100; a T4 only for the smoke run (`PRECISION = "nf4"`). **Expected:** 1–2 h ≈ 2–3 units on an L4 (1.54 units/h); record the real figure. **Notebook:** `notebooks/colab/c2_student.ipynb`.

## Before (laptop, Claude)
1. CG2 passed: the quality-100 sheet scored at least 85 % and `python -m finsight.risks.teacher_data filter` wrote `simplify.jsonl`.
2. `uv run python -m finsight.risks.simplify split` wrote `train.jsonl` and `dev.jsonl` (split by company; no test or bench company).
3. The zero-shot bake-off picked the base model (gold-50 sheet); if it changed `MODEL`, set it in the notebook.

## Run (you)
1. Drive: create `MyDrive/FinSight/student/`, copy `train.jsonl` and `dev.jsonl` into it. `_common.py` must be in `MyDrive/FinSight/`.
2. Upload `notebooks/colab/c2_student.ipynb`. **Smoke first:** T4, `PRECISION = "nf4"`, `SMOKE = True`, `EXPORT_GGUF = False` (10 steps, minutes).
3. **Real run:** L4 or A100, `PRECISION = "bf16"`, `SMOKE = False`, `EXPORT_GGUF = True`. On an A100 `BATCH_SIZE = 8`, `GRAD_ACCUM = 2`. Type `UNITS_BEFORE`, run all.
4. A disconnect is safe: reconnect, run all, it resumes from the newest checkpoint in `MyDrive/FinSight/student/ck/trainer/` (at most `SAVE_STEPS` = 200 steps redone).
5. When it ends type `UNITS_AFTER`, re-run the last cell, disconnect the runtime.
6. Optional: `UPLOAD = True` pushes the adapter and GGUF to the **private** repo `HF_REPO` (token in Colab secrets as `HF_TOKEN`). Merged fp16 weights are never kept or uploaded.

## Bring back
- `MyDrive/FinSight/student/out/` → `adapter/`, `simplifier-q4_k_m.gguf`, `metrics.json` to `models/student/` (gitignored); `run_summary.json` to `eval_results/c/` and run `scripts/log_compute.py` on it.
- Tell Claude "student is back". Claude runs E18–E20 (meaning kept, numbers copied, forbidden phrases) on the gold-50 and the held-out dev rows, measures CPU seconds per risk, and writes `docs/model_cards/risk_simplifier.md`.

## Honesty notes
Single seed (2026). The training rewrites are AI-made (`label_source`), the gold-50 is rated by one person, and the corpus terms are non-commercial: keep the repo private.
