# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 2026-09-30 — P0.2 scaffold merged (PR #14): uv project (groups dev/api/ml/asr), poe tasks, ruff/mypy/pytest, pre-commit, backend CI, NOTICE, PR template. Next: add 'require CI' protection on main, then P0.3 core + API skeleton, P0.4 recon.
- STEP 4 done: 28 labels, issues #4-#13 (P0.2-P1.7), main protected (linear history, no force-push).
- P0.1 done [AKSHAT]: pnpm 12.8.1, Ollama 0.35.0, Node 24, driver 617.14 (CUDA 13.4). qwen3.5:2b runs (37 % CPU / 63 % GPU at ctx 4096; thinking must be off, ADR-032).
- Laptop: 16 GB RAM (15.4 usable), RTX 2050 4 GB. RAM 10.2 GB used idle → 12.0 GB with qwen3.5:2b loaded (Ollama ≈ 1.8 GB). dev_light uses qwen3.5:0.8b.
- Current gate: G0 (P0.3, P0.4 left). Demo set: 10 IPOs registered locally (configs/demo_ipos.yaml, commits with P0.4).
- Autopilot: run sub-phases back to back; stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md. Usage limit hit: commit green work, note here, stop.
- Blockers: none.
