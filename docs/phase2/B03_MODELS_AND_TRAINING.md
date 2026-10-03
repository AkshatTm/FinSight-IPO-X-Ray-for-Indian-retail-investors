# B03 — Models and Training (Big Phase 2)

## 1. Model inventory

| # | Model | Job in the product | Size | Train where | Serve where |
|---|---|---|---|---|---|
| M1 | Fine-tuned DeBERTa extractor (Phase 1) | Key facts | 184 M | Done (Kaggle) | Worker CPU (ONNX int8); laptop GPU |
| M2 | bge-m3 (Phase 1) | Risk bank embeddings (+ chat dense retrieval locally) | 568 M | none | Laptop GPU / Kaggle (bank, offline); worker CPU int8 for the ~80 risks of an upload; deployed chat uses BM25 |
| M3 | **Risk-category classifier — base** | Category for each risk | DeBERTa-v3-base 184 M | **Kaggle (T4)** | Worker CPU (ONNX int8) |
| M4 | **Risk-category classifier — large** (optional, first to cut) | Same; kept if it beats M3 on dev | DeBERTa-v3-large 435 M | **Kaggle (T4, fp16, 1 seed)**; Colab optional | Worker CPU (ONNX int8) |
| M5 | **Teacher LLM** (Qwen family, AWQ 4-bit) | One-time: category labels + plain-English rewrites for ~5,000 corpus risks | ~14 B on Kaggle (~32 B if Colab) | **Kaggle T4 / T4×2 with vLLM** — inference only | not served |
| M6 | **Student simplifier** (Qwen ~3–4B instruct + QLoRA) | Plain-English rewrites in the product | ~3–4 B | **Kaggle T4** (fp16); Colab optional | **CPU: GGUF Q4_K_M via llama.cpp**; GPU path: vLLM (optional ~8B variant only if a GPU host appears) |
| M7 | Chat answer model (deployed) | Chat answers on the public site | qwen3.5:2b Q4 GGUF (ADR-022) | none | API CPU via llama.cpp; demo cache for showcase |
| M8 | Local chat model (Phase 1) | Laptop dev/demo | qwen3.5:2b / 0.8b | none | Ollama |

All open-weight. No hosted LLM APIs. Every model choice is recorded in an ADR with its licence. **Qwen family (Apache-2.0)** for teacher and student, so using teacher outputs to train the student is clean; avoid models whose terms restrict output use.

**Candidate base models** (final choice by bake-off in B2.3a/B2.5a, recorded in ADRs; exact checkpoints verified on the Hub at that time):
- Teacher: the best open Qwen instruct model with an AWQ checkpoint that fits the training GPU with ≥ 4k context — ~14B on a Kaggle T4 (16 GB, fp16 compute; T4×2 for more KV cache); ~32B if Colab Pro is bought.
- Student: a Qwen ~3–4B instruct (e.g. the qwen3.5 4B used in the Phase 1 bake-off) that rewrites well after QLoRA **and runs on CPU as GGUF Q4** at ≈ 15 s per risk on 4 vCPU.

## 2. Where training runs, and why (Kaggle-first)

| Job | GPU memory need | Where | Reason |
|---|---|---|---|
| M3 classifier base | ~8 GB | Kaggle T4 (free) | Small model; matches Phase 1 workflow |
| M4 classifier large | ~14 GB fp16, batch 4–8 | Kaggle T4 (1 seed); Colab optional | Optional rung; cut first |
| M5 teacher generation | ~9 GB (14B AWQ) + KV cache | Kaggle T4 / T4×2 with vLLM | Free; launched by a local session with the Kaggle CLI (ADR-042); one session ≈ 1–2 h for 5,000 risks |
| M6 student QLoRA | ~8–12 GB (4B, 4-bit base, seq 1,024) | Kaggle T4 (fp16, gradient checkpointing) | Fits a T4; GGUF export in the same notebook |

**Kaggle budget:** about 30 GPU-hours per week. Planned: teacher pilot 0.5 h + full 2 h, classifiers base 3 seeds ≈ 2 h, large 1 seed ≈ 2 h, student 2 epochs ≈ 3 h, smoke runs ≈ 1 h → ≈ 10–11 h. Rules: smoke run on 50 items first; checkpoint every 100 items / 200 steps to `/kaggle/working` and the output dataset; record GPU hours in `PROGRESS.md`.

**If Colab Pro is bought (optional):** the teacher may move to Colab (~32B AWQ with vLLM on an A100, L4 fallback) and M4/M6 may use it for speed. Akshat starts Colab runs (no CLI) with `docs/phase2/COLAB_STEPS_<job>.md`. Nothing else changes.

### 2.1 The four steps for every trained model (hybrid workflow, B11)

| Step | What | Where |
|---|---|---|
| 1. Write | Notebook, data-prep script, evaluation code, smoke test on the fake fixture set (tiny test model, CPU, 1 step) | ☁️ Cloud session |
| 2. Prepare data | Build the real training file from the corpus / teacher outputs; upload as a private Kaggle dataset (Google Drive only for the optional Colab path) | 💻 Local session |
| 3. Train | Run on GPU. **Kaggle (default):** launched by a local session via the Kaggle CLI (token stays on the laptop) or by Akshat on the website. **Colab (optional):** always Akshat (no CLI), using `COLAB_STEPS_<job>.md` | Kaggle (Colab optional) |
| 4. Evaluate + integrate | Download weights to `models/`, run the B04 experiments, plug into FinSight | 💻 Local session |

| Model | 1 Write | 2 Data | 3 Train (by) | 4 Evaluate |
|---|---|---|---|---|
| Teacher outputs (M5) | ☁️ | 💻 export 5,000 risks → Kaggle dataset | Kaggle (💻 CLI); pilot 500 first | 💻 filters + 👤 quality-100 |
| Classifier base (M3) | ☁️ | 💻 train/dev from teacher labels | Kaggle (💻 CLI or 👤) | 💻 E16 |
| Classifier large (M4) | ☁️ | same | Kaggle (💻 CLI); Colab optional (👤) | 💻 E16 |
| Student simplifier (M6) | ☁️ | 💻 filtered pairs → Kaggle dataset | Kaggle (💻 CLI); Colab optional (👤) | 💻 E18–E20 + 👤 gold-50 |

Cloud sessions never receive the Kaggle token, Drive access or model weights.

**Who runs notebooks:** Claude Code writes them; Kaggle runs are launched by a local Claude Code session via the Kaggle CLI (Phase 1 permission, ADR-042); **Colab runs (optional) are started by Akshat** (no supported CLI) with a one-page `docs/phase2/COLAB_STEPS_<job>.md`.

## 3. Data generation with the teacher (B2.3)

### 3.1 Input
- Risk bank from the 389-IPO corpus (B02 §7.1), filtered to risks with 40–600 words.
- Sample **5,000** risks stratified by company and year (max 20 per company).
- **Exclusions:** all 10 showcase IPOs and all gold-v2/v3 IPOs (none are in the corpus anyway — corpus ends 2023 — but the exclusion test from Phase 1 still runs).

### 3.2 Teacher prompt (one call per risk, JSON output)
Returns: `category` (one of the 10), `seriousness_1to5`, `hard_fact` (bool), `simple` (≤ 60 words, plain English), `numbers_copied` (list). Rules in the prompt mirror B01 §6 and B02 §8.

### 3.3 Filtering (deterministic, logged)
Drop an example if: invalid JSON; category not in list; any number in `simple` not in the original (verifier); a forbidden phrase (`configs/forbidden_phrases.yaml`); length > 70 words; certainty changed (may→will); duplicate of another rewrite. Report the drop rate per reason.

### 3.4 Quality check before training (Akshat + Claude chat)
- 100 random teacher outputs rated for faithfulness (same meaning? yes/partly/no) and category correctness. Pre-filled by Claude (chat) where Akshat asks, verified by Akshat, disclosed.
- Run on the **500-item pilot first** (vLLM, AWQ, checkpoint every 100 items, resume flag), then the full 5,000.
- Go/no-go: ≥ 85 % "same meaning: yes" → full run and train the student on the filtered set; otherwise fix the prompt and regenerate a 500-item batch first.
- Gold-150, quality-100 and the teacher are all LLM-assisted: every set records `label_source` and how many values Akshat changed; results are reported as agreement with Akshat-verified labels, and disclosed.

### 3.5 Outputs
`data/processed/teacher/{labels,simplify}.jsonl` (gitignored) + `eval_results/teacher_quality.json` (committed) + a datasheet (`docs/phase2/datasheets/teacher_outputs.md`).

## 4. Risk-category classifier (B2.4)

- Labels: teacher categories on the filtered corpus set (~4,000) → train/dev split **by company** (90/10).
- Gold test: **150 risks from the 10 showcase IPOs**, labelled by Akshat (Claude chat may pre-fill; disclosed), never used for tuning.
- M3 base on Kaggle: 3 seeds (13, 42, 2026), max_length 384, lr 2e-5, 3–4 epochs, class-weighted loss, best-epoch checkpoint by dev macro-F1. Gate: dev macro-F1 must beat a TF-IDF + logistic-regression baseline (trained on the same data, laptop CPU).
- M4 large on Kaggle T4 (fp16, lr 1e-5, batch per memory), 1 seed (reported as such; Colab optional for more seeds). First to cut.
- Keep the better of M3/M4 by **dev** macro-F1 (never by gold). Report both on gold.
- Ladder for the report: TF-IDF+LR → DeBERTa-base → DeBERTa-large → teacher (zero-shot) on gold-150.
- Serving: the chosen model exported to ONNX int8 for the CPU worker (`scripts/export_onnx_classifier.py`); accuracy of the ONNX export checked against PyTorch on dev.

## 5. Student simplifier (B2.5)

- Base: student candidate from §1, bake-off on 30 dev risks (zero-shot with our prompt) to pick it.
- Training data: filtered teacher pairs (original → simple), split by company 95/5.
- QLoRA (4-bit base, LoRA r=16, alpha=32, dropout 0.05, target attention + MLP projections), lr 2e-4, 1–2 epochs, max_seq 1,024, **fp16 on a Kaggle T4** (bf16 only on Colab A100/L4), gradient checkpointing; checkpoint every 200 steps to the Kaggle output; resume flag.
- Merge the adapter and **export GGUF Q4_K_M** (llama.cpp convert + quantize, in the notebook) for the Cloud Run CPU job; keep the merged fp16 weights (and an AWQ export) for the GPU path. Store in `models/simplifier/` and a **private** Hugging Face repo (licence note: trained on NC-SA-derived text → release under non-commercial terms if ever published).
- Evaluation (B04): faithfulness (human), readability (FKGL/Flesch), number preservation (verifier), certainty preservation, forbidden phrases, length, **CPU seconds per rewrite (GGUF Q4)**; compare **zero-shot base** vs **QLoRA student** vs **teacher** on the same 50 gold risks.

## 6. Embeddings and the risk bank (B2.1–B2.2)

- bge-m3 on GPU (laptop when Ollama is stopped, or a Kaggle T4 for the full corpus); store fp16 vectors. Novelty uses the 2018–2023 part of the bank (B02 §7.1). For an upload, the worker embeds its ~80 risks on CPU (int8).
- Similarity threshold τ for "similar risk": choose on dev by spot-checking 60 pairs at several τ values (Akshat + Claude chat), record in ADR.

## 7. Serving (B3.3) — CPU first

- **Cloud Run CPU job (`cloud`, works without billing for GPUs):** the worker job carries M1 and M3/M4 as ONNX int8, bge-m3 int8 for risk embeddings, and the student as GGUF Q4 through the existing `generate/llama_cpp_backend.py`; it rewrites the top 15 risks automatically and the rest on click. The API serves chat with qwen3.5:2b Q4 via llama.cpp (ADR-022) and the demo cache for showcase questions.
- **Cloud Run L4 GPU job (`cloud_gpu`, once GCP billing is enabled):** vLLM offline with the student (AWQ 4-bit, or an ~8B variant if trained) for simplify, plus bge-m3 for dense chat indexes. The code and images are written now; deploying waits for Akshat's "go".
- **Local profile:** Ollama with a small chat model + the classifier on the laptop GPU; the student GGUF runs locally too.

## 8. Model cards

Every trained model gets `docs/model_cards/<model>.md` (template in B09): intended use, training data, metrics with n and CIs, limitations, licence, and **"not for investment advice"**.
