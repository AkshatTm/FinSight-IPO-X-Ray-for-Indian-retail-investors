---
license: apache-2.0
base_model: BAAI/bge-reranker-v2-m3
pipeline_tag: text-ranking
language: [en]
tags: [retrieval, reranking, rag]
---

# Reranker and retrieval (bge-reranker-v2-m3, bge-m3)

!!! info "Status in v1.1"
    **Not trained here.** Two pretrained open-weight models are used as they are:
    `BAAI/bge-reranker-v2-m3` reranks chat passages, and `BAAI/bge-m3` embeds risk factors for the
    "unusual" badge. In profile `local` chat retrieval is **BM25, then the reranker on the top 20**
    (`retrieve: {dense: false, rerank: true, rerank_top_n: 20}`); the dense index is off.

- **Models:** `BAAI/bge-reranker-v2-m3` (cross-encoder, Apache-2.0) and `BAAI/bge-m3` (embeddings,
  MIT), loaded from the Hugging Face cache by `finsight.retrieve` and `finsight.risks`.
- **Precision:** fp16 on the GPU, fp32 on the CPU (`CrossEncoderReranker`). An ONNX int8 export lives in
  `models/reranker_onnx/`; chat does not use it, but its hash is part of the cache fingerprint.
- **Owner:** Akshat · **Evaluation:** `eval_results/retrieval.json`, `eval_results/rerank_dev.json`,
  `eval_results/c/retrieval_profile.json`.

## Intended use

Order the passages of one offer document by how well they answer a chat question, so the student model
sees the right page and the number checker can compare against it. Out of scope: ranking across
documents, the web, or any use outside Vidura chat.

## Evaluation

**Retrieval methods (E5), 56 test questions over 7 test IPOs, recall with 95 % bootstrap intervals**
(`eval_results/retrieval.json`; the dense and hybrid rows use `bge-m3`):

| Method | Recall@1 | Recall@5 |
| --- | --- | --- |
| BM25 | 0.30 [0.27, 0.34] | 0.62 [0.48, 0.75] |
| Dense (bge-m3) | 0.27 [0.18, 0.38] | 0.52 [0.43, 0.63] |
| Hybrid (RRF) | 0.34 [0.27, 0.41] | 0.64 [0.52, 0.77] |
| Hybrid + rerank | 0.46 [0.38, 0.57] | 0.61 [0.46, 0.73] |

The reranker lifts recall@1 (the passage the model reads first); recall@5 does not change. The
product's exact setting (BM25 + rerank, dense off) was chosen for speed and memory; it is not a row of
this file.

**Reranker variants, dev (41 answerable of 50 questions)** (`eval_results/rerank_dev.json`):

| Variant | Recall@1 | Recall@5 | Rerank s / question |
| --- | --- | --- | --- |
| No rerank (hybrid) | 0.317 | 0.561 | 0.00 |
| fp16, 512 tokens (GPU) | 0.341 | 0.561 | 0.79 |
| fp32, 512 tokens | 0.341 | 0.561 | 3.54 |
| ONNX fp32, 512 tokens (CPU) | 0.341 | 0.561 | 41.56 |
| ONNX int8, 512 tokens (CPU) | 0.317 | 0.537 | 26.14 |

**Laptop timing** (`eval_results/c/retrieval_profile.json`, 6 questions, top 20): reranker on the GPU
0.82 s mean per question, on the CPU 42.82 s. On a laptop without a usable GPU the first chat answers
are slow for this reason.

## Variants not adopted

| Variant | Why | Source |
| --- | --- | --- |
| ONNX int8 reranker in chat | lower recall@1 (0.317 vs 0.341) and still 26 s per question on CPU | `rerank_dev.json` |
| Dense retrieval in profile `local` | switched off in the shipped profile; no file compares BM25 + rerank with hybrid + rerank, so the choice is not backed by a measurement | `configs/config.yaml` |
| 1,024-token reranker input | no recall gain over 512 (0.341 / 0.561) | `rerank_dev.json` (`fp32_1024`) |

## Limitations

- 56 test questions over 7 IPOs; intervals are wide.
- Questions were written in English and Hindi in Phase 1 (`retrieval.json` has per-language rows); the
  product is English-only since v1.1.
- The reranker reads 512 tokens: 11.6 % of passages in the dev pools were cut.

## Ethical considerations

A wrong top passage leads to an unverifiable (⚠️) or contradicted (❌) number rather than a silent
error, because the number checker compares against the cited passage. A profile can set an abstain
threshold per method (`retrieve.abstain_thresholds`, ADR-049): below it the chat says it could not
find the answer. Only profile `full` sets one (hybrid + rerank, -4.402); profile `local` has none, so it
never abstains on score.
