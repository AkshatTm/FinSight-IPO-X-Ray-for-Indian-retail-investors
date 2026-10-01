# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 1 Oct — P2.4 metrics + fine-tune notebook + Kaggle packager: `evaluate/metrics.py` (EM/F1/NVM/bootstrap/Wilson), `notebooks/01_finetune_extractor.ipynb`, `weaklabel/package.py`; ADR-039. [AKSHAT] package + upload (C7), run the 200-slice smoke on Kaggle, then 3 seeds (P2.5); still open: weak-label audit. P2.6 waits on weights.
- 1 Oct — P2.3 weak labelling (#30): 302 corpus IPOs -> 1,869 positives / 2,791 negatives (train 272 IPOs, dev 30), Excel-checked seeds; ADR-038. [AKSHAT] label data/gold/weaklabel_audit.jsonl (50 rows: correct | wrong_span | wrong_value | ambiguous). Next P2.4 (S): model switch.
- 1 Oct — P2.2 pretrained QA + X-Ray v0 (#28): xray.json for 10/10 IPOs, fresh+OFS=total verified 10/10; `--stage qa` needs the ml group (~8 min); ADR-037 (transformers 5 has no QA pipeline). Next P2.3 is ★ Opus: model switch. Eye-check notes for 3 parsed docs still pending from Akshat.
- 1 Oct — P2.1 rules extractor merged (#27): fields.yaml, extract/rules.py + table.py, dev IPOs 33/33 vs gold; ADR-036. G1 passed, v0.1.0 tagged (gold v1 AI-prefilled + verified, ADR-035).
- G0 passed (P0.2 #14, P0.3 #15, P0.4 #16). CI 'test' required on main; close each issue by hand after merge.
- P0.1: qwen3.5:2b 37 % CPU / 63 % GPU at ctx 4096 (thinking off, ADR-032). RAM 10.2 GB idle, 12.0 GB with model. dev_light = qwen3.5:0.8b.
- Autopilot: stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md, model switch (check Model column before every sub-phase).
- Blockers: none.
