# PROGRESS — CC (Phase 4)
<!-- ≤15 lines, overwrite each session. Newest state only. -->
Date: 2026-10-21
Done: CC-01, CC-02 (merged). CC-04 cache v2 (PR to main, merge commit): preflight, cache key = pdf sha + `pipeline_version` + models fingerprint, `complete|degraded|failed` + reasons, stale → re-run on open, DELETE + re-analyse (API + `CacheBar` UI), `scripts/purge_degraded.py`, migration 0002. 2145 py tests + 136 vitest green; Playwright not run.
In progress: nothing open. Next session: CC-05a Jio diagnosis on **Opus**, diagnosis only, then STOP for Akshat's review.
Blocked: none. CC-03 (Platform Bench ingest) waits until Akshat has filled ≥5 IPOs. `comms/to_cc.md` does not exist yet: ARGON has not posted `sod_fixture_ids`; when it does, export those 10 docs' word positions first thing.
Notes: CC works in worktree `../FinSight-cc` (junctions to data/raw, data/store, models; `frontend/node_modules` junction to the main checkout's). Showcase IPOs are not deletable through the API (403); uploads only.
Gates: G0 [~] G1 [ ] G2 [ ] G3 [ ]
