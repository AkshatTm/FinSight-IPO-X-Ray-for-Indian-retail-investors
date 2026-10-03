# Retrain the risk classifier (Kaggle)

The risk category classifier sorts each risk factor into one of ten categories. It is fine-tuned on teacher labels on Kaggle and served as ONNX int8 on the CPU worker. Training never runs on the laptop or in a cloud session.

**Prerequisites:** a Kaggle account with phone verification (GPU access), the official `kaggle` CLI with its token in `~/.kaggle/kaggle.json` (never printed or committed), and the filtered teacher labels in `data/processed/teacher/`.

1. **Split the data by company** (no company in both train and dev):

   ```bash
   uv run python -m finsight.risks.classify split
   ```

   This writes `data/processed/kaggle/risk-classifier/`. Upload it as the private Kaggle dataset `finsight-risk-classifier`.
2. **Baseline on the laptop CPU:** `uv run python -m finsight.risks.classify baseline --gold <gold-150 JSONL>` writes `eval_results/b/classifier_tfidf.json`. A model has to beat it.
3. **Notebooks** are generated, never edited by hand: `uv run python scripts/make_classifier_notebooks.py`. Push `notebooks/b2_classifier_base_kaggle.ipynb` with `SMOKE = True` first (GPU and internet on, the dataset attached), then the full run (3 seeds); the large model has its own notebook (1 seed).
4. **Choose** base or large by **dev** macro-F1 only, and record the choice as a proposed ADR.
5. **Export:**

   ```bash
   uv run --group ml --group onnx python scripts/export_onnx_classifier.py --model <chosen>/final --dev data/processed/kaggle/risk-classifier/dev.jsonl
   ```

   The script checks that the ONNX model agrees with PyTorch on the dev set.
6. **Evaluate (E16)** on gold-150 with the scripts; results go to `eval_results/b/classifier_*.json` with the seed count and `label_source`. Never type a number by hand.
7. **Model card:** `docs/model_cards/risk_classifier.md` (template in B09 §4).

The step-by-step session prompt is the B2.4b item in `docs/AKSHAT_TODO.md`.
