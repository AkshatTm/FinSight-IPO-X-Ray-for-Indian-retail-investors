# Retrain the simplifier (Kaggle)

The simplifier rewrites each risk factor in plain English. It is a small student model (Qwen3-4B-Instruct-2507, QLoRA) trained on the teacher's filtered rewrites, then exported as GGUF Q4_K_M for llama.cpp on the CPU worker. The merged fp16 weights (`merged/`) can serve the optional GPU job with vLLM; the AWQ export B03 §5 mentions is not in the notebook yet and is only needed if the L4 runs short of memory.

**Prerequisites:** as for [the classifier](retrain_classifier.md), plus the filtered rewrite pairs in `data/processed/teacher/simplify.jsonl`.

1. **Split:** `uv run python -m finsight.risks.simplify split` writes `data/processed/kaggle/simplify/`. Upload it as the private Kaggle dataset `finsight-simplify`.
2. **Notebook:** `uv run python scripts/make_student_notebook.py` regenerates `notebooks/b2_student_qlora_kaggle.ipynb`. Push it with `SMOKE = True` first, then the full run. Training uses NF4 + LoRA r16 in fp16 on a T4, with loss on the answer only, and resumes from its last checkpoint.
3. **Download** `simplifier-q4_k_m.gguf`, `merged/` and `metrics.json` into `models/simplifier/`. Weights are never committed; a private Hugging Face repository is the backup.
4. **Check on the laptop** with `finsight.risks.Simplifier`. Every rewrite runs the same post-checks as the teacher's filters (numbers kept, no forbidden phrase, length, certainty kept). A rewrite that fails a check is rejected, never shown.
5. **Evaluate (E18–E20):** readability and post-check pass rates by script, and the blind gold-50 rating sheet for Akshat. Results go to `eval_results/b/`.
6. **Model card:** `docs/model_cards/simplifier.md`.

The step-by-step session prompt is the B2.5b item in `docs/AKSHAT_TODO.md`.
