# B11 — Hybrid workflow: Claude Code cloud sessions + local sessions

**Why:** Akshat has a one-time **$100 Claude Code cloud-session credit** (claim by **Wed 7 Oct 2026, 23:59 PT** at claude.ai/code/claim-credit or `/claim-credit`; usable until 4 Nov). Cloud sessions spend that credit first, before normal plan limits. Moving cloud-safe work there protects the weekly limit for the work that must run on the laptop.

**Precedence:** this file decides **where** each piece of work runs. `B07_ROADMAP.md` lists the sub-phases with their location marks.

## 1. The three places work happens

| Mark | Place | Has | Doesn't have |
|---|---|---|---|
| ☁️ **C** | Claude Code **cloud session** (Anthropic VM, fresh clone of the GitHub repo) | The repo: code, docs, tests, `data/samples`, `data/gold`, `tests/fixtures/real/` (fixture pack), `eval_results/` | `data/raw`, `data/processed`, PDFs, `models/`, Ollama, GPU, any credentials |
| 💻 **L** | Claude Code **local session** on the laptop | Everything: PDFs, corpus, models, Ollama, RTX 2050, Kaggle token, gcloud | — (but uses the weekly plan limit and laptop RAM) |
| 👤 **A** | **Akshat** by hand | Colab (no CLI), browser logins, cloud consoles, labelling, rating | — |

Kaggle, Colab and Google Cloud do the GPU work. **No Claude Code session ever trains a model itself.**

## 2. What goes where (rules of thumb)

- ☁️ **Cloud:** writing code, tests with fixtures, frontend on mocks, API contracts, rule engines, notebooks (written + smoke-tested on tiny fake data), Dockerfiles and CI (written, not deployed), docs site, report drafts, the kickoff review.
- 💻 **Local:** anything that needs real full documents, the corpus, model weights, Ollama, the Kaggle CLI, gcloud deploys, evaluations, demo recording, the Playwright sweep on the real API.
- 👤 **Akshat:** Colab runs, cloud console clicks and logins, gold/rating work (with Claude chat), approving PRs and gates.

## 3. The fixture pack (makes most development cloud-safe)

Built once in **B0.4 (💻 L)** by `scripts/export_fixtures.py`, committed under `tests/fixtures/real/` (target ≤ 20 MB, compressed JSON, **no PDFs, no weights**):
- For each of the 10 showcase IPOs (RHP + Prospectus): only the pages of **Summary of the Offer Document, Basis for Offer Price, restated financial summary, Capital Structure, Objects of the Offer, Risk Factors**. Per page: number, text, words with bbox + bold/size flags.
- **Risk Factors text of 20 corpus IPOs** (stratified by year), plain text.
- A small **corpus statistics file** (`corpus_stats.json`: distributions needed for percentiles and risk-level thresholds; recomputed locally when the corpus changes).
- Small samples of `parsed.json`, `xray.json`, `report.json` for 2 IPOs.
- A tiny fake training set (20 risks with categories and rewrites) for notebook smoke tests.
- `README.md` with sources and licences (public SEBI filings; corpus excerpts CC BY-NC-SA 4.0, Ghosh et al.).

If a cloud step needs data that isn't in the pack, the cloud session writes it to `docs/AKSHAT_TODO.md` → "needs a LOCAL session", and a local session extends the pack.

## 4. Session rules

### Cloud sessions (☁️)
1. **One sub-phase (or half) = one new cloud session.** Starting a fresh session replaces `/clear`.
2. Every cloud prompt starts with the **cloud note** (B10 Prompt C0).
3. Ends with a merged PR (CI green, rebase-merge), `PROGRESS.md` "Resume here" updated, and the local follow-up written to `docs/AKSHAT_TODO.md` with the exact prompt to use.
4. **Never** receives secrets (Kaggle token, gcloud keys, Supabase service key, HF write token).
5. Notebooks are smoke-tested on CPU with the fake fixture set and a tiny test model **only if** the session has internet access to Hugging Face; otherwise the smoke test moves to the local follow-up.
6. Opus only for the kickoff review and ★ cloud parts; Sonnet otherwise (credits burn faster on Opus).

### Local sessions (💻)
1. Always start with `git pull` (cloud work arrives through merged PRs).
2. Keep them **short and specific**: build data, launch Kaggle, evaluate, run on real documents, deploy. `/clear` after each, per B07 §0.
3. Heavy jobs one at a time; Ollama only when needed.

### Hand-off loop for a split sub-phase
☁️ write + test with fixtures → PR merged → 💻 `git pull` → run on real data / launch training → (👤 Colab if needed) → 💻 evaluate + integrate → PR merged → next.

## 5. Credit budget (guide)

The credit balance shows in Claude Code on the web. Rough plan for the $100, by priority:

| Priority | Cloud work | Model |
|---|---|---|
| 1 | Kickoff review + B_EXECUTION_PLAN (B0.2) | Opus |
| 2 | B1.2 jobs/storage/db | Opus |
| 3 | B1.3a, B2.1a, B2.6a (★ parts on fixtures) | Opus |
| 4 | All frontend (B1.5, B3.1, B3.2) | Sonnet |
| 5 | Rules, features, notebooks, Docker/CI (B1.4, B2.2a, B2.3a–B2.5a, B3.3a) | Sonnet |
| 6 | Documentation site + report drafts (B4.1, B4.2) | Sonnet |

**Check the balance after each cloud session.** At ~$20 left, keep the rest for B4.1 (documentation). When the credit runs out, cloud sessions continue on the normal plan limits, the same as local.

## 6. Checklist before the first cloud session
- [ ] 👤 Claim the credit (before 7 Oct) and connect GitHub to Claude Code on the web.
- [ ] 💻 Phase 2 docs committed and pushed (`docs/phase2/`), so the cloud sees them.
- [ ] 💻 B0.4 fixture pack merged (needed by cloud B1.3a and B2.1a; the kickoff review can run before it).
- [ ] 👤 Confirm the repo has no secrets committed (the cloud clones everything).
