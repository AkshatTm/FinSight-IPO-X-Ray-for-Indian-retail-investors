# Phase 4 docs — index

| File | Who reads it | What |
|---|---|---|
| P4_PLAN.md | both, every session | Goal, ownership, workstreams, gates, targets, compute budget |
| P4_PRODUCT_SPECS.md | CC | What CC builds (CC-01..CC-10) |
| P4_MODEL_SPECS.md | ARGON (CC skims) | Labels L1–L4, models M1–M5 |
| P4_HANDOFF_CONTRACT.md | both | Handoff pack (CC→ARGON), deliveries (ARGON→CC), frozen interfaces, metrics.json |
| P4_GIT_WORKFLOW.md | both | Branches, who writes which paths, push and merge rules |
| PROMPTS.md | Akshat | Every session prompt, in order |
| KICKSTART_CC.md / KICKSTART_ARGON.md | Akshat | First message for each agent |
| P4_EXECUTION_PLAN_CC.md / _ARGON.md | owner agent | Written by each agent in its kickstart session |
| PROGRESS_CC.md / PROGRESS_ARGON.md | both + Akshat | ≤15-line status, overwritten each session |
| comms/to_cc.md / comms/to_argon.md | both | The only channel between agents (each writes only its outbox) |

Install (Akshat): copy `docs/phase4/`, `AGENTS.md`, `CLAUDE_PHASE4_ADDENDUM.md` to the repo root, and
`data/platform_bench/` into `data/`. Then run the CC kickstart; CC-01 commits these files.
