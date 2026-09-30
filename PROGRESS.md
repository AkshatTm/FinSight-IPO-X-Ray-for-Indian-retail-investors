# PROGRESS (≤ 10 lines; newest first; Claude Code updates at the end of each sub-phase)

- 2026-09-30 — P0.3 core + contract-first API merged (PR #15): schemas (kind-discriminated values), registry, profile config, ids, JSON logging, 501 route skeleton, openapi.json. Next: P0.4 recon (dataset summary, ADR-016), then G0 review.
- P0.2 scaffold merged (PR #14); CI 'test' is a required check on main (linear history, no force-push). Issues #4-#13 = P0.2-P1.7.
- P0.1 done [AKSHAT]: pnpm 12.8.1, Ollama 0.35.0, driver 617.14. qwen3.5:2b runs (37 % CPU / 63 % GPU at ctx 4096; thinking off, ADR-032). RAM 10.2 GB idle, 12.0 GB with model.
- Laptop: 16 GB RAM (15.4 usable), RTX 2050 4 GB (2591 MiB used by the 2B model). dev_light uses qwen3.5:0.8b.
- Pending doc edit for Akshat (needs approval): 02 section 9 line for Prospectus passage ids (ADR-033).
- Autopilot: stop only for hand-work with nothing unblocked, gates, 01/02/06 edits, irreversible actions, BLOCKED.md.
- Blockers: none.
