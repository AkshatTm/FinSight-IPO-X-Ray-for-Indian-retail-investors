# Models

FinSight uses open-weight models only and calls no paid LLM API (ADR-002, B-ADR-06). Each trained model
has a card in the Hugging Face model-card format: metadata, intended use, training data, procedure and
hyper-parameters, metrics with intervals or seeds, variants not adopted, limitations and ethical
considerations. Numbers in the generated blocks come from `eval_results/` (`uv run poe docs-gen`).

## In the product (v1.1)

| Model | Job in the product | Runs | Card |
| --- | --- | --- | --- |
| Plain-English student: Qwen3-4B-Instruct-2507 + LoRA, GGUF Q4_K_M | Rewrites risk factors; answers chat questions | Ollama (`finsight-student:q4`) | [Student](risk_simplifier.md) |
| Risk classifier: DeBERTa-v3-base, ONNX fp32 | Category and seriousness band of every risk | CPU, upload stage `risks_scored` | [Risk classifier](risk_classifier.md) |
| `BAAI/bge-reranker-v2-m3` (pretrained) | Reranks chat passages | GPU fp16 (CPU fp32 fallback) | [Reranker](reranker.md) |
| `BAAI/bge-m3` (pretrained) | Embeds risks for the "unusual" badge | GPU or CPU, upload stage `risks_scored` | [Reranker](reranker.md) |
| Field extractor v1: DeBERTa-v3-base-squad2 fine-tuned | Cross-checks rule-read facts of the 10 showcase IPOs (offline build only) | offline `--stage qa` | [Field extractor](extractor_qa.md) |

The red-flag checks, the risk level, the number checker and the advice guard are rules, not models.

## Trained but not adopted

| Model | Why not | Card |
| --- | --- | --- |
| Qwen3-8B student | 30 / 50 gold-50 post-checks vs the 4B's 49 / 50 (too long) | [Student](risk_simplifier.md#variants-not-adopted) |
| DeBERTa-v3-large classifier | dev macro-F1 0.894 vs base 0.892, inside the seed spread; lower severe recall | [Risk classifier](risk_classifier.md#variants-not-adopted) |
| Field extractor v2 | better agreement with rule labels, lower gold test NVM (0.696 vs 0.738) | [Field extractor](extractor_qa.md#variants-not-adopted) |
| MuRIL advice guard | 4 / 9 false blocks on held-out fact questions | [Advice guard](guard_muril.md) |
| BiLSTM-CRF | baseline, below the fine-tuned extractor | [BiLSTM-CRF](bilstm_crf.md) |

## Never trained (Phase 4, cut)

Phase 4 planned M1 student v2, M2 salience ranker, M3 event classifier, M4 severity v2 and M5 (the
evaluation of all of them), to be trained by a second agent (ARGON). None was trained; the product keeps the Phase 3
models above ([Project history](../history.md#phase-4-closed)).

## Teacher (not shipped)

Gemma-4-31B-it wrote the training pairs for the student and the labels for the classifier on a Colab
G4 (12,000 risks in 44.7 min, 10,892 kept). It won a blind bake-off against Qwen3-32B-AWQ and
Qwen3.8-27B-FP8 (C-ADR-05). Its outputs have a [datasheet](../phase2/datasheets/teacher_outputs.md).
