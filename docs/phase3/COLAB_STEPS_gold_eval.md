# COLAB_STEPS_gold_eval — teacher answers on the test-slice gold sets (C2.4, C2.5)

**Job:** the teacher (`google/gemma-4-31B-it`) and the bake-off runner-up (`Qwen/Qwen3.8-27B-FP8`) answer the 200 gold risks: gold-150 (15 risks × 10 test IPOs) and gold-50 (5 risks × 10 other test IPOs), sampled by `uv run python scripts/gold_sets.py sample` (manifest `data/manifests/gold_eval_risks.json`, kind `eval`). **Evaluation only:** nothing here trains or tunes a model (C-ADR-02). **GPU:** G4, run right after `teacher_full` in the same session (both models are cached on the VM disk only if the runtime stayed up). **Expected:** ~10 min ≈ 1.5 units (two model loads + 200 risks each).

Uses:
- **gold-150:** the verification sheet's `category` is pre-filled from **Qwen3.8**'s answers, not the teacher's, so the classifier's gold is not checked against its own teacher's labels (`scripts/gold_sets.py sheet150 --prefill gemma-4-31b-it` switches the source). The number of changed labels is reported.
- **gold-50:** the teacher's `simple` rewrite is one of the three blind systems (base, student, teacher).

## Run (Claude through colab-mcp)
1. Laptop: `uv run python scripts/gpu_jobs.py push gold_eval`.
2. Colab runner (`notebooks/colab/teacher_runner.py`, two cells): `PRESET = "gold_eval"`, `UNASSIGN = True` (the last job of the session), run both cells. Ends with `TEACHER DONE` and releases the GPU.

## Bring back
- `uv run python scripts/gpu_jobs.py pull gold_eval --units-before <n> --units-after <n>`: `raw_*.jsonl` → `data/processed/gold_eval/`.
- `uv run python scripts/gold_sets.py sheet150` → `data/gold/gold150_sheet.csv`.
