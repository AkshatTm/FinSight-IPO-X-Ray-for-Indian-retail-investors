# PROGRESS — CC (Phase 4)
<!-- ≤15 lines, overwrite each session. Newest state only. -->
Date: 2026-10-22
Done: CC-01, CC-02, CC-04, SOD fixture export (#255) merged. **CC-05b + CC-06** on `p4/cc` (PR to main pending): SOD-less fallback (`summary/locate.py`), SOD part-header TOC fix, heading-voted TOC offset, RF01/03/04/06/08/09/12/13 reader fixes, litigation counted from sections, "in case of" hedge, `sod.json` (financial rows, ratios, strengths, `price_band` slot), `pipeline_version` 4.1.
Jio: 7/13 decided from the RHP (was 1/13); p.40 false serious finding gone; p.472 left for C-ADR-26.
Guard: E14 0.769 → 0.774, E15 0.769 → 0.769; decided checks over 289 RHPs 1,561 → 1,704; 4 docs lost one check (listed in the PR; 2 verified corrections).
In progress: nothing.
Next: CC-07 (Opus): `price_band` API + small UI, `PENDING_PRICE` status for RF05/06/07/11, C-ADR-26 regulator rule, rewire the checks on `sod.json`; then measure Jio with the band.
Blocked: ARGON's `data/gold/sod_fixtures/*/expected.json` (AR-02). `tests/summary/test_sod_fixtures.py` skips until it lands (gate ≥8/10). CC-03 waits until Akshat has filled ≥5 Platform Bench IPOs.
Notes: CC works in worktree `../FinSight-cc`. Batch parses live in the main checkout's `data/processed/batch/store/docs/<doc_id>/` (use `--data-root`). Sweep: `scripts/p4_decided_counts.py`.
Gates: G0 [~] G1 [ ] (waits on AR-02) G2 [ ] G3 [ ]
