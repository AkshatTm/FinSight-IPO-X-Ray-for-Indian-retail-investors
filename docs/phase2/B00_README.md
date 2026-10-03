# Big Phase 2 — Documentation index

**What Big Phase 2 is:** FinSight changes from "find facts in 10 prospectuses" to **"upload any IPO offer document and understand, in plain English, what could go wrong and how risky it looks."**
**Period:** Sun 4 Oct → Sun 1 Nov 2026 (feature freeze Sun 25 Oct).
**Owner:** Akshat Tomar · built with Claude Code · designed with Claude (chat).

All Phase 1 docs (`docs/00`–`12`) stay valid unless a Phase 2 doc says otherwise. Phase 2 docs live in `docs/phase2/` and use the prefix **B** (for "Big Phase 2"). Sub-phases are numbered **B0.1, B1.1 …** and gates **BG0–BG3**, so they never clash with Phase 1 IDs (P0.1, F1, G1 …).

## Reading order

| # | Doc | Owns | Read when |
|---|---|---|---|
| B00 | `B00_README.md` | This index, precedence | Always first |
| B01 | `B01_PRD.md` | What we build and why: features, journeys, requirements, wording rules, success metrics | Before any Phase 2 work |
| B02 | `B02_ARCHITECTURE.md` | Upload pipeline, jobs, new modules, schemas, cloud design, security, cost controls | Before touching backend or cloud |
| B03 | `B03_MODELS_AND_TRAINING.md` | Every model, where it trains (Kaggle / Colab / none), data generation, notebooks, budgets | Before any model or notebook work |
| B04 | `B04_DATA_AND_EVALUATION.md` | New gold labels, experiments E13–E24, metrics, validation of the risk level | Data / eval work |
| B05 | `B05_UI_SPEC.md` | New screens and **all copy** (English), states, layout, landing changes | Before any frontend work |
| B06 | `B06_API_CONTRACT.md` | New endpoints, auth, job events, payloads | Backend + frontend integration |
| B07 | `B07_ROADMAP.md` | Sub-phases, Opus/Sonnet routing, dates, gates, cut order, `/clear` points, hand-work | **Every session** |
| B08 | `B08_DECISIONS.md` | New ADRs (B-ADR-01 …) and which Phase 1 ADRs change | When something looks odd |
| B09 | `B09_DOCUMENTATION_STANDARDS.md` | Industry-grade documentation the project must ship with | Throughout; mainly B4 |
| B10 | `B10_PROMPTS.md` | Kickoff, resume (after `/clear`), overnight, stuck and gate-review prompts; **cloud and local versions** | Akshat, each session |
| B11 | `B11_CLOUD_WORKFLOW.md` | **Where work runs**: cloud sessions vs local sessions vs Akshat, fixture pack, hand-off loop, credit budget | Before starting any session |

## Precedence

1. A direct instruction from Akshat in the current session (Claude Code points out conflicts first).
2. Phase 2 docs over Phase 1 docs where they disagree (and the Phase 1 doc gets a one-line note pointing here, in the same PR).
3. Within Phase 2: `B11` decides where work runs, `B06` wins on payloads, `B02` on module boundaries, `B07` on order and dates, `B01` on scope, `B05` on anything visible on screen, `B04` on metrics.

## What stays from Phase 1 (unchanged)

Parser, section finder, tables, number normaliser, rules + fine-tuned DeBERTa extractor, retrieval, verifier, advice/privacy guard, chat + SSE, Hindi voice for chat, Model Lab, demo mode, the 10 showcase IPOs, all honesty rules, git workflow, testing standards.

## What changes (summary)

- Any user (signed in with Google) can upload an RHP, DRHP or final Prospectus.
- New: **red-flag scorecard**, **plain-English risk report** (English only), **risk level (Low / Medium / High) with reasons**, **comparisons**.
- New models: risk-category classifier (base on Kaggle, large on Colab), teacher → student simplifier (Colab Pro).
- Public deployment on **Google Cloud Run** (CPU API + L4 GPU worker, scale to zero) + Vercel + Supabase.
- Phase 1 ADR-005 ("never use rating labels") is narrowed: outcome data may be used **only to validate** the risk level, never to train a buy/avoid predictor (B-ADR-03).
