# COLAB_STEPS_student_8b — the 8B student variant (C2.5)

**Status:** prepared, **not started** (waits for Akshat's "go"). **Job:** LoRA on `Qwen/Qwen3-8B` (Apache-2.0, hybrid thinking, so the notebook renders the chat template with `enable_thinking=False`) on the same `train.jsonl` / `dev.jsonl` as the 4B, then GGUF Q4_K_M. **GPU:** G4 (bf16, batch 16×1). **Expected:** about 2× the 4B's 1 h 10 m, so roughly 2–2.5 h, ≈ 20–22 units at ~8.9 units/h (the 4B session used 11.5 units in total); record the real figure. **Notebook:** `notebooks/colab/c2_student.ipynb`, presets `student_8b_smoke` and `student_8b` (own job folder `student_8b`, own private repo `AkshatTm/finsight-student-8b`; the 4B outputs are untouched).

**Same split as the 4B:** the 8B sees exactly the 4B's training pairs; nothing from the test or bench slices (C-ADR-02).

## Before (Claude, laptop)
1. `uv run python scripts/gpu_jobs.py push student_8b` (uploads the notebooks, `_common.py`, `train.jsonl`, `dev.jsonl` under `student_8b/in/`).

## Run (you attach a G4; Claude drives through colab-mcp)
1. Runtime → Change runtime type → **G4** → Connect. Tell Claude the units in the Resources panel.
2. **Smoke:** `PRESET = "student_8b_smoke"`, `UNASSIGN = False`. Check the log prints `PRESET student_8b_smoke | GPU G4 ...` and 10 steps finish (the 8B in bf16 is ~16 GB of weights; it fits).
3. **Real run:** `PRESET = "student_8b"`, `UNASSIGN = True`, `UNITS_BEFORE = <n>`, `RESUME = False` for the first run (the smoke run shares the job folder). A disconnect is safe: reconnect, `RESUME = True`, run all.
4. The runtime releases itself at the end. Give `UNITS_AFTER` to the pull.

## Bring back
- `uv run python scripts/gpu_jobs.py pull student_8b --units-before <n> --units-after <n>`: `models/student_8b/{adapter/, simplifier-q4_k_m.gguf, metrics.json}`; run summary → `eval_results/c/student_8b_run_summary.json`.
- Claude serves it through Ollama with the Qwen3 template and `/no_think` behaviour checked on three prompts, then runs `gold_sets.py generate --system student8b`, `student_vs_base.py` and `student_eval.py --model <tag>` for the same post-checks, E19, E20 and CPU seconds, and adds a row to the model card.
- Fix first (flagged): the Ollama template for the 8B must emit the empty think block the same way training did; if the outputs start with `<think>`, change the Modelfile, not the weights.

## Honesty notes
Single seed (2026); AI-made labels; same gold-50 and one rater. The 8B is reported next to the 4B, not instead of it; the 4B stays the laptop default unless the 8B wins on gold-50 and its CPU seconds per risk are acceptable.
