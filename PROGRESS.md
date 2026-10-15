# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` + `docs/phase3/C_EXECUTION_PLAN.md`.
- **Last done (C2.5, 4B student, Sonnet):** LoRA r=16 on Qwen3-4B-Instruct-2507, bf16, G4, 2 epochs, 1,290 steps, 1 h 10 m 24 s train time; dev loss 0.353 (0.437 at step 200). Adapter + `simplifier-q4_k_m.gguf` (2.4 GB) in `models/student/` (gitignored) and the private job repo `AkshatTm/finsight-gpu-jobs` (`student/out/`). Gold-50 (test slice, product post-check, single seed): student **49/50** pass vs base **16/50**; mean 43 words vs 79, 0 vs 38 over 60 words (`eval_results/c/student_vs_base_gold50.json`).
- **Flags:** (1) the notebook's GGUF step failed on the first run (llama.cpp converter's older transformers cannot read the new tokenizer_config) and the runtime was recycled; the final adapter is checkpoint-1290 and the GGUF was built in a second step on the same G4 with the original tokenizer files; the notebook now copies the original tokenizer files before conversion (test added, fixed). (2) `metrics.json` was assembled from checkpoint-1290 `trainer_state.json`, so `train_runtime_s` was 0 there; corrected to 4,224 s (`eval_results/c/student_train_metrics.json`). (3) Student runs through Ollama (`finsight-student:q4`, base model's template) for gold-50 generation; `llama_cpp` is not installed locally.
- **Next:** C2.7 extractor v2 (seed values for 2024+ from documents we already have, no new manual labels, gold-v3/demo IPOs out of training); then C3.3. (C1.5 backfill done: 0 → 40 PDFs in `data/raw/bir_backfill/`.)
- **Units (Colab Pro):** 147.28 left after the C2.4 large run (154.98 before, 7.7 used; 171.38 before the 8B, 16.4 used; logged in `eval_results/c/compute_log.jsonl`).
- **Open files / failing tests:** none new (fast suite green apart from the regenerated docs page).

## Log
- C3.2 merged (#233); gold v3 verified by Akshat; E14/E15 final v1 (#236): E14 NVM 0.682 (195 rows), status 0.667, page 0.766; E15 acc 0.646 (130), 0 serious disagreements. RF04/RF05 low = evaluator lacks X-Ray offer facts (fix in C3.7).
- C2.4 done: large (DeBERTa-v3-large, 3 seeds, Colab G4) 0.894 vs base 0.892 on dev, inside the seed spread, lower severe recall; the base stays the classifier; ONNX fp32 is the shipped export
- C2.5 8B variant done and not adopted: gold-50 post-checks 30/50 vs the 4B's 49/50 (outputs too long, 68.7 vs 43.2 words) despite dev loss 0.342 vs 0.353; 16.4 units; serving format checked (raw training format gives the same lengths); the 4B stays the product model (C-ADR-18)
- C2.4 base done: 3 seeds on Kaggle, dev macro-F1 0.892 ± 0.006 vs TF-IDF 0.862, gold-150 0.899; seriousness MAE 0.186 / severe recall 0.56 (dev); ONNX fp32 exact (int8 rejected); large on Colab pending
- C1.5 done: BIR link check (`scripts/check_bir_links.py`): 855 links, 48 direct PDFs live, 780 HTML pages, 27 dead; backfill decision in AKSHAT_TODO
- C3.1a: summary financial tables + financials stage (PR #224); dev coverage: all 11 values in 67% of RHPs, cross-source agreement 257/258.
- C2.5 done (4B): gold-50 human rating: faithful yes base 0.84 / student 0.92 (CI 0.81-0.97) / teacher 0.98, plain English 3.00 / 4.64 / 4.80; post-check rejects cut-off outputs now (base had 9; student and teacher 0)
- C2.5 follow-ups: notebook GGUF fix + test, `train_runtime_s` 4,224 s recorded, model card, E19/E20 + CPU timing (12.3 s per risk, 60 dev risks; FKGL 19.0 -> 9.6; 3/60 rejected), 8B preset + steps ready, gold-50 sheet written
- C2.5 done (4B): student LoRA trained on the G4 (dev loss 0.353, gold-50 post-check 49/50 vs base 16/50), GGUF built; human gold-50 rating, E18-E20, 8B and model card still open
- C2.3b done: `teacher_cleanup` (strict numbers, category remap v1, non-risk titles, severe band); teacher prompt v1.1 tie-break rules; student notebook `RESUME` flag + per-epoch checkpoint
- **CG2 passed** (C2.3): quality-100 rated, faithful 98 % | category_correct 94 % | notes 17 (`data/processed/teacher/quality_sheet.csv` + `quality_ratings.csv`, committed); no teacher rerun. Follow-ups → C2.3b (strict number filter, category remap, title check, severe band). Roadmap back to full scope (no cut line); C1.2/C1.3 ticked.
- C2.3 teacher run: Gemma-4-31B-it on the G4, 12,000 risks in 44.7 min, 10,892 kept; quality-100 sheet written; gold_eval (gold-150 pre-fill + gold-50 teacher) done; G4 released
- C2.2 done: Gemma-4-31B-it wins the blind bake-off (faithful yes 0.98 vs 0.90 / 0.88), C-ADR-05; C0.2 done: vLLM 0.31.0 pin, G4 tier (CG0 passed)
- Colab lane automated: HF job repo IO, `scripts/gpu_jobs.py`, presets, GPU auto-config, auto-disconnect (C-ADR-13 accepted); colab-mcp installed locally
- C2.1 done: bank 29,677 rows (440 IPOs), eval 8,819 (110 test IPOs), teacher input 12,305 achievable at cap 35, 12,000 written; E13b hand-checked (73/75 boundaries)
- C1.4 done: splits frozen (`configs/splits.yaml`, `data/manifests/`), leakage tests green; CG0 setup check passed (HF, Kaggle via `uvx kaggle`, disk)
- C1.2/C1.3 done: 289 docs fetched, 275 parsed, 14 excluded (12 SME, 2 unnumbered risks); section-header dash fix
- C1.3 fix: Risk Factors missed by 6 batch docs (wrapped TOC leaders, unmapped glyphs, singular title, heading fallback); regression tests; all 6 now parse
- C2.8 code: rolling-window reference scores, tercile fit on train+dev, E21 outcomes module with import guard; fit and E21 runs in AKSHAT_TODO
- C2.6 code: novelty tau rule, blind pair sheet, scoring; rating in AKSHAT_TODO
- Blockers: none.
