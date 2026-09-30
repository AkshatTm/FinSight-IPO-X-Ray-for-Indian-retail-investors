# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 2026-09-30 — P1.4 numerals merged (PR #20): parse_amounts/parse_amount (Indian + Hindi, [●], %, bps, ranges, share counts), equal() at coarser precision, to_unit/format_money, fiscal periods; ADR-034. P1.3 tables merged (#19): Docling on key sections, objects rows 8/8. Next: P1.5 corpus — switch to Sonnet.
- Finding: RHP fresh issue can also be share-denominated with ₹[●] (Tata Capital), so fresh_issue_size needs the Prospectus companion too; Prospectus covers carry the final offer price and amounts.
- [AKSHAT, non-blocking] Eyeball 3 parsed docs: `uv run python -m finsight.pipeline inspect --ipo <id> --stats --page <n>`; paste problems.
- G0 passed (P0.2 #14, P0.3 #15, P0.4 #16). CI 'test' required on main; close each issue by hand after merge.
- P0.1: qwen3.5:2b 37 % CPU / 63 % GPU at ctx 4096 (thinking off, ADR-032). RAM 10.2 GB idle, 12.0 GB with model. dev_light = qwen3.5:0.8b.
- Pending doc edit for Akshat (needs approval): 02 section 9 line for Prospectus passage ids (ADR-033).
- Autopilot: stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md, model switch (check Model column before every sub-phase).
- Blockers: none.
