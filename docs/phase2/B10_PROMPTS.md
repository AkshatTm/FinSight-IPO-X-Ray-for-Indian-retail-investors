# B10 — Claude Code prompts for Big Phase 2 (cloud + local)

**Which prompt when**

| Situation | Where | Prompt |
|---|---|---|
| Very first Phase 2 session (review + plan) | ☁️ cloud session, **Opus** | C0 + C1 |
| Next cloud part (☁️ in B07) | ☁️ new cloud session, model per B07 | C0 + C2 |
| Local part or local follow-up (💻 in B07 / AKSHAT_TODO) | 💻 local, after `/clear` | L1 |
| Unattended night (local, Sonnet parts only) | 💻 local | L3 |
| Stuck | either | 4 |
| Gate review | 💻 local | 5 |
| Documentation pass (B4.1) | ☁️ cloud, Sonnet | C0 + 6 |

Starting a cloud session: claude.ai/code (or the desktop/mobile app) → choose the FinSight repo → pick the model → paste the prompt. In the CLI: `claude --cloud`.

---

## C0 — Cloud note (paste at the top of EVERY cloud-session prompt)

```text
CLOUD SESSION NOTE: You are running in a Claude Code cloud session with the GitHub repo only: no data/raw, data/processed, models/, PDFs, Ollama, GPU or credentials. Follow docs/phase2/B11_CLOUD_WORKFLOW.md. Only do work that can be built and tested with committed code, data/samples, data/gold, tests/fixtures/real/ (real section text for the 10 showcase IPOs) and eval_results/. Mark tests that need full documents or models with @pytest.mark.local. If a step needs real documents, models, the corpus or credentials, stop that step, add it to docs/AKSHAT_TODO.md under "needs a LOCAL session" with the exact prompt to use, and continue with the next cloud-safe step. Never ask for or store secrets. Finish by merging your PR (CI green, rebase-merge), updating the "Resume here" note in PROGRESS.md, and telling me the local follow-up, if any.
```

---

## C1 — Phase 2 kickoff (cloud, Opus)

```text
BIG PHASE 2 KICKOFF. These are my instructions.

FinSight is changing from "find facts in 10 prospectuses" to "upload any IPO offer document and understand, in plain English, what could go wrong and how risky it looks". Everything from Phase 1 stays. The plan is in docs/phase2/ (B00–B11). Deadline 1 Nov 2026, feature freeze 25 Oct. We work in a hybrid way: cloud sessions for code/docs, local sessions for real data/models/deploys (B11).

STEP 1 — Read fully, in this order: CLAUDE.md, PROGRESS.md, docs/phase2/B00_README.md, B11_CLOUD_WORKFLOW.md, B01_PRD.md, B02_ARCHITECTURE.md, B03_MODELS_AND_TRAINING.md, B04_DATA_AND_EVALUATION.md, B05_UI_SPEC.md, B06_API_CONTRACT.md, B07_ROADMAP.md, B08_DECISIONS.md, B09_DOCUMENTATION_STANDARDS.md, B10_PROMPTS.md. Skim the Phase 1 docs they reference (02, 06, 09, 12, EXECUTION_PLAN.md) and the code layout (src/finsight, frontend/) with targeted searches.

STEP 2 — Review before building. Reply with:
(a) a 10-line summary of Phase 2 and what "done" means at BG0–BG3;
(b) every contradiction, gap or risk you find, between the B docs, against the Phase 1 docs, and against the actual code (file + section), each with a proposed fix. Be critical: especially summary/financial extraction across unseen PDFs, risk segmentation, the cloud/local split (is each ☁️ part really doable with the repo + fixture pack?), Colab/Kaggle steps, Cloud Run GPU + vLLM, Supabase auth, costs, and the timeline;
(c) all questions you need me to answer, in one numbered list, each with a default.
Then STOP and wait for my answers.

STEP 3 — After my answers, write docs/phase2/B_EXECUTION_PLAN.md: every sub-phase/part in B07 with location (☁️/💻/👤), issue title, branch, model (O/S), concrete files to create/change, tests that prove it's done, 3–10 planned meaningful commit messages, dependencies, and the hand-work it needs from me with dates. Include the fixes I approved. Do the B0.2 work in the same branch (docs/b0.2-phase2-docs): pointers in Phase 1 docs, CLAUDE.md update, B-ADRs as proposed, issues for B0–B1 with location labels (cloud/local/akshat). Open the PR and STOP for my approval.

CLAUDE.md update must add:
- Environment rule: detect cloud vs local; in cloud, follow the cloud note and B11.
- Phase 2 session protocol: one sub-phase/part per session; model check in both directions (B07 §0); the /clear protocol for local sessions and "one part = one new cloud session" for cloud; the "Resume here" note at the top of PROGRESS.md; the hand-off loop (cloud PR → local git pull → local part).
- New packages and the cloud profile; never commit credentials; never deploy or spend cloud credits without my explicit "go" in chat.
- Documentation-as-code (B09).

STEP 4 — After I approve and you merge the PR, list the next ☁️ parts I can start in new cloud sessions and the 💻 parts for my laptop (B0.1, B0.4 first), each with the exact prompt (C0+C2 or L1). Then stop.

Standing rules (unchanged from Phase 1): plan before >50-line changes (in the PR description), never fake or hand-edit results, never add buy/apply/avoid wording, honesty about AI-assisted labels, tests first, meaningful commits only, rebase-merge.

Begin with STEP 1 and STEP 2 now.
```

---

## C2 — Next cloud part (cloud, model per B07)

```text
Resume FinSight Big Phase 2 in a cloud session. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B11_CLOUD_WORKFLOW.md and docs/phase2/B_EXECUTION_PLAN.md. Do sub-phase part <ID, e.g. B1.2> only (it must be marked ☁️). Read only the B-doc sections it cites. Run the tests (cloud-safe ones) and report the result in one line. State in 3 lines: what you'll build, what you'll test with (which fixtures), and the local follow-up it will need. Write the plan in the PR description, then follow the per-sub-phase loop: issue → branch → tests first → green commits → docs updated → PR → CI green → rebase-merge → close issue → PROGRESS.md + B07 ticks → local follow-up written to AKSHAT_TODO.md with its exact L1 prompt.
```

---

## L1 — Local part / follow-up (after `/clear`)

```text
Resume FinSight Big Phase 2 LOCALLY. First `git pull` (cloud sessions merge PRs on GitHub). Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase2/B_EXECUTION_PLAN.md and the "needs a LOCAL session" list in docs/AKSHAT_TODO.md. Do part <ID, e.g. B1.3b> only. Run the tests (including @pytest.mark.local ones relevant to this part) and report in one line. Do the model check (both directions). Keep the session short and specific: real documents / corpus / models / Kaggle launches / evaluation / deploy steps, one heavy job at a time, Ollama only if needed. Never deploy or spend cloud credits without my explicit "go" in chat. End with the PR merged, the AKSHAT_TODO item ticked, PROGRESS.md updated, and the /clear message (B07 §0).
```

---

## L3 — Overnight mode (local, Sonnet parts only)

```text
OVERNIGHT MODE (Phase 2, local). These are my instructions. I'm asleep.
`git pull`, then read CLAUDE.md, PROGRESS.md ("Resume here"), docs/phase2/B_EXECUTION_PLAN.md, B07 and the "needs a LOCAL session" list. Work through 💻 local parts marked S whose dependencies and hand-work are done, in roadmap order. Skip ★/O parts, ☁️ parts (they belong to cloud sessions), and anything needing my hand-work or credentials (list them in docs/AKSHAT_TODO.md).
- No stops for plan approvals or gates: plans in PR descriptions, gate checklists in docs/gates/BGx.md.
- Nobody can type /clear: rely on auto-compaction; after every merge update PROGRESS.md "Resume here" and docs/MORNING_REPORT.md (new section "Overnight <date>").
- Never: deploy to the cloud, spend credits, start Colab, force-push, rewrite history, delete data/gold, commit secrets/PDFs/weights, change B01 scope.
- Stop only after 3 identical failures (write BLOCKED.md, move on) or if free RAM stays under 1.5 GB (pause heavy steps).
Begin now.
```

---

## 4 — Stuck (either)

```text
We're stuck on <ID>. Read BLOCKED.md. In 5 lines: what failed and why you think so. Then 2–3 alternatives with trade-offs and a recommendation, including whether to move the work cloud↔local or cut scope per B07 §2. No code until I choose.
```

---

## 5 — Gate review (local)

```text
Gate review for BG<n>. `git pull`. Check every "must be true" item for BG<n> in docs/phase2/B07_ROADMAP.md against the real repo and the real pipeline (run tests incl. local ones, read eval_results/b/, try the flow on real documents). Report each as PASS / FAIL with evidence. For each FAIL, propose the smallest fix, the cloud/local part that should do it, or the cut from B07 §2. Write docs/gates/BG<n>.md, update PROGRESS.md, then stop.
```

---

## 6 — Documentation pass (B4.1, cloud, Sonnet; paste C0 first)

```text
B4.1 documentation pass. Read docs/phase2/B09_DOCUMENTATION_STANDARDS.md fully. Build the MkDocs Material site with the exact navigation in §2, generate reference pages (API from openapi.json via Redoc, Python via mkdocstrings, config, red-flag and risk-level rules, data formats, CLI), write tutorials and how-tos, model cards and datasheets from the templates (numbers only from eval_results/), the runbooks, SECURITY/PRIVACY/CONTRIBUTING/CHANGELOG/CODE_OF_CONDUCT, C4 diagrams, the evaluation page with generated tables, troubleshooting, glossary, and rewrite README per §3. Add the docs CI checks in §9 and the GitHub Pages workflow. Mark anything needing my voice "DRAFT — Akshat". Add "test the deploy and rollback runbooks once" to AKSHAT_TODO.md as a local follow-up. Follow the per-sub-phase loop.
```
