# Claude Code prompts — kickoff and resume

Paste **Prompt 1** once, in the first Claude Code session, started from the repo root (Opus). After that, start every new session with **Prompt 2**.

---

## Prompt 1 — Kickoff (first session only)

```text
You are the engineering partner on FinSight, my CSE472 (Deep Learning for NLP) project. I'm Akshat, a B.Tech CSE student building this solo with you. I'm new to NLP, so when you make a design choice, explain it in one or two plain sentences. Deadline: Sun 1 Nov 2026. Feature freeze: Mon 26 Oct.

STEP 1 — Read the docs, in this order, fully:
CLAUDE.md, PROGRESS.md, docs/00_README.md, docs/01_PRD.md, docs/02_ARCHITECTURE.md,
docs/03_UI_UX_DESIGN.md, docs/04_TECH_STACK_AND_RESOURCES.md, docs/05_DATA_AND_EVALUATION.md,
docs/06_API_CONTRACT.md, docs/07_ROADMAP.md, docs/08_GIT_WORKFLOW.md, docs/09_DECISIONS.md,
docs/10_FINSIGHT_EXPLAINED.md (Parts A–B only), docs/templates/frontend.CLAUDE.md.
Do not read anything under data/raw, data/processed, models/ or any PDF.

STEP 2 — Review before building. Reply with:
(a) A 10-line summary of what we're building and what "done" means at each gate (G0–G5), so I know you understood.
(b) Every contradiction, gap or risk you found across the docs (with file + section), and your proposed fix for each. Be critical; don't just agree with the docs.
(c) Any questions you need me to answer before Phase 0. Ask all of them now, in one numbered list.
Then STOP and wait for my answers.

STEP 3 — Write the execution plan. After I answer, create docs/EXECUTION_PLAN.md:
- Every phase and sub-phase from docs/07_ROADMAP.md, in order, each with: ID, GitHub issue title, branch name, owner ([CC] / [AKSHAT] / [CC→AKSHAT]), the concrete files to create, the tests that prove it's done, the planned commits (3–10 meaningful commit messages per sub-phase, following docs/08_GIT_WORKFLOW.md), and which Claude model to use.
- A list of everything I must do by hand, with the date it's needed.
- Fixes from STEP 2 that I approved.
Commit it on branch docs/execution-plan, open the PR, and STOP for my approval.

STEP 4 — Set up GitHub. After I approve: create the labels from docs/08_GIT_WORKFLOW.md §6, one issue per sub-phase for Phase 0 and Phase 1 (later phases get issues when their phase starts), the PR template, and merge the execution-plan PR with --rebase.

STEP 5 — Execute, one sub-phase at a time, starting with P0.2 (P0.1 is mine; I'll confirm it's done). For every sub-phase follow this loop exactly:
  1. Re-read the sub-phase in docs/EXECUTION_PLAN.md and the doc sections it cites.
  2. If the work is > ~50 lines: show a plan (≤ 15 lines) and wait for my "go".
  3. git switch main && git pull --rebase; create the branch.
  4. Tests first where it makes sense; then implement in small steps. Commit each time a test goes green or a coherent step is complete. Push regularly.
  5. Run: uv run poe lint, typecheck, test (and the frontend equivalents for F sub-phases). Fix everything.
  6. Tick the boxes in docs/07_ROADMAP.md, update PROGRESS.md, append the Part C section of docs/10_FINSIGHT_EXPLAINED.md for any new module, add ADRs for non-obvious decisions (status "proposed").
  7. Open the PR (closes the issue), wait for CI, merge with gh pr merge --rebase --delete-branch.
  8. At a phase end: tag + GitHub release per docs/08_GIT_WORKFLOW.md §7, and give me a gate checklist to verify by hand.
  9. Tell me what I need to do next by hand (if anything), then print "✅ <ID> done — run /clear and paste the resume prompt." and stop.

Standing rules: follow CLAUDE.md at all times. Never train models (write notebooks for me). Never read raw data or PDFs. Never fake or hand-edit results. Never add investment advice. If a sub-phase takes more than one session, write BLOCKED.md and stop. If anything in the docs turns out to be wrong in practice, propose a doc fix in the same PR instead of silently diverging.

Begin with STEP 1 and STEP 2 now.
```

---

## Prompt 2 — Resume (start of every later session, after /clear)

```text
Resume FinSight. Read CLAUDE.md, PROGRESS.md and docs/EXECUTION_PLAN.md, find the next unfinished sub-phase, then read only the doc sections it cites. Run uv run poe test first and tell me the result. Then state in 3 lines: the sub-phase ID, what you'll build, and anything you need from me. If it's > ~50 lines, show your plan and wait for "go". Follow the sub-phase loop from the kickoff (STEP 5) exactly.
```

## Prompt 3 — Frontend sessions (after /clear, when the next item is an F sub-phase)

```text
Resume FinSight frontend. Read CLAUDE.md, frontend/CLAUDE.md, PROGRESS.md and the F sub-phase in docs/EXECUTION_PLAN.md, then docs/03_UI_UX_DESIGN.md §1–2, §10 and the section for this sub-phase. Work only inside frontend/ (plus fixtures if the API contract requires). Run pnpm lint, typecheck and test first. Follow the sub-phase loop from the kickoff exactly.
```

## Prompt 4 — When something is stuck

```text
We're stuck on <ID>. Read BLOCKED.md. Summarize in 5 lines what failed and why you think it failed. Propose 2 alternatives with trade-offs and a recommendation, including whether to cut scope per the cut order in docs/07_ROADMAP.md. Don't write code until I choose.
```

## Prompt 5 — Gate review

```text
Gate review for G<n>. Check every "must be true" item for G<n> in docs/07_ROADMAP.md against the actual repo state (run tests, read eval_results/, list files). Report each item as PASS / FAIL with evidence. For each FAIL, propose the smallest fix or the cut from the cut order. Update PROGRESS.md. Don't start new work.
```
