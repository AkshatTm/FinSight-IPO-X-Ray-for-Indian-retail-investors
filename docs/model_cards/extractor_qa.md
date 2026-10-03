# Fine-tuned QA extractor

- **Base model:** `deepset/deberta-v3-base-squad2` (CC BY 4.0), fine-tuned on FinSight weak labels
- **Owner:** Akshat · **Notebook:** `notebooks/01_finetune_extractor.ipynb` (Kaggle, 2 GPUs)
- **Version:** the run recorded in `eval_results/extractor_metrics-*.json` and `ladder_table.json` (gold v1)

## Intended use

Reads eight offer facts (fresh issue size, offer-for-sale shares and amount, total issue size, face value, book-running lead managers, registrar, promoters) from passages of an Indian IPO offer document, so the fact sheet can show the value with its page. Every value it returns is checked by the number verifier and shown with its source page.

**Out of scope:** investment advice, predictions of any kind, documents other than Indian IPO offer documents, and answering free-form questions (the chat uses retrieval and a local LLM).

## Training data

[Weak labels](../datasheets/weak_labels.md) built from the [corpus](../datasheets/corpus.md) of older IPO documents: cover-page values are found by rules and searched for in the body, which gives answerable and unanswerable passages. The 2025 showcase and gold IPOs are excluded from training (`configs/demo_ipos.yaml` and `data/gold/excluded_ipos.txt`).

## Training procedure

<!-- generated:training start -->

| Seed | epochs | learning_rate | batch_size | max_len | train_runtime_s | Dev EM | Dev F1 | HasAns F1 | NoAns acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | 3 | 2e-05 | 16 | 384 | 1005 | 0.967 | 0.974 | 0.959 | 0.983 |
| 2026 | 3 | 2e-05 | 16 | 384 | 1083 | 0.969 | 0.977 | 0.968 | 0.983 |
| 42 | 3 | 2e-05 | 16 | 384 | 1067 | 0.967 | 0.975 | 0.967 | 0.980 |

Base: `deepset/deberta-v3-base-squad2`. Training examples: 4047; dev examples: 491 (194 answerable). GPUs: 2 (Kaggle). Dev scores are on weak labels, not gold.

<!-- generated:training end -->

## Evaluation

The extractor ladder (E2, E3, E11) compares rules, the pretrained QA model, this fine-tuned model and the BiLSTM-CRF on the [gold set](../datasheets/gold_sets.md). "Body-only" blanks pages 1–15, so the cover page cannot be used: it measures robustness when the cover is missing or unusual. The bold rows are this model (mean over seeds).

<!-- generated:ladder start -->

Gold `v1`, seeds 13, 42, 2026, bootstrap over IPOs. NVM = normalised value match.

| Rung | Split | Full NVM [95 % CI] | Body-only NVM [95 % CI] | n (full / body) |
| --- | --- | --- | --- | --- |
| Rung 1: rules | dev | 1.00 [1.00, 1.00] | 0.29 [0.20, 0.40] | 24 / 14 |
| Rung 1: rules | test | 0.86 [0.79, 0.93] | 0.23 [0.20, 0.29] | 56 / 35 |
| Rung 2: pretrained QA | dev | 0.38 [0.38, 0.38] | 0.36 [0.00, 0.60] | 24 / 14 |
| Rung 2: pretrained QA | test | 0.36 [0.25, 0.46] | 0.37 [0.20, 0.54] | 56 / 35 |
| **Rung 3: fine-tuned QA** | dev | 0.61 [0.58, 0.62] | 0.71 [0.60, 0.80] | 24 / 14 |
| **Rung 3: fine-tuned QA** | test | 0.74 [0.66, 0.80] | 0.85 [0.80, 0.90] | 56 / 35 |
| Rung 4: BiLSTM-CRF | dev | 0.53 [0.46, 0.58] | 0.40 [0.25, 0.60] | 24 / 14 |
| Rung 4: BiLSTM-CRF | test | 0.49 [0.41, 0.56] | 0.28 [0.20, 0.36] | 56 / 35 |

<!-- generated:ladder end -->

In the app the extractor is chosen per field (`configs/fields.yaml`, ADR-018): rules come first for the product and this model is the fallback and cross-check (`fallback: qa_finetuned`).

## Limitations and known failure cases

- Lists of names: it often returns one manager instead of the full list, because training spans are single passages.
- Values the document leaves blank (`[●]` in an RHP): it may read a different number from the same page; the placeholder logic and the verifier are the guard.
- Seven test IPOs make every score wide; read the intervals.

Three wrong answers from the test IPOs:

<!-- generated:failures start -->

| IPO | Field | Read | Checked value |
| --- | --- | --- | --- |
| `hdb-financial-services-2025` p.3 | `book_running_lead_managers` | Goldman Sachs (India) Securities Private Limited | JM Financial Limited; BNP Paribas; BofA Securities India Limited; Goldman Sachs (India) Securities Private Limited; HSB… |
| `lenskart-2025` p.3 | `book_running_lead_managers` | Axis Capital Limited | Kotak Mahindra Capital Company Limited; Morgan Stanley India Company Private Limited; Avendus Capital Private Limited;… |
| `lg-electronics-india-2025` p.10 | `book_running_lead_managers` | Axis, Morgan Stanley, JPM, BofA and Citi | Axis Capital Limited; Citigroup Global Markets India Private Limited; Morgan Stanley India Company Private Limited; J.P… |

<!-- generated:failures end -->

## Ethical considerations

The model reads public offer documents only; it sees no personal data beyond names printed in them (promoters, managers). Wrong values could mislead an investor, so every value carries its page and a ✅/⚠️/❌ check, and the app never turns a value into advice.

## How to use and reproduce

`finsight.extract` loads the weights from `models/extractor/seed-<n>` (the best epoch of each Kaggle run; weights are never committed). To reproduce: build the weak labels (`python -m finsight.weaklabel`), run `notebooks/01_finetune_extractor.ipynb` on Kaggle (the Kaggle steps are the same as in [Retrain the risk classifier](../howto/retrain_classifier.md)), score the gold set with `uv run python -m finsight.evaluate.run_gold`, then rebuild the table with `uv run python -m finsight.evaluate.ladder`.
