# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 1 Oct — Kaggle runs (#40, #42; ADR-042/043): dataset `akshattmo/finsight-weaklabel` (v2) private; smoke PASSED (= runs end to end + outputs; Akshat's call). Quality gate: 25-step loss, dev EM/F1 per epoch, NVM computed locally, best checkpoint only. Zero-shot baseline on dev: EM 0.719 / F1 0.804 / NVM 0.809. Seed 13 running; 42 and 2026 start only if it beats the baseline. Next: P3.3 (Opus) while Kaggle trains.
- 1 Oct — Weak labels v2 (#39): audit 45/50 on v1 (Wilson 78.6-95.7 %, AI-labelled + reviewed); equity-only face value, initials, brackets, whole-list spans; v2 = 1,818 pos / 2,720 neg; ADR-041.
- 1 Oct — P3.2 generation (#37): Ollama backend (think=false guard), EN/HI grounded prompts, injection tests pass live, `generate ask` CLI, bake-off (2b beats 0.8b in EN; Hindi weak); ADR-020. [AKSHAT] rate data/gold/hindi_fluency_sheet.csv 1-5. Next P3.3 is ★ Opus: model switch.
- 1 Oct — P3.1 retrieval built (#35): chunker (tables whole), bm25s, bge-m3 dense, RRF, reranker w/ fallback, `index` stage for 10 IPOs, E6 harness; ADR-040 (measured 6 GB RAM / 2.1 GB VRAM). [AKSHAT] write data/gold/questions_{dev,test}.jsonl (05 §8), then run E6. 02 §12 edit proposed in ADR-040.
- 1 Oct — P2.4 metrics + fine-tune notebook + Kaggle packager: `evaluate/metrics.py` (EM/F1/NVM/bootstrap/Wilson), `notebooks/01_finetune_extractor.ipynb`, `weaklabel/package.py`; ADR-039. [AKSHAT] package + upload (C7), run the 200-slice smoke on Kaggle, then 3 seeds (P2.5); still open: weak-label audit. P2.6 waits on weights.
- 1 Oct — P2.3 weak labelling (#30): 302 corpus IPOs -> 1,869 positives / 2,791 negatives (train 272 IPOs, dev 30), Excel-checked seeds; ADR-038. [AKSHAT] label data/gold/weaklabel_audit.jsonl (50 rows: correct | wrong_span | wrong_value | ambiguous). Next P2.4 (S): model switch.
- G0 passed (P0.2 #14, P0.3 #15, P0.4 #16). CI 'test' required on main; close each issue by hand after merge.
- P0.1: qwen3.5:2b 37 % CPU / 63 % GPU at ctx 4096 (thinking off, ADR-032). RAM 10.2 GB idle, 12.0 GB with model. dev_light = qwen3.5:0.8b.
- Autopilot: stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md, model switch (check Model column before every sub-phase).
- Blockers: none.
