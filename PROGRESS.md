# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 1 Oct — G1 PASS: gold v1 (110 rows, AI-prefilled + verified by Akshat, ADR-035) validates `--complete`; tag v0.1.0. Next P2.1 (S). Eye-check notes for 3 parsed docs not yet received.
- 2026-09-30 — P1.5 corpus merged (PR #21): 389 IPOs (110 RHP + 279 Prospectus texts), 331 with all key sections; exclusion of demo + gold names; `python -m finsight.ingest.corpus build`. [AKSHAT] add gold-v2 names to data/gold/excluded_ipos.txt. P1.7 tooling merged (#22).
- 2026-09-30 — P1.4 numerals (#20) + P1.3 tables (#19) merged: normalize (Indian/Hindi amounts, equal, periods; ADR-034); Docling tables, objects rows 8/8.
- G0 passed (P0.2 #14, P0.3 #15, P0.4 #16). CI 'test' required on main; close each issue by hand after merge.
- P0.1: qwen3.5:2b 37 % CPU / 63 % GPU at ctx 4096 (thinking off, ADR-032). RAM 10.2 GB idle, 12.0 GB with model. dev_light = qwen3.5:0.8b.
- Autopilot: stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md, model switch (check Model column before every sub-phase).
- Blockers: none.
