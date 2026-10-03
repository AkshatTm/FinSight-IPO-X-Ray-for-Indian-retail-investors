# Colab steps — student QLoRA (optional; only if Colab Pro is bought)

The plan is Kaggle-first (B-ADR-12). Use this only if Akshat buys Colab Pro and wants a faster run or more seeds. Akshat starts Colab runs by hand; no session launches them.

1. Put `train.jsonl` and `dev.jsonl` (from `uv run python -m finsight.risks.simplify split`) in a private Drive folder, for example `MyDrive/finsight/simplify/`. Never commit them.
2. Open `notebooks/b2_student_qlora_kaggle.ipynb` in Colab. Pick an **L4** or **A100** runtime.
3. Add a cell at the top: `from google.colab import drive; drive.mount('/content/drive')`.
4. In the body cell:
   - set `DATA_DIR = Path("/content/drive/MyDrive/finsight/simplify")`;
   - in the parameters cell, set `OUT_DIR = "/content/drive/MyDrive/finsight/student"`. Checkpoints then survive a disconnect, and a rerun resumes from them.
5. On L4/A100 you may switch fp16 to bf16 (`bnb_4bit_compute_dtype=torch.bfloat16`, `bf16=True`). Note the change in the model card.
6. Run all. When `STUDENT OK` prints, copy `simplifier-q4_k_m.gguf` and `metrics.json` to `models/simplifier/` on the laptop. Keep `merged/` in the private Hugging Face repo, not in git.
