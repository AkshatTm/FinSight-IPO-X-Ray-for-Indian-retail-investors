# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Phase 3, gate-driven, local code (C-ADR-01, C-ADR-10). Plan: `docs/phase3/C05_ROADMAP.md` + `docs/phase3/C_EXECUTION_PLAN.md`. GPU lane (Session A, `main`); Session B (C4.1 bench) runs in its own worktree.
- **Last done (overnight, Opus):** C0.2 ✓ (CG0) → C2.2 ✓ (Gemma-4-31B-it, C-ADR-05) → **C2.3 teacher run ✓** on the G4: 12,000 risks in 44.7 min (~4.6 risks/s), **kept 10,892 (90.8 %)**; dropped duplicate 570, certainty_changed 292, number_mismatch 204, invalid_json 36, forbidden_phrase 6 (critical drop rate 4.1 %, bake-off 3.7 %; `eval_results/c/teacher_full_filter_report.json`). Then `gold_eval` on the same G4 (teacher + Qwen3.8 on 200 test-slice gold risks, 6 min); the runtime released the G4 itself.
- **Prepared, not launched:** classifier split (train 9,832 / dev 1,060) + manifests; student split (train 10,363 / dev 529); gold-50 base rewrites (Qwen3-4B-Instruct-2507 zero-shot via Ollama: 16/50 pass the product checks, 30 too long). Student waits for CG2; classifier seeds wait for CG2 + gold-150.
- **Units (Colab Pro, 199 at start):** logged 0.18 (L4 rate check) + 2.09 (G4 rate check) + 4.03 (bake-off) = 6.30. Tonight's G4 session (teacher smoke + full + gold_eval, ~70 min) is **not logged yet**: estimate ~9–11 units at 8.9 u/h; read the Resources panel (before: 193.67) and tell Claude → `scripts/log_compute.py`. Teacher lane so far ≈ 16 of ~60.
- **Morning checklist (in this order):**
  1. Tell Claude the units in the Resources panel (1 min).
  2. **quality-100** (~30 min): `data/processed/teacher/quality_sheet.csv`, `faithful` yes/partly/no, `category_correct` yes/no → "quality-100 rated" → Claude scores (CG2 needs ≥ 85 % yes).
  3. **gold-150** (~45 min): `data/gold/gold150_sheet.csv`, fix `category` where the Qwen3.8 pre-fill is wrong → "gold-150 verified" → Claude runs `gold_sets.py gold150` and the 3 Kaggle seeds (13, 42, 2026).
  4. **60 novelty pairs** (~30 min): `data/gold/novelty_pairs.csv`, `same_risk` yes/no/unsure → Claude scores τ.
  5. After CG2: connect a **G4** (you click) → Claude runs `student_smoke` then `student` (~0.5–0.8 h ≈ 5–7 units) → pulls → `gold_sets.py generate --system student` → blind gold-50 sheet `data/gold/simplify_gold50_sheet.csv` (150 rows) → you rate it (~45 min).
- **C2.7 (below the cut line, not built):** adds extractor v2 from weak labels over `train` incl. 2024+ (ladder row `qa_finetuned_v2`), kept only if it beats v1 on dev. Compute: Kaggle T4 × 3 seeds (free Kaggle quota, 0 Colab units). Effort ~3–5 h (weak-label wiring to manifests + 3 runs + eval). Fits only after CG3 if C3.x is on time; otherwise keep v1 (C05 §6 cut order).
- **Next:** wait for the ratings above; then CG2 score → C2.4 seeds + C2.5 student.
- **Open files / failing tests:** none (fast suite green). Fixed tonight: Colab runner as a subprocess (vLLM `fileno` crash), per-job work folder, `status --wait` retries, gold-50 rates every output.

## Log
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
