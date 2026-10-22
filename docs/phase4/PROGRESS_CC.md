# PROGRESS — CC (Phase 4)
<!-- ≤15 lines, overwrite each session. Newest state only. -->
Date: 2026-10-22
Done: CC-01, CC-02, CC-04 (merged). SOD fixtures exported for ARGON's 10 ids → `tests/fixtures/real/sod/` (PR #255, CI green, **awaiting Akshat's merge**; answer in `comms/to_argon.md`). Bench candidates: `data/platform_bench/candidates.csv` (gitignored, 102 rows). CC-05a Jio diagnosis written: `docs/phase4/CC05A_JIO_DIAGNOSIS.md`.
Key finding: Jio's RHP has **no SOD**; 6 readers read only the SOD and fall back to pp. 1–29. p.40 "default" is a hypothetical the hedge filter missed ("in case of"); p.472 is a real SEBI penalty on the Promoter (RIL, ₹3 mn), and ARGON labels such sentences `actual_event`, so M3 won't clear it (needs an entity/materiality rule in CC-07).
In progress: nothing. STOPPED after the diagnosis for Akshat's review (no fixes made).
Next: Akshat decides (1) does "until the price is set" count toward G2's ≥10/13 (RHP-only Jio can reach 7–8 decided), (2) p.472 policy (issuer vs promoter/group, materiality, set aside). Then CC-05 on Opus: SOD-less fallback (Introduction run + chapter readers), fixes sized in the diagnosis table.
Blocked: none. CC-03 waits until Akshat has filled ≥5 Platform Bench IPOs.
Notes: CC works in worktree `../FinSight-cc`. Batch parses live in the main checkout's `data/processed/batch/store/docs/<doc_id>/` (use `--data-root`). Showcase IPOs are not deletable through the API (403).
Gates: G0 [~] G1 [ ] G2 [ ] G3 [ ]
