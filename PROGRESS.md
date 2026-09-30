# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 2026-09-30 — P0.4 recon done (PR #16): configs/demo_ipos.yaml (10 IPOs, 3 dev / 7 test), ingest.registry + ingest.recon, 5 sample rows, ADR-016 (corpus = RHP + Prospectus texts, ~398 usable). G0 review next.
- Dataset finding: file names lie (~170 '_RHP' files are final Prospectuses); 112 RHP + 286 Prospectus by cover; none overlap the 2025 demo set.
- P0.2 (PR #14) and P0.3 (PR #15) merged; CI 'test' is required on main. Issues #4-#13 = P0.2-P1.7; close each issue by hand after merge.
- P0.1 done [AKSHAT]: pnpm 12.8.1, Ollama 0.35.0, driver 617.14. qwen3.5:2b 37 % CPU / 63 % GPU at ctx 4096 (thinking off, ADR-032). RAM 10.2 GB idle, 12.0 GB with model. dev_light = qwen3.5:0.8b.
- Pending doc edit for Akshat (needs approval): 02 section 9 line for Prospectus passage ids (ADR-033).
- Autopilot: stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md.
- Blockers: none.
