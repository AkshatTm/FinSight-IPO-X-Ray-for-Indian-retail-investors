# Colab steps — teacher run (optional; only if Colab Pro is bought)

The plan is Kaggle-first (B-ADR-12, B03 §2). Use this only if Akshat buys Colab Pro and wants a larger teacher (~32B AWQ). Akshat starts Colab runs by hand; no session launches them.

1. Upload `risks.jsonl` (and `raw.jsonl` to resume) to a private Google Drive folder, e.g. `MyDrive/finsight/teacher/`. Never commit it.
2. Open `notebooks/b2_teacher_kaggle.ipynb` in Colab and select an **A100** (L4 fallback) runtime.
3. Add a cell at the top: `from google.colab import drive; drive.mount('/content/drive')`.
4. In the parameters cell, set:
   - `MODEL = "Qwen/Qwen3-32B-AWQ"` (check the licence on the Hub first);
   - `OUT_DIR = "/content/drive/MyDrive/finsight/teacher"`;
   - `LIMIT` for the run (50, 500 or `None`).
5. In the body cell, point `risks_file` at `/content/drive/MyDrive/finsight/teacher/risks.jsonl`. `raw.jsonl` already sits in `OUT_DIR`, so a rerun resumes from it.
6. Run all. When `TEACHER OK` prints, copy `raw.jsonl` and `run_summary.json` to `data/processed/teacher/` on the laptop. A local session then runs the filters (`python -m finsight.risks.teacher_data filter`).
7. Record the GPU hours and the model in `PROGRESS.md`. The datasheet's model line changes with the run.
