# B03 — Models and Training (Big Phase 2)

## 1. Model inventory

| # | Model | Job in the product | Size | Train where | Serve where |
|---|---|---|---|---|---|
| M1 | Fine-tuned DeBERTa extractor (Phase 1) | Key facts | 184 M | Done (Kaggle) | Worker (GPU/CPU) |
| M2 | bge-m3 (Phase 1) | Chat retrieval **+ risk bank embeddings** | 568 M | none | Worker GPU (offline), API CPU int8 (queries) |
| M3 | **Risk-category classifier — base** | Category for each risk | DeBERTa-v3-base 184 M | **Kaggle (T4)** | Worker |
| M4 | **Risk-category classifier — large** | Same; kept if it beats M3 on dev | DeBERTa-v3-large 435 M | **Colab Pro (A100/L4)** | Worker |
| M5 | **Teacher LLM** (open, ~27–32B instruct, 4-bit) | One-time: write category labels + plain-English rewrites for ~5,000 corpus risks | ~30 B | **Colab Pro (A100)** — inference only | not served |
| M6 | **Student simplifier** (open 7–9B instruct + QLoRA) | Plain-English rewrites in the product | ~8 B | **Colab Pro (A100/L4)** | vLLM on Cloud Run L4 |
| M7 | Chat answer model | Chat answers (cloud) | same base as M6 (no adapter) or M6 | none | vLLM on Cloud Run L4 |
| M8 | Local chat model (Phase 1) | Laptop dev/demo | qwen3.5:2b / 0.8b | none | Ollama |

All open-weight. No hosted LLM APIs. Every model choice is recorded in an ADR with its licence (teacher and student licences must allow using outputs to train another model and non-commercial use).

**Candidate base models** (final choice by bake-off in B2.3/B2.5, recorded in ADRs):
- Teacher: the strongest open instruct model in the ~27–32B range that fits an A100 at 4-bit with ≥ 8k context.
- Student: an open 7–9B instruct model with good English instruction-following and an Apache/MIT-style licence (e.g. a Qwen3.5 ~9B or similar). Must fit the L4's 24 GB at bf16 or 8-bit with vLLM.

## 2. Where training runs, and why

| Job | GPU memory need | Where | Reason |
|---|---|---|---|
| M3 classifier base | ~8 GB | Kaggle T4 (free) | Small model; free; matches Phase 1 workflow |
| M4 classifier large | ~16–24 GB, faster on A100 | Colab Pro | Large model benefits from A100 |
| M5 teacher generation | ~20–24 GB (4-bit 30B) + long prompts | Colab Pro A100 | Too big for T4 |
| M6 student QLoRA | ~16–24 GB | Colab Pro A100 or L4 | Too big for T4; QLoRA keeps it to one GPU |

**Compute-unit budget (Colab):** priority order M5 → M6 → M4. Before each Colab run, the notebook prints an estimate (GPU type × expected hours). Rules: smoke run on 50 items first; checkpoint every N steps to Google Drive; stop the runtime immediately after; record units used in `PROGRESS.md`.

### 2.1 The four steps for every trained model (hybrid workflow, B11)

| Step | What | Where |
|---|---|---|
| 1. Write | Notebook, data-prep script, evaluation code, smoke test on the fake fixture set (tiny test model, CPU, 1 step) | ☁️ Cloud session |
| 2. Prepare data | Build the real training file from the corpus / teacher outputs; upload to Kaggle (dataset) or Google Drive | 💻 Local session |
| 3. Train | Run on GPU. **Kaggle:** launched by a local session via the Kaggle CLI (token stays on the laptop) or by Akshat on the website. **Colab:** always Akshat (no CLI), using `COLAB_STEPS_<job>.md` | Kaggle / Colab |
| 4. Evaluate + integrate | Download weights to `models/`, run the B04 experiments, plug into FinSight | 💻 Local session |

| Model | 1 Write | 2 Data | 3 Train (by) | 4 Evaluate |
|---|---|---|---|---|
| Teacher outputs (M5) | ☁️ | 💻 export 5,000 risks → Drive | Colab (👤) | 💻 filters + 👤 quality-100 |
| Classifier base (M3) | ☁️ | 💻 train/dev from teacher labels | Kaggle (💻 CLI or 👤) | 💻 E16 |
| Classifier large (M4) | ☁️ | same | Colab (👤) | 💻 E16 |
| Student simplifier (M6) | ☁️ | 💻 filtered pairs → Drive | Colab (👤) | 💻 E18–E20 + 👤 gold-50 |

Cloud sessions never receive the Kaggle token, Drive access or model weights.

**Who runs notebooks:** Claude Code writes them; Kaggle runs can be launched by Claude Code via the Kaggle CLI (Phase 1 permission); **Colab runs are started by Akshat** (Colab has no supported CLI) — Claude Code provides a one-page `docs/phase2/COLAB_STEPS_<job>.md` for each.

## 3. Data generation with the teacher (B2.3)

### 3.1 Input
- Risk bank from the 389-IPO corpus (B02 §7.1), filtered to risks with 40–600 words.
- Sample **5,000** risks stratified by company and year (max 20 per company).
- **Exclusions:** all 10 showcase IPOs and all gold-v2/v3 IPOs (none are in the corpus anyway — corpus ends 2023 — but the exclusion test from Phase 1 still runs).

### 3.2 Teacher prompt (one call per risk, JSON output)
Returns: `category` (one of the 10), `seriousness_1to5`, `hard_fact` (bool), `simple` (≤ 60 words, plain English), `numbers_copied` (list). Rules in the prompt mirror B01 §6 and B02 §8.

### 3.3 Filtering (deterministic, logged)
Drop an example if: invalid JSON; category not in list; any number in `simple` not in the original (verifier); forbidden words; length > 70 words; certainty changed (may→will); duplicate of another rewrite. Report the drop rate per reason.

### 3.4 Quality check before training (Akshat + Claude chat)
- 100 random teacher outputs rated for faithfulness (same meaning? yes/partly/no) and category correctness. Pre-filled by Claude (chat) where Akshat asks, verified by Akshat, disclosed.
- Go/no-go: ≥ 85 % "same meaning: yes" → train the student on the filtered set; otherwise fix the prompt and regenerate a 500-item batch first.

### 3.5 Outputs
`data/processed/teacher/{labels,simplify}.jsonl` (gitignored) + `eval_results/teacher_quality.json` (committed) + a datasheet (`docs/phase2/datasheets/teacher_outputs.md`).

## 4. Risk-category classifier (B2.4)

- Labels: teacher categories on the filtered corpus set (~4,000) → train/dev split **by company** (90/10).
- Gold test: **150 risks from the 10 showcase IPOs**, labelled by Akshat (Claude chat may pre-fill; disclosed), never used for tuning.
- M3 base on Kaggle: 3 seeds (13, 42, 2026), max_length 384, lr 2e-5, 3–4 epochs, class-weighted loss, best-epoch checkpoint by dev macro-F1. Gate: dev macro-F1 must beat a TF-IDF + logistic-regression baseline (trained on the same data, laptop CPU).
- M4 large on Colab: same recipe (lr 1e-5, batch per memory), 3 seeds if units allow (else 1 seed, reported as such).
- Keep the better of M3/M4 by **dev** macro-F1 (never by gold). Report both on gold.
- Ladder for the report: TF-IDF+LR → DeBERTa-base → DeBERTa-large → teacher (zero-shot) on gold-150.

## 5. Student simplifier (B2.5)

- Base: student candidate from §1, bake-off on 30 dev risks (zero-shot with our prompt) to pick it.
- Training data: filtered teacher pairs (original → simple), split by company 95/5.
- QLoRA (4-bit base, LoRA r=16, alpha=32, dropout 0.05, target attention + MLP projections), lr 2e-4, 1–2 epochs, max_seq 1,024, bf16 on A100/L4, gradient checkpointing; checkpoint to Drive every 200 steps; resume flag.
- Merge the adapter for serving (or serve base + LoRA with vLLM's LoRA support); export to `models/simplifier/` and push to a **private** Hugging Face repo (licence note: trained on NC-SA-derived text → release under non-commercial terms if ever published).
- Evaluation (B04): faithfulness (human), readability (FKGL/Flesch), number preservation (verifier), certainty preservation, forbidden words, length; compare **zero-shot base** vs **QLoRA student** vs **teacher** on the same 50 gold risks.

## 6. Embeddings and the risk bank (B2.1–B2.2)

- bge-m3 on GPU (laptop when Ollama is stopped, or a Kaggle T4 for the full corpus); store fp16 vectors.
- Similarity threshold τ for "similar risk": choose on dev by spot-checking 60 pairs at several τ values (Akshat + Claude chat), record in ADR.

## 7. Serving (B3.3)

- vLLM on Cloud Run L4: one service, the student model (merged) at bf16 if it fits, else 8-bit; max_model_len 4,096; `--max-num-seqs 16`; OpenAI-compatible endpoint; API key from Secret Manager.
- The worker image carries M1, M2, M3/M4 (classifier) and calls vLLM for simplification and the API calls vLLM for chat in the cloud profile.
- Local profile: Ollama with a small model + the classifier on the laptop GPU; simplification uses the student model only if it fits (else marked "cloud only" in dev).

## 8. Model cards

Every trained model gets `docs/model_cards/<model>.md` (template in B09): intended use, training data, metrics with n and CIs, limitations, licence, and **"not for investment advice"**.
