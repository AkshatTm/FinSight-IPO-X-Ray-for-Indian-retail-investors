# COLAB_STEPS_student — the plain-English student (C2.5)

**Job:** LoRA fine-tune of `Qwen/Qwen3-4B-Instruct-2507` on the filtered teacher rewrites, then a GGUF Q4_K_M. **GPU:** **G4** recommended (RTX PRO 6000 Blackwell, bf16, batch 16×1): ~0.5–0.8 h ≈ 5–7 units at ~8.9 units/h. An L4 also works (bf16, 2×8) but takes ~4–5 h for about the same units (~7). A T4 only for a smoke run (`PRECISION = "nf4"`). Record the real figure. **Notebook:** `notebooks/colab/c2_student.ipynb`. **Do not launch before CG2** (quality-100 at least 85 % "same meaning: yes").

## Before (laptop, Claude)
1. CG2 passed (quality-100: faithful 98 %) and `python -m finsight.risks.teacher_cleanup run` wrote `simplify.clean.jsonl` (strict number filter applied).
2. `uv run python -m finsight.risks.simplify split` wrote `train.jsonl` (10,362) and `dev.jsonl` (529) from the clean pairs (split by company; no test or bench company).
3. `uv run python scripts/gpu_jobs.py push student` (uploads `train.jsonl`, `dev.jsonl`, `_common.py` and the notebooks to the private HF job repo; Drive mode `IO = "drive"` is the fallback). Colab secret `HF_TOKEN` with notebook access on.

## Run (Claude through colab-mcp; you pick the GPU and Connect)
1. Runtime → Change runtime type → **G4** → Connect. Tell Claude the units in the Resources panel.
2. **Smoke:** `PRESET = "student_smoke"`, `UNASSIGN = False` (64 train / 16 dev rows, 10 steps, no GGUF; minutes).
3. **Real run:** `PRESET = "student"`, `UNASSIGN = True`, `UNITS_BEFORE = <n>`, `RESUME = True`. Batch and precision come from the GPU tier. Run all. `RESUME = False` ignores old checkpoints (use it after a smoke run on the same job repo).
4. A disconnect is safe: reconnect, run all, it resumes from the newest checkpoint in the job repo (`student/out/trainer/`; a checkpoint is saved every `SAVE_STEPS` = 200 steps and at the end of each epoch).
5. When it ends the runtime disconnects itself (`main()` releases it in `finally`, also after a crash); give `UNITS_AFTER` to `gpu_jobs.py pull`.
6. Optional: `UPLOAD = True` pushes the adapter and GGUF to the **private** repo `HF_REPO`. Merged fp16 weights are never kept or uploaded.

## Bring back
- `uv run python scripts/gpu_jobs.py pull student --units-before <n> --units-after <n>`: `adapter/`, `simplifier-q4_k_m.gguf`, `metrics.json` → `models/student/` (gitignored); the run summary → `eval_results/c/student_run_summary.json` and the compute row is logged.
- gold-50 (test slice, `scripts/gold_sets.py`): `generate --system student --backend llama-cpp --model models/student/simplifier-q4_k_m.gguf` and `generate --system base --backend ollama --model <base tag>`; the teacher system comes from the `gold_eval` Colab job. Then `sheet50` → blind `data/gold/simplify_gold50_sheet.csv` (150 rows: 50 risks × base / student / teacher). You rate `faithful` (yes / partly / no) and `plain_english_1to5`; `score50` → `eval_results/c/simplify_gold50.json`.
- Claude runs E18–E20 (meaning kept, numbers copied, forbidden phrases) on the gold-50 and the held-out dev rows, measures CPU seconds per risk, and writes `docs/model_cards/risk_simplifier.md`.

## Honesty notes
Single seed (2026). The training rewrites are AI-made (`label_source`), the gold-50 is rated by one person, and the corpus terms are non-commercial: keep the repo private.
