# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 2026-09-30 — P1.1 parse merged (PR #17): words + boxes + fonts, header/footer strip, printed page, scanned flag, WebP pages, pipeline build/build-all/inspect. All 20 demo docs parsed (~10-20 s each) + images (~0.15 s/page); eval_results/parse_timing.json. Next: P1.2 sections (★).
- Finding: RHP fresh issue can also be share-denominated with ₹[●] (Tata Capital), so fresh_issue_size needs the Prospectus companion too; Prospectus covers carry the final offer price and amounts.
- [AKSHAT, non-blocking] Eyeball 3 parsed docs: `uv run python -m finsight.pipeline inspect --ipo <id> --stats --page <n>`; paste problems.
- G0 passed (P0.2 #14, P0.3 #15, P0.4 #16). CI 'test' required on main; close each issue by hand after merge.
- P0.1: qwen3.5:2b 37 % CPU / 63 % GPU at ctx 4096 (thinking off, ADR-032). RAM 10.2 GB idle, 12.0 GB with model. dev_light = qwen3.5:0.8b.
- Pending doc edit for Akshat (needs approval): 02 section 9 line for Prospectus passage ids (ADR-033).
- Autopilot: stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md.
- Blockers: none.
