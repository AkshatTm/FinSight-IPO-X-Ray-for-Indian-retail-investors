# C03 — Training: compute, models, budgets

B03 stays the spec for each model. This file changes **where** jobs run, **how big** they are, and adds two jobs (teacher bake-off, extractor v2).

## 1. Who does what

| Resource | Use it for | Who starts it |
| --- | --- | --- |
| **Colab** via Google AI Pro (200 compute units, expiring 90 days after purchase; A100 / L4 / T4; 2 TB Google Drive) | Teacher bake-off + full teacher, student 4B fine-tune (large classifier and 8B student are cut, C05 §5) | **Akshat**, from `docs/phase3/COLAB_STEPS_<job>.md` |
| **Kaggle** (free T4, ~30 GPU-h/week) | Smoke runs, base classifier (3 seeds), extractor v2 (3 seeds), bge-m3 embeddings if the laptop is too slow | Local Claude Code session via the official CLI (ADR-042), or Akshat |
| **Laptop** (RTX 2050 4 GB, 16 GB RAM) | Downloading, parsing, splitting, filters, TF-IDF baselines, bge-m3 embeddings (fits 4 GB with Ollama stopped), ONNX/GGUF inference, evaluation. 16 GB RAM, much of it used by Windows and Claude Code: one model loaded at a time | Claude Code local sessions. **Never training.** |
| **Google Cloud trial** (trial credit) | Nothing until deploy at C5.1 (C08) | Akshat, on "go" |

## 2. Colab rules (every Colab notebook)

1. First cell mounts Drive; all inputs and outputs live in `MyDrive/FinSight/<job>/`.
2. **Checkpoint and resume:** checkpoints are written to the runtime's local disk (fast) and synced to Drive every N items/steps (Drive-mounted writes are slow and lag). Generation jobs append to a JSONL and skip done ids on restart; training resumes from the last synced checkpoint. A disconnect never loses more than ~10 minutes of work.
3. **Smoke first:** `SMOKE = True` runs 20 items / 20 steps on the cheapest GPU (T4) before the real run.
4. **Compute-unit log:** the last cell writes `run_summary.json` with GPU type, wall time, items/steps done and Akshat's reading of compute units before/after (typed into a parameter cell) → copied to `eval_results/c/compute_log.jsonl` by a local script.
5. Weights go to a **private Hugging Face repo** (`AkshatTm/finsight-<model>`) as **adapters, GGUF or ONNX only, never merged fp16** (HF private storage is limited). Drive keeps checkpoints and adapters. Never to git.
6. Disconnect the runtime when the cell finishes (`from google.colab import runtime; runtime.unassign()` at the end, behind a flag).
7. Pin library versions in the first cell (vLLM, transformers, peft, trl, bitsandbytes, llama.cpp commit) and record them in `run_summary.json`. The current teacher notebook pins `vllm==0.8.5.post1` with `VLLM_USE_V1=0`; that old engine is gone in later vLLM and the install downgrades torch on current Colab images. **C0.2's rate-check notebook also installs the candidate vLLM pin and loads a small AWQ model**; the version that works is the pin. AWQ uses `awq_marlin` on L4/A100.

## 3. The jobs

### C2.1 Risk bank (was B2.1b, extended)

- Segment Risk Factors for every `train` + `dev` IPO (corpus + new) and embed with bge-m3 → `data/processed/bank/risk_bank.parquet` with `ipo_id`, `doc_date`, `split`.
- Test/bench IPOs are embedded into a **separate** parquet used only at evaluation time (leakage test checks this).
- Includes the B2.1a golden tests on real fixture pages and E13/E13b.

### C2.2 Teacher bake-off (new, C-ADR-05)

- Candidates (checked on the Hub at kickoff, re-checked when the part runs): `Qwen/Qwen3-14B-AWQ` vs `Qwen/Qwen3-32B-AWQ`, both Apache-2.0. Both are hybrid-thinking models, so `enable_thinking=False` stays.
- **L4-only fallback:** Colab does not guarantee an A100. 32B-AWQ (~19 GB of weights) on an L4 (24 GB) is too tight for useful batching. If no A100 is available, the bake-off is skipped (cut-line item 2, C05 §6) and Qwen3-14B-AWQ (fits an L4) is used directly, logged as an ADR.
- Same 300 risks (dev + train, stratified) through both with the `teacher-v1` prompt; filters applied.
- Akshat rates a **blind, shuffled** sheet: 50 risks × 2 teachers (meaning yes/partly/no, category right yes/no). ~30 minutes.
- Pick by "meaning: yes" rate after filters, then drop rate, then speed. Record as an ADR with numbers → `eval_results/c/teacher_bakeoff.json`.

### C2.3 Teacher full run (was B2.3b, bigger)

- Input: `train` risks, 40–600 words, **max 25 per company**, stratified by year with **extra weight on 2024+**. Target `min(12,000, achievable)` (config `teacher.n_risks`). With ~500 train companies a cap of 20 allows at most ~10–11k, so the export prints the achievable number.
- Colab A100 with vLLM, checkpoint every 200 items. Filters → drop rates.
- Quality-100 from the **full** output (not the pilot): go/no-go ≥ 85 % "same meaning: yes" (B03 §3.4). If no-go: fix the prompt, re-run 500, re-rate.
- Outputs as B03 §3.5; datasheet updated with the chosen model and counts.

### C2.4 Risk classifier (was B2.4b, upgraded)

- TF-IDF + LR baseline (laptop CPU).
- DeBERTa-v3-base: **Kaggle**, 3 seeds.
- DeBERTa-v3-large: **cut** (C05 §5 cut 3); the base model is used.
- Base must beat TF-IDF on **dev** macro-F1; ONNX int8 export checked against PyTorch on dev.
- E16 on gold-150 (drawn from dev/test with the time split). Teacher zero-shot as the ceiling rung.

### C2.5 Student simplifier (was B2.5b, two sizes)

- Bake-off zero-shot on 30 dev risks: Qwen ~4B candidates (as GGUF Q4 on the laptop CPU) → pick base.
- Fine-tune on the filtered teacher pairs on Colab with a `PRECISION` parameter: on L4/A100 the 4B uses **bf16 LoRA without 4-bit** (the current notebook's NF4 + fp16 is the T4 recipe and stays as the T4 option). Merge in the same session, export GGUF Q4_K_M, upload adapters + GGUF.
- **8B variant: cut** (C05 §5 cut 1). The 4B is the default on the laptop. C3.3 measures RAM and speed and tries partial llama.cpp GPU offload on the 4 GB RTX 2050.
- E18 (blind human, gold-50: zero-shot base vs student-4B vs teacher), E19, E20, CPU seconds per rewrite.

### C2.6 Novelty threshold (was B2.2b)

- 60 pairs from dev IPOs against the bank **within the rolling window**; Akshat rates; τ by precision → E22.

### C2.7 Extractor v2 (new)

- Below the cut line (C05 §6 item 3). Re-run weak labelling (`finsight.weaklabel`) over `train` documents including 2024+ RHPs → more and fresher positives.
- Retrain the DeBERTa QA extractor on **Kaggle**, 3 seeds (Phase 1 notebook, new dataset version).
- New ladder row `qa_finetuned_v2`; compared with v1 on the same dev/test gold; kept only if it wins on **dev**.
- Why: facts are the bench task where frontier models are strongest; the extractor must be as good as it can be on 2024+ layouts.

### C2.8 Risk-level thresholds + validation (was B2.6b, rolling window)

- Reference deciles from the rolling window (C02 §5; thresholds fitted on train + dev only); E17; E21 on the corpus years with outcomes as a **risk-points-only** variant (the corpus has no tables, so no red flags), limitation stated; E8 re-run.

## 4. Compute budget (Colab)

The budget is **200 compute units** (Google AI Pro), which expire 90 days after purchase. Plan in **units**, not hours. Colab shows the real hourly rate of each GPU in the Resources panel; **C0.2 replaces the assumed rates below with the observed ones** and re-plans this table.

Assumed rates (to be replaced): A100 ≈ 11–13 units/h, L4 ≈ 5 units/h, T4 ≈ 2 units/h. So 200 units ≈ 15 A100 hours.

| Job | GPU | Assumed hours | Units (approx.) |
| --- | --- | --- | --- |
| Smoke runs (all jobs) + C0.2 rate check / vLLM smoke | T4 (+ a few minutes on L4, A100) | 2–3 | ~10 |
| Teacher bake-off (2 × 300 risks) | A100 | 1–1.5 | ~20 |
| Teacher full (≈ min(12k, achievable) risks) | A100 | 2–4 (vLLM throughput probably makes this < 2 h; kept conservative) | ~50 |
| Student 4B LoRA + merge + GGUF export | L4 / A100 | 2–3 | ~20 |
| ~~Classifier large, 3 seeds~~ | cut | — | 0 |
| ~~Student 8B~~ | cut | — | 0 |
| **Reserve** (disconnects, a teacher re-run after a quality-100 no-go) | — | — | **≥ 100** |

Rules: never debug on an A100; stop the runtime as soon as a job ends. The reserve exists because of the cuts; it buys a second teacher pass if needed. Kaggle carries everything that fits a T4 (classifier base, extractor v2).

## 5. Order and parallelism

```text
C1.x data ──► C2.1 risk bank ──► C2.2 teacher bake-off ──► C2.3 teacher full ──┬─► C2.4 classifier
                                                                                ├─► C2.5 student
                    C1.4 split ──► C2.7 extractor v2 (Kaggle, independent)      └─► C2.6 / C2.8
```

C2.7 needs only the split and weak labels, so it runs on Kaggle **while** the teacher runs on Colab.

## 6. Every trained model ends with

Weights in `models/<name>/` + private HF repo (adapters/GGUF/ONNX); `eval_results/c/*.json` written by scripts; model card (B09 template, "not for investment advice", CC BY-NC-SA note); datasheet for any new dataset; ADR for any choice made.
