# Kickstarter — Claude Code (paste as the first message of a fresh session, after /clear)

```
Phase 4 starts now. You are CC, one of two agents on FinSight. The other is ARGON (Gemini 4 Argon in
Antigravity), which owns model training and PDF labelling only. You own everything else.

Akshat has added Phase 4 files to the repo root (they may be untracked):
- docs/phase4/  (P4_PLAN.md, P4_PRODUCT_SPECS.md, P4_MODEL_SPECS.md, P4_HANDOFF_CONTRACT.md,
  P4_GIT_WORKFLOW.md, PROMPTS.md, comms/, PROGRESS_*.md)
- AGENTS.md (ARGON's rules)
- CLAUDE_PHASE4_ADDENDUM.md (to append to CLAUDE.md)

Do this in order. Plan-first rule applies: after step 3, STOP and wait for my approval.

1. Read: CLAUDE.md, CLAUDE_PHASE4_ADDENDUM.md, docs/phase4/P4_PLAN.md, P4_PRODUCT_SPECS.md,
   P4_GIT_WORKFLOW.md, P4_HANDOFF_CONTRACT.md. Skim P4_MODEL_SPECS.md only for what ARGON needs from you.
2. Review phase 3 docs only as needed to reconcile: docs/phase3/C05_ROADMAP.md, docs/phase3/C_EXECUTION_PLAN.md,
   and the ADRs referenced by red flags, risk level, compare, cache/jobs and the student. Use rg, not full reads.
3. Write docs/phase4/P4_EXECUTION_PLAN_CC.md (≤ 120 lines):
   - Conflicts between phase 3 docs and phase 4 docs, and how you resolve them (phase 4 wins unless an ADR makes it
     unsafe — then flag it for me).
   - For CC-01..CC-10: the modules/files you'll touch, the tests you'll add, the model you'll use (Opus for CC-05,
     CC-07; Sonnet otherwise), session count estimate, and the exact handoff-pack exports you'll produce for CC-02
     with the real source paths in this repo.
   - Risks and what you'd cut first if behind (follow P4_PLAN gates).
   - Anything in the Phase 4 files that is wrong for this repo (wrong paths, existing names, things already done).
   Then STOP and show me the plan summary.
4. After approval, do CC-01 then CC-02 per P4_PRODUCT_SPECS.md, pushing as you go per P4_GIT_WORKFLOW.md.
   Finish by touching ml/handoff/READY, posting "## READY handoff pack" in comms/to_argon.md, updating
   PROGRESS_CC.md, and telling me what to verify.

Never read PDFs, weights, data/raw or data/processed. Never edit ARGON's paths.
```
