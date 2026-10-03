# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 1 log: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Big Phase 2, B0 (setup) → BG0 Mon 5 Oct. Plan: `docs/phase2/B07_ROADMAP.md` + `docs/phase2/B_EXECUTION_PLAN.md`.
- **Last done:** B0.K kickoff review + B0.2 docs (#120, PR `docs/b0.2-phase2-docs`), waiting for Akshat's approval and merge.
- **Next ☁️ cloud parts:** B0.3 hosting bootstrap (#122, S); B1.1a validation (#125, S high effort) → B1.2 jobs (#127, O); B2.3a teacher (#133, O). After B0.4: B1.3a (#128, O), B2.1a (#132, O).
- **Next 💻 local parts:** B0.1 workspace bug (#121), B0.4 fixture pack (#123). Exact L1 prompts: `docs/AKSHAT_TODO.md` → "needs a LOCAL session".
- **Open questions:** Colab bought or not (plan is Kaggle-first, works either way); B0.1 bug details; host choice (Azure vs HF) after B0.3.
- **Tests:** 1129 passed, 6 skipped (`uv run poe test`, cloud session, 3 Oct).

## Log
- 3 Oct — B0.K + B0.2 (#120): kickoff review (45 fixes approved) and Akshat's hosting change: CPU-first, cloud-agnostic hosting (Azure Container Apps for Students or an HF Docker Space + Supabase + Vercel; GCP GPU optional), top-15 automatic rewrites on CPU, Kaggle-first training (Qwen ~14B AWQ teacher, ~3–4B student as GGUF Q4), normalised risk level over 2018–2023. B_EXECUTION_PLAN, B00–B11 fixes, B-ADR-01..15 proposed, CLAUDE.md Phase 2 rules, `local`/`postgres` markers, gold v3 template (270 rows), issues #120–#135 with cloud/local/akshat labels.
- Blockers: none.
