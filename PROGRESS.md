# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` (full scope, no cut line) + `docs/phase3/C_EXECUTION_PLAN.md`. Session B (C4.1 bench) has not started (issue #193 open, no branch yet).
- **Last done:** CG2 passed (quality-100: faithful 98 %, category 94 %; PR #217 awaits merge). **C2.3b ✓:** strict number filter dropped 2 rewrites (+9 flagged), 799 categories remapped (7 rules), 22 non-risk titles, severity bands 1/2/3/severe = 1,669 / 5,793 / 2,942 / 488. Student split now train 10,362 / dev 529; classifier split train 9,832 / dev 1,060 (clean labels).
- **Next (Akshat):** (1) tell Claude the Colab units (last night's G4 session, 193.67 before); (2) connect a G4 and run `COLAB_STEPS_student.md` (smoke, then real, ~5-7 units); (3) rate gold-150 (`data/gold/gold150_sheet.csv`, use the 5 tie-break rules in `configs/category_remap.yaml`) and the 60 novelty pairs (`data/gold/novelty_pairs.csv`).
- **Next (Claude):** `gpu_jobs.py push student` once Akshat is ready; then C2.4 classifier seeds on Kaggle after gold-150; code lane C3.1, C3.2 (incl. severe rules), C1.5.
- **Open files / failing tests:** none (fast suite green).

## Log
- C2.3b done: `teacher_cleanup` (strict numbers, category remap v1, non-risk titles, severe band); teacher prompt v1.1 tie-break rules; student notebook `RESUME` flag + per-epoch checkpoint
- **CG2 passed** (C2.3): quality-100 rated, faithful 98 % | category_correct 94 % | notes 17 (`data/processed/teacher/quality_sheet.csv` + `quality_ratings.csv`, committed); no teacher rerun. Follow-ups → C2.3b (strict number filter, category remap, title check, severe band). Roadmap back to full scope (no cut line); C1.2/C1.3 ticked.
- C2.3 teacher run: Gemma-4-31B-it on the G4, 12,000 risks in 44.7 min, 10,892 kept; quality-100 sheet written; gold_eval (gold-150 pre-fill + gold-50 teacher) done; G4 released
- C2.2 done: Gemma-4-31B-it wins the blind bake-off (faithful yes 0.98 vs 0.90 / 0.88), C-ADR-05; C0.2 done: vLLM 0.31.0 pin, G4 tier (CG0 passed)
- Colab lane automated: HF job repo IO, `scripts/gpu_jobs.py`, presets, GPU auto-config, auto-disconnect (C-ADR-13 accepted); colab-mcp installed locally
- C2.1 done: bank 29,677 rows (440 IPOs), eval 8,819 (110 test IPOs), teacher input 12,305 achievable at cap 35, 12,000 written; E13b hand-checked (73/75 boundaries)
- C1.4 done: splits frozen (`configs/splits.yaml`, `data/manifests/`), leakage tests green; CG0 setup check passed (HF, Kaggle via `uvx kaggle`, disk)
- C1.2/C1.3 done: 289 docs fetched, 275 parsed, 14 excluded (12 SME, 2 unnumbered risks); section-header dash fix
- C1.3 fix: Risk Factors missed by 6 batch docs (wrapped TOC leaders, unmapped glyphs, singular title, heading fallback); regression tests; all 6 now parse
- C2.8 code: rolling-window reference scores, tercile fit on train+dev, E21 outcomes module with import guard; fit and E21 runs in AKSHAT_TODO
- C2.6 code: novelty tau rule, blind pair sheet, scoring; rating in AKSHAT_TODO
- Blockers: none.
