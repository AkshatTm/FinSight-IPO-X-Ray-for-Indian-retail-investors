# What exists today (v1.0, Phase 3) — per model

Numbers are in `eval/baselines.json` (read from saved result files, with sha256). ADR ids refer to `docs/phase3/C_DECISIONS.md`
(not shipped to you; the facts you need are here). All numbers are single-run or 3-seed as stated.

## Risk classifier (feeds M4)
- **Model:** `microsoft/deberta-v3-base`, two heads trained separately: 10-way category and seriousness **band** (1-4; band 4 = severe;
  seriousness levels 4 and 5 merged because level 5 had 17 rows).
- **Data:** 9,832 train / 1,060 dev rows (`data/classifier_train.jsonl`, `classifier_dev.jsonl`) with **AI labels** from the teacher
  (Gemma-4-31B-it, C-ADR-05; category + seriousness band + hard-fact flag; 98 % faithful, 94 % category-correct on a 100-row human check).
  Test = gold-150 (`classifier_test.jsonl`, human-verified, comes from test-slice IPOs, **evaluation only**).
- **Training:** Kaggle T4, 4 epochs, lr 2e-5, batch 16, max_len 384, seeds 13 / 42 / 2026; model selected on dev macro-F1.
- **Scores (dev, 3-seed mean):** category macro-F1 0.8923 (sd 0.0062); band macro-F1 0.7617, band MAE 0.1862, **severe-band recall 0.5575,
  precision 0.5645 on only 58 severe dev rows** (noisy). `deberta-v3-large` (Colab G4) reached 0.8943 category, inside the seed spread, lower
  severe recall: not adopted. Shipped export: ONNX fp32 (int8 rejected, not exact).
- **Known weakness:** severe bands are under-recalled (the 17-row level 5 merge, small support, AI-teacher bands).

## Student (M1)
- **Model:** `Qwen/Qwen3-4B-Instruct-2507`, LoRA r=16, bf16, 2 epochs on a G4 (about 1 h 10 m), teacher pairs from Gemma-4-31B-it,
  rewrite pairs filtered by strict number rules; Ollama tag `finsight-student:q4` (GGUF Q4_K_M). An 8B variant had lower dev loss but
  worse post-checks (30/50 vs 49/50, outputs too long) and was not adopted (C-ADR-18).
- **Two prompts, both frozen** (`data/student_prompt_template.txt` = rewrite `student-v1`; `data/student_chat_template.txt` (+`_hi`) = chat).
  The rewrite SFT data (10,362 train / 529 dev pairs) is `data/student_v1_train.jsonl` / `student_v1_dev.jsonl` (chat-format `messages`).
- **Rewrite quality (gold-50, test slice, Akshat's blind rating):** faithful 0.92, plain-English 4.64, post-checks 49/50, mean 43.2 words.
- **Chat quality (Bench v1 Task C, 7 test IPOs, single run):** correct on answerable 0.49, **hallucinated numbers on unanswerable 0.333**,
  abstention on unanswerable 0.333. The chat path also has a retrieval abstain gate and the number verifier in front of the user.
- **Known weakness:** invents numbers when the passages do not contain the answer.

## Red flags and severe sentences (feeds M3)
- 13 deterministic checks (RF01-RF13) over extracted values (`summary`), plus five sentence rules in `redflags/severe.py`
  (going concern, default / loan recall, regulator order, fraud, qualified audit). A sentence fires only if no negation/hedge word
  (`no, not, may, could, if, in the event ...`) is in it. A fired sentence forces the risk level to High (C-ADR-19).
- `data/serious_finding_hits.jsonl` holds **every sentence that matched a pattern**, with the rules' `decision`:
  `fired`, `blocked_soft` (negation/hedge), `blocked_no_debt`. M3 should learn actual vs hypothetical vs negated better than the regex.

## Other components you may meet
- Retrieval: BM25 + cross-encoder reranker (ONNX); optional dense embeddings. Guard: keyword advice guard (MuRIL classifier optional).
- Extractor (BiLSTM-CRF v1 / v2), novelty (embedding nearest-neighbour, tau 0.71), risk-level thresholds fitted on 165 full-document IPOs.
  None of these is yours to change.
