# C01 — Strategy: how FinSight beats general chatbots (honestly)

## 1. The goal

> FinSight's analysis of a new Indian IPO offer document should be **more accurate, better evidenced and more consistent** than what a retail investor gets by uploading the same PDF to Claude Opus or ChatGPT — and we prove it on a frozen benchmark.

"Better" means **measured on FinSight Bench (C04)**, never asserted.

## 2. Where we can win, and how we prove each

| Axis | Why FinSight should win | Bench measure (C04) |
| --- | --- | --- |
| **Numeric accuracy** | Indian-format normaliser (lakh/crore, ₹, Indian grouping, table-header scales) + deterministic verifier; chatbots mix scales | Fact NVM, scale-error rate |
| **Evidence** | Every value tied to page + words; chatbots cite loosely or not at all | Citation accuracy (right page) |
| **Coverage of 500–700 pages** | We parse every page; chatbots may truncate or skim very long PDFs | Fact coverage, red-flag "not found" rate |
| **Comparison with past IPOs** | Risk bank + rolling reference window (C02 §5); chatbots have no corpus | Novelty precision (E22), rewrite of "how unusual" questions |
| **Consistency** | Same document → same facts and flags every time | A property of the deterministic pipeline, stated as such, not scored as a win (bench Task E is cut, C05 §5) |
| **Abstention** | Says "not in the document" instead of guessing | Abstention accuracy on unanswerable questions |
| **Cost, privacy, offline** | Open-weight, runs locally | Per-document fee (none for FinSight; it runs locally), data leaves the machine (yes/no) |

## 3. Where we expect to lose (and will say so)

- Open-ended explanation and business reasoning ("is this a good business model?" — which we refuse anyway).
- Fluency of free-text answers versus a frontier model.
- Questions that need knowledge outside the document.

The report keeps a **"Where FinSight loses"** section filled from the bench, whatever it shows.

## 4. Claim rules (what may go in slides, README and the report)

1. A "better than X" claim needs a bench result where the 95 % interval of the **paired difference** excludes zero (C04 §6). Otherwise the wording is "on par".
2. Every claim names the conditions: the date-free "bench version", the frontier app and plan (Claude.ai with Opus; ChatGPT Go), how the PDF was given, n.
3. No claim about markets, returns, or "better investment decisions". FinSight is a disclosure-reading tool (SEBI, B-ADR-13).
4. The contribution claim (report abstract) is rewritten **after** the bench, from its numbers.

## 5. Competitors

Two kinds exist:

1. **LLM-wrapper analysers** — upload an RHP, get a generated report or dashboard (several exist, including prompt templates that turn a DRHP into a "red flags" dashboard). They publish no accuracy numbers and give no per-value evidence.
2. **IPO information sites and broker apps** — hand-curated key facts (issue size, price band, dates) and news; no reading of the full document, no risk analysis.

FinSight's position: **the only one that shows its evidence for every number and publishes how often it is right.** The bench is the moat as much as the models.

We do not benchmark against competitor sites (terms of use, no stable access); the report describes them qualitatively.

## 6. The three levers that decide whether we win

1. **Data that matches what users upload** — newest IPOs, time split (C02).
2. **Label quality** — the teacher is the ceiling for both the classifier and the simplifier, so the teacher gets the best GPU and a blind bake-off (C03 §3).
3. **An improvement loop** — bench v1 → error analysis on the **dev** slice only → targeted fixes → bench v2 on the untouched test slice (C04 §7).

## 7. Proposed ADRs (C-ADR-NN; Claude Code records them in `docs/09_DECISIONS.md` + `docs/phase3/C_DECISIONS.md` in C0.1)

| ID | Decision |
| --- | --- |
| C-ADR-01 | Phase 3 is gate-driven; no dates in plans. The course deadline lives only in the CLAUDE.md header. Evaluation records keep their timestamps. |
| C-ADR-02 | Strict time split by offer-document date: every `train` document is dated before every `test` document (the cut is the earliest test-slice document, which may be a showcase IPO). Showcase IPOs keep their B04 roles from `configs/demo_ipos.yaml`. Leakage is checked on committed manifests by `ipo_id` and company key. |
| C-ADR-03 | "Compared with past IPOs" uses a rolling window of IPOs **before** the document's date (4 years; corpus rows by close year), never later ones. Two references: *eval* (as of each test IPO, excluding test/bench, never stored in configs) and *product* (all collected IPOs before today; never an input to threshold fitting). Window n is reported per as-of date. |
| C-ADR-04 | Colab (Google AI Pro compute units) is the main GPU for heavy jobs (teacher, student); Kaggle for small, CLI-launched jobs; laptop never trains. |
| C-ADR-05 | Teacher chosen by a blind bake-off rated by Akshat. |
| C-ADR-06 | FinSight Bench is pre-registered and frozen before the first frontier run. |
| C-ADR-07 | Frontier systems: Claude Opus (Claude.ai paid plan) and ChatGPT Go (ChatGPT app), used as a retail investor would; memory and web search off; plan and exact model string recorded per run. |
| C-ADR-08 | Offer-document downloader policy: official sources only, polite rate, never re-hosted. |
| C-ADR-09 | SME IPOs excluded from Phase 3 (different format and rules); future work. |
| C-ADR-10 | A Google Cloud free trial is active (this corrects B-ADR-16's "credit used up" premise; the code stays local-only). It is used only at C5.1. No paid resource and no upgrade without a budget alert first and Akshat's explicit "go". |
| C-ADR-11 | Gold values used to score frontier models are verified by Akshat against the page, never accepted from any model's pre-fill unchecked. Pre-fill mixes FinSight and Claude-chat values with the source hidden, and changes are recorded per field (bias rule, C04 §3). |
| C-ADR-12 | Kickoff scope: cuts 1–5 of C05 §5 applied now; the critical path and cut line in C05 §6 decide further cuts (accepted at the kickoff review). |
