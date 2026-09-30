# FinSight — Documentation Index (read this first)

FinSight is an **IPO X-Ray** for Indian retail investors: it reads a 400–700 page Red Herring Prospectus (RHP), extracts the key facts with page-level citations, answers questions in English or Hindi (including voice), and marks every number in an answer as ✅ verified / ⚠️ unverifiable / ❌ contradicted against the source document. Everything runs on open-weight models, locally first, deployed later.

Course: CSE472 Deep Learning for NLP (LPU) · Solo build: Akshat Tomar + Claude Code · **Final deadline: Sun 1 Nov 2026**

> These docs replace the older `FINSIGHT_MASTER_PLAN.md` (v1 and v2) and `FinSight_Feasibility_Research.md`. Do **not** copy those files into this repo; they contain superseded decisions (US/SEC data, hosted LLM APIs, a 12 Oct demo). Why things changed is recorded in `09_DECISIONS.md`.

---

## Reading order

| # | Doc | What it owns | Read when |
|---|---|---|---|
| 00 | `00_README.md` | This index, precedence rules | Always first |
| 01 | `01_PRD.md` | **What** we build and why: scope, priorities, requirements, success metrics | Before any feature work |
| 02 | `02_ARCHITECTURE.md` | **How** it fits together: pipelines, modules, schemas, interfaces, storage, memory plan | Before touching any module |
| 03 | `03_UI_UX_DESIGN.md` | Screens, design tokens, interactions, microcopy (EN/HI), demo mode | Before frontend work |
| 04 | `04_TECH_STACK_AND_RESOURCES.md` | Tools, models, versions policy, Windows setup, compute, budget, accounts | Setup + when choosing a library |
| 05 | `05_DATA_AND_EVALUATION.md` | Datasets, splits, gold labelling, weak-label audit, metrics, experiments | Data/eval/notebook work |
| 06 | `06_API_CONTRACT.md` | Every endpoint, payload, SSE event, error format | Backend API + frontend integration |
| 07 | `07_ROADMAP.md` | **When**: phases, sub-phases, gates, day plan, cut list, status checkboxes | Every session |
| 08 | `08_GIT_WORKFLOW.md` | Issues, branches, commits, PRs, tags, releases | Every session |
| 09 | `09_DECISIONS.md` | Decision log (ADRs): what was decided and why | When something looks odd, or before changing a decision |
| 10 | `10_FINSIGHT_EXPLAINED.md` | Learning doc: every concept explained from scratch + viva questions. Living doc | Akshat: continuously. CC: append a section after each module |
| 11 | `11_CLAUDE_CODE_PROMPTS.md` | Kickoff prompt, resume prompts, stuck + gate-review prompts | Akshat: start of every Claude Code session |
| — | `templates/frontend.CLAUDE.md` | Frontend-specific Claude Code rules | Copied to `frontend/CLAUDE.md` after the Next.js scaffold |
| — | `../CLAUDE.md` | Always-loaded Claude Code rules | Loaded automatically |
| — | `../PROGRESS.md` | 10-line daily status | Start of every session |

## Precedence when docs disagree

1. A direct instruction from Akshat in the current session wins — but Claude Code must point out the conflict first.
2. Otherwise: `06_API_CONTRACT` wins on payload shapes, `02_ARCHITECTURE` on module boundaries, `07_ROADMAP` on dates and ordering, `01_PRD` on scope and priority, `05_DATA_AND_EVALUATION` on metrics and splits.
3. Every resolved conflict gets a new entry in `09_DECISIONS.md` and the losing doc is fixed in the same PR.

## Who may edit what

| Doc | Claude Code may… | Needs Akshat's approval |
|---|---|---|
| `07_ROADMAP.md` | Tick checkboxes, add status notes, add sub-tasks | Moving dates, cutting features |
| `09_DECISIONS.md` | Append new ADRs (status "proposed") | Marking an ADR "accepted" |
| `10_FINSIGHT_EXPLAINED.md` | Append module explanations | — |
| `01_PRD.md`, `02_ARCHITECTURE.md`, `06_API_CONTRACT.md` | Propose edits in a PR | Always |
| Everything else | Fix typos, broken links | Content changes |

## Glossary of tags used across docs

- **[AKSHAT]** human-only task · **[CC]** Claude Code task · **[CC→AKSHAT]** CC prepares, Akshat runs and reports back
- **P0 / P1 / P2** priority (P0 = must ship, P1 = should ship, P2 = only if time)
- **◇** nice-to-have UI element, first to cut
- **G0–G5** checkpoint gates (see `07_ROADMAP.md`)
