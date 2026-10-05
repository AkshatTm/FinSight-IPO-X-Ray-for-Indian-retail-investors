# C03 — Training: compute, models, budgets

B03 stays the spec for each model. This file changes **where** jobs run, **how big** they are, and adds two jobs (teacher bake-off, extractor v2).

## 1. Who does what

| Resource | Use it for | Who starts it |
|---|---|---|
| **Colab Pro** (200 compute units, A100 / L4 / T4, Google Drive) | Teacher bake-off + full teacher, large classifier, student QLoRA (4B and optional 8B) | **Akshat**, from `docs/phase3/COLAB_STEPS_<job>.md` |
| **Kaggle** (free T4, ~30 GPU-h/week) | Smoke runs, base classifier (3 seeds), extractor v2 (3 seeds), bge-m3 embeddings if the laptop is too slow | Local Claude Code session via the official CLI (ADR-042), or Akshat |
| **Laptop** (RTX 2050 4 GB, 16 GB RAM) | Downloading, parsing, splitting, filters, TF-IDF baselines, bge-m3 embeddings (fits 4 GB with Ollama stopped), ONNX/GGUF inference, evaluation | Claude Code local sessions. **Never training.** |
| **Google Cloud trial** | Nothing until deploy (C08) | — |

## 2. Colab rules (every Colab notebook)

1. First cell mounts Drive; all inputs and outputs live in `MyDrive/FinSight/<job>/`.
2. **Checkpoint and resume:** generation jobs append to a JSONL every N items and skip done ids on restart; training saves every N steps and resumes from the last checkpoint. A disconnect never loses more than ~10 minutes of work.
3. **Smoke first:** `SMOKE = True` runs 20 items / 20 steps on the cheapest GPU (T4) before the real run.
4. **Compute-unit log:** the last cell writes `run_summary.json` with GPU type, wall time, items/steps done and Akshat's reading of compute units before/after (typed into a parameter cell) → copied to `eval_results/c/compute_log.jsonl` by a local script.
5. Weights go to a **private Hugging Face repo** (`AkshatTm/finsight-<model>`) and to Drive; never to git.
6. Disconnect the runtime when the cell finishes (`from google.colab import runtime; runtime.unassign()` at the end, behind a flag).
7. Pin library versions in the first cell (vLLM, transformers, peft, trl, bitsandbytes, llama.cpp commit) and record them in `run_summary.json`.

## 3. The jobs

### C2.1 Risk bank (was B2.1b, extended)
- Segment Risk Factors for every `train` + `dev` IPO (corpus + new) and embed with bge-m3 → `data/processed/bank/risk_bank.parquet` with `ipo_id`, `doc_date`, `split`.
- Test/bench IPOs are embedded into a **separate** parquet used only at evaluation time (leakage test checks this).
- Includes the B2.1a golden tests on real fixture pages and E13/E13b.

### C2.2 Teacher bake-off (new, C-ADR-05)
- Candidates: the current Qwen ~14B instruct (AWQ) vs the largest Qwen instruct that fits a Colab A100 with ≥ 4k context (~32B AWQ). Exact checkpoints and licences verified on the Hub when the part runs.
- Same 300 risks (dev + train, stratified) through both with the `teacher-v1` prompt; filters applied.
- Akshat rates a **blind, shuffled** sheet: 50 risks × 2 teachers (meaning yes/partly/no, category right yes/no). ~30 minutes.
- Pick by "meaning: yes" rate after filters, then drop rate, then speed. Record as an ADR with numbers → `eval_results/c/teacher_bakeoff.json`.

### C2.3 Teacher full run (was B2.3b, bigger)
- Input: `train` risks, 40–600 words, max 20 per company, stratified by year with **extra weight on 2024+** (default 12,000 risks; config `teacher.n_risks`).
- Colab A100 with vLLM, checkpoint every 200 items. Filters → drop rates.
- Quality-100 from the **full** output (not the pilot): go/no-go ≥ 85 % "same meaning: yes" (B03 §3.4). If no-go: fix the prompt, re-run 500, re-rate.
- Outputs as B03 §3.5; datasheet updated with the chosen model and counts.

### C2.4 Risk classifier (was B2.4b, upgraded)
- TF-IDF + LR baseline (laptop CPU).
- DeBERTa-v3-base: **Kaggle**, 3 seeds.
- DeBERTa-v3-large: **Colab L4 or A100**, now **3 seeds** (affordable on Colab).
- Pick base or large by **dev** macro-F1 only; must beat TF-IDF; ONNX int8 export checked against PyTorch on dev.
- E16 on gold-150 (drawn from dev/test with the time split). Teacher zero-shot as the ceiling rung.

### C2.5 Student simplifier (was B2.5b, two sizes)
- Bake-off zero-shot on 30 dev risks: Qwen ~4B candidates (as GGUF Q4 on the laptop CPU) → pick base.
- QLoRA on the filtered teacher pairs, **Colab L4/A100 in bf16**; merge; export GGUF Q4_K_M.
- **Optional 8B variant** (same notebook, `BASE_SIZE = "8b"`): trained only if compute units remain after C2.3 and C2.4. The deploy decision (C08) picks which one serves; both are evaluated.
- E18 (blind human, gold-50: zero-shot base vs student-4B vs student-8B if trained vs teacher), E19, E20, CPU seconds per rewrite.

### C2.6 Novelty threshold (was B2.2b)
- 60 pairs from dev IPOs against the bank **within the rolling window**; Akshat rates; τ by precision → E22.

### C2.7 Extractor v2 (new)
- Re-run weak labelling (`finsight.weaklabel`) over `train` documents including 2024+ RHPs → more and fresher positives.
- Retrain the DeBERTa QA extractor on **Kaggle**, 3 seeds (Phase 1 notebook, new dataset version).
- New ladder row `qa_finetuned_v2`; compared with v1 on the same dev/test gold; kept only if it wins on **dev**.
- Why: facts are the bench task where frontier models are strongest; the extractor must be as good as it can be on 2024+ layouts.

### C2.8 Risk-level thresholds + validation (was B2.6b, rolling window)
- Reference quantiles from the rolling window (C02 §5); E17; E21 on the corpus years with outcomes; E8 re-run.

## 4. Compute budget (Colab)

Colab shows the real hourly rate of each GPU in the Resources panel. **The first Colab part (C0.2) replaces the assumed rates below with the observed ones** and re-plans this table.

| Job | GPU | Assumed hours | Share of 200 units (approx.) |
|---|---|---|---|
| Smoke runs (all jobs) | T4 | 2 | small |
| Teacher bake-off (2 × 300 risks) | A100 | 1–1.5 | ~10 % |
| Teacher full (≈12k risks) | A100 | 4–6 | ~35 % |
| Classifier large, 3 seeds | L4 | 3 | ~8 % |
| Student 4B QLoRA + GGUF export | L4 / A100 | 2–3 | ~10 % |
| Student 8B (optional) | A100 | 3 | ~18 % |
| **Reserve** | — | — | **≥ 15 %** |

Rules: never debug on an A100; stop the runtime as soon as a job ends; if units drop below the reserve, the 8B student is cut first (C05 §5). Kaggle carries everything that fits a T4.

## 5. Order and parallelism

```
C1.x data ──► C2.1 risk bank ──► C2.2 teacher bake-off ──► C2.3 teacher full ──┬─► C2.4 classifier
                                                                                ├─► C2.5 student
                    C1.4 split ──► C2.7 extractor v2 (Kaggle, independent)      └─► C2.6 / C2.8
```

C2.7 needs only the split and weak labels, so it runs on Kaggle **while** the teacher runs on Colab.

## 6. Every trained model ends with

Weights in `models/<name>/` + private HF repo; `eval_results/c/*.json` written by scripts; model card (B09 template, "not for investment advice", non-commercial licence note); datasheet for any new dataset; ADR for any choice made.
