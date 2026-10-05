# B07 — Roadmap (Big Phase 2)

> **Superseded in part (4 Oct 2026, B-ADR-16):** Google Cloud (Cloud Run, Cloud Storage, GPU job, `deploy/gcp/`, `cloud` and `cloud_gpu` profiles) was removed when the credit ran out. The product runs locally. Read the Cloud Run, GCS, GPU and deploy parts below as history.

**Written:** Sat 3 Oct 2026 (kickoff review) · **Feature freeze:** Sun 25 Oct · **Final tag v2.0.0:** Sat 31 Oct · **Submission:** Sun 1 Nov

**Detail per part** (files, tests, commits, dependencies, dated hand-work): `B_EXECUTION_PLAN.md`. **Hosting is Google Cloud Run** (B-ADR-04): CPU API + CPU worker job + optional L4 GPU job, Supabase, GCS, Vercel; billing enabled later, no deploy before Akshat's "go". **Training is Kaggle-first**; Colab optional.

> **Phase 3 (C0.1):** every open part below is either done or moved to Phase 3 (`docs/phase3/C05_ROADMAP.md`, ids in brackets). This file is now history; Phase 3 tracks progress.

## 0. How to use this file

- Each sub-phase = one GitHub issue = one branch = one PR (rebase-merge). Branch: `<type>/b<x.y>-<slug>`.
- **Model column:** **O** = Opus (★ hard logic/design), **S** = Sonnet. Bugs that failed twice on Sonnet → Opus.
- **Model check (both directions)** before every sub-phase: if the current model differs from the column, stop and print
  `🔁 MODEL SWITCH: next is <ID> (<title>) — recommended <Opus/Sonnet>. Type /model <opus/sonnet>, then say continue.`
- **`/clear` protocol (keeps context clean):**
  1. At the end of every sub-phase: update `PROGRESS.md` + tick boxes here, then print
     `✅ <ID> done — run /clear and paste the Phase 2 resume prompt.` and stop.
  2. **Mid-sub-phase checkpoint:** if the conversation has been auto-compacted, or a sub-phase has gone through 3+ long tool-heavy steps, then commit everything green, push, write a "Resume here" note (exact next step, open files, failing test names) at the top of `PROGRESS.md`, and print
     `🧹 Checkpoint saved — run /clear and paste the Phase 2 resume prompt to continue <ID>.`
  3. In **overnight mode** (B10 Prompt 3) there is nobody to type `/clear`: keep going, rely on auto-compaction, and write the "Resume here" note after every merge.
- **No cloud sessions (B-ADR-16):** the cloud credit is gone, so every ☁️ part below now runs as a 💻 local session on the laptop (fixtures first, then real data in the same session where it fits).
- Hand-work for Akshat goes to `docs/AKSHAT_TODO.md` with a date; Claude Code continues with any unblocked sub-phase.
- Gates: Claude Code runs the gate review (B10 Prompt 5) and stops (except in overnight mode, where it writes `docs/gates/BGx.md` and continues).

## 1. Gates

| Gate | Date | Must be true | If it fails |
|---|---|---|---|
| **BG0** | Mon 5 Oct | Phase 1 IPO-click bug fixed (or proven not to reproduce); Phase 2 docs merged; CLAUDE.md updated; Kaggle GPU ready (Supabase/Vercel optional; no Google Cloud); B0.4 fixture pack merged | Slip B1 by a day |
| **BG1** | Sun 11 Oct | Locally: upload an unseen RHP → facts + 13 red flags + progressive events; E14/E15 numbers on gold v3; upload UI with Google sign-in | Ship red flags for showcase only; uploads continue in week 2 |
| **BG2** | Sun 18 Oct | Risk report end-to-end locally (split → features → simplified with checks → risk level with reasons); E13, E16, E18–E22 have real numbers; no deploy (B-ADR-16) | Use zero-shot base model for rewrites; drop large classifier |
| **BG3** | Sun 25 Oct | **Complete local demo**: sign in (optional), upload an RHP on the laptop, get a full report (top 15 rewrites automatic, the rest on click); E23/E24 measured locally; Model Lab updated; **FEATURE FREEZE** | Uploads for Akshat's account only; showcase-only demo |

## 2. Cut order (cut from the top if behind)
1. Report "Download summary (PDF)"
2. B3.2 Compare tab
3. M4 large classifier (keep base)
4. Student QLoRA → serve the zero-shot base instruct model with the same prompt and checks
5. Hindi polish for chat/voice
6. Sign-in and multi-user uploads → single local user

**Never cut:** upload pipeline, red flags with pages, risk report with originals and number checks, risk level with reasons + disclaimer, E21 validation (reported whatever it shows), honesty rules.

## 3. Sub-phases

**Location marks (B11):** ☁️ **C** = Claude Code cloud session (repo only) · 💻 **L** = local session on the laptop · 👤 **A** = Akshat by hand. Split sub-phases have an **a** (cloud) and **b** (local) half; do them in order. Each ☁️ part = one new cloud session; each 💻 part ends with `/clear`.

### B0 — Setup (Sun 4 – Mon 5 Oct) → BG0

- [x] **B0.0 Claim the cloud credit + push docs** · 👤 A + 💻 L · — · obsolete (B-ADR-16; Phase 3 C-ADR-10)
  👤 Claim the $100 credit (by Wed 7 Oct) and connect GitHub to Claude Code on the web. 💻 Commit and push `docs/phase2/` (a quick local session or plain git).
- [x] **B0.K Kickoff review** · ☁️ C · **O** (Sat 3 Oct)
  B10 Prompt C1: STEP 2 review and questions → (my answers via Claude chat) → STEP 3 `B_EXECUTION_PLAN.md`, part of B0.2.
- [x] **B0.1 Fix the IPO workspace bug** · 💻 L · **S** · `fix/b0.1-workspace-error`
  Reproduce with Playwright against the real API; fix; regression test opening all 10 workspaces. Done when: all 10 open with facts and page images.
- [x] **B0.2 Phase 2 docs + project rules** · ☁️ C · **O** (done inside the kickoff session) · `docs/b0.2-phase2-docs`
  As before, plus: CLAUDE.md learns the **environment rule** (detect cloud vs local; in cloud, follow the cloud note and B11) and the hand-off loop; issues for B0–B1 with location labels (`cloud`, `local`, `akshat`).
- [x] **B0.3 Hosting bootstrap (no deploy)** · ☁️ C · **S** · `chore/b0.3-hosting-bootstrap`
  `HOSTING_SETUP_STEPS.md` (Supabase + Vercel + Kaggle now; Google Cloud section "later, with your go"), `HOSTING_COMPARISON.md` (Cloud Run CPU vs with L4 vs HF PRO fallback), `.env.example`, `cloud` + `cloud_gpu` profiles, upload limits and kill switch config. 👤 Follow the steps (~45 min).
- [x] **B0.4 Fixture pack** · 💻 L · **S** · `test/b0.4-fixture-pack`
  `scripts/export_fixtures.py` → `tests/fixtures/real/` per B11 §3 (≤ 20 MB, no PDFs or weights). Done when: merged and the size is reported.

### B1 — Upload and red flags (Tue 6 – Sun 11 Oct) → BG1

- [x] **B1.1a Doc type + validation (fixtures)** · ☁️ C · **S (high effort)** · `feat/b1.1-ingest-any-pdf`
  `ingest.upload` validation, dedupe, doc-type detection, rejection codes; synthetic PDF fixtures (RHP/DRHP/Prospectus/non-offer/scanned) generated in tests.
- [x] **B1.1b Harden on real and unseen PDFs** · 💻 L · **S** · `fix/b1.1b-real-pdfs` · **moved to Phase 3 (C1.3)**
  Run on the 20 showcase PDFs + 5 unseen RHPs (👤 downloads them by Wed 7 Oct); fix what breaks; record timings.
- [x] **B1.2 ★ Jobs, storage, database, events** · ☁️ C · **O** · `feat/b1.2-jobs-pipeline`
  Local/GCS storage, SQLite/Postgres (pooler), jobs + events + replay, simplification priority queue, quotas + kill switch + retention, local worker; tested with fixtures; Postgres in a CI service job.
- [x] **B1.3a ★ Summary + financial extraction (fixtures)** · ☁️ C · **O** · `feat/b1.3-summary-extraction` · **moved to Phase 3 (C3.1)**
  `summary` package developed and tested on the fixture pack (dev IPOs only for tuning).
  - [x] Pipeline groundwork (#166): `parsed`, `sections` and `risks_split` stages in `upload_stages` (parse limited to 10 min), tested end to end on a synthetic RHP.
  - [ ] Left: the `summary` extractors + `financials` stage on the fixture pack, then `redflags` in `upload_stages`.
- [x] **B1.3b Run on full documents + E14** · 💻 L · **S** · `eval/b1.3b-summary-eval` · **moved to Phase 3 (C3.1)**
  Run on all 20 full documents; fix gaps; E14 vs gold v3. 👤+Claude chat: gold v3 pre-fill and verification by Fri 9 Oct.
- [x] **B1.4 Red flags** · ☁️ C · **S** · `feat/b1.4-redflags` · **moved to Phase 3 (C3.2)**
  Rules + `configs/redflags.yaml` + API; tests with gold v3 values (committed) and fixture summaries. 💻 follow-up (short): E15 on the full pipeline output.
  - [x] Cloud half B1.4a (#162): rules engine, `configs/redflags.yaml`, `summary.json` schema, status-gold script, generated reference + how-to; tested on synthetic inputs.
  - [ ] Left: tests with real gold v3 values, wiring after B1.3a, E15 (💻).
- [x] **B1.5 Upload + processing UI + Google sign-in** · ☁️ C · **S** · `feat/b1.5-upload-ui`
  Frontend on mocks (Supabase Auth via env placeholders). 💻 follow-up (short): try with the real local API + Supabase project.
- [x] **BG1 review** (Sun 11) · 💻 L — stop for Akshat. · **moved to Phase 3 (CG1–CG4 gates)**

### B2 — Risk intelligence (Mon 12 – Sun 18 Oct) → BG2

**Pulled forward (Q16):** the ☁️ parts B2.1a, B2.3a, B2.4a and B2.5a start in week 1 (Tue 6 – Thu 8) in parallel cloud sessions; B2.1b and the teacher pilot run Sat 10; see the calendar in `B_EXECUTION_PLAN.md` §2.

- [x] **B2.1a ★ Risk segmentation (fixtures)** · ☁️ C · **O** · `feat/b2.1-risk-segmentation` · **moved to Phase 3 (C2.1)**
  Segmentation for PDF pages (bold/numbered) and corpus text, tested on the fixture pack.
  - [x] Code half (#164): `risks.segment` (PDF + corpus rules), `pipeline/risks_stage.py` (`risks_split` → `risks.json`, addresses withheld), per-stage timeout in the job runner; synthetic bold / numbered / mixed tests.
  - [x] `risks_split` runs in `upload_stages` (#166).
  - [ ] Left: golden tests on real fixture pages of 3 dev IPOs (needs B0.4).
- [x] **B2.1b Risk bank + E13** · 💻 L · **S** · `data/b2.1b-risk-bank` · **moved to Phase 3 (C2.1)**
  Segment the full corpus, embed with bge-m3 (GPU, Ollama stopped, or Kaggle), build `risk_bank.parquet`; E13/E13b; export the teacher input set (5,000 risks) as a private Kaggle dataset. 👤+Claude chat: segmentation spot-check + E13b boundaries.
- [x] **B2.2a Unusualness, hedging, numbers (code)** · ☁️ C · **S** · `feat/b2.2-risk-features`
  Logic + API, tested with a tiny fake bank fixture.
- [x] **B2.2b Run + τ choice + E22** · 💻 L · **S** · `eval/b2.2b-novelty` · **moved to Phase 3 (C2.6)**
  Run against the real bank; τ spot-check (👤+Claude chat); E22.
- [x] **B2.3a ★ Teacher notebook + filters** · ☁️ C · **O** · `feat/b2.3-teacher`
  Prompt, **Kaggle** notebook (vLLM + Qwen ~14B AWQ) with checkpoint/resume, filters, forbidden-phrase filter, quality-100 sheet generator, datasheet, optional `COLAB_STEPS_teacher.md`; smoke test on the fake fixture set.
- [x] **B2.3b Teacher run** · 💻 L (Kaggle CLI) + 👤 A (rating) · **S** · `data/b2.3b-teacher-outputs` · **moved to Phase 3 (C2.3)**
  💻 pilot 500 (Sat 10) → filters → 👤+Claude chat rate quality-100 (go/no-go, Sun 11) → 💻 full 5,000 (Mon 12), drop rates.
- [x] **B2.4a Classifier code + notebooks** · ☁️ C · **S** · `feat/b2.4-risk-classifier`
  TF-IDF+LR baseline, base and large notebooks (Kaggle; Colab optional), ONNX int8 export for the CPU worker; smoke tests on fixtures.
- [x] **B2.4b Train + evaluate** · 💻 L (Kaggle CLI) · **S** · `eval/b2.4b-classifier` · **moved to Phase 3 (C2.4)**
  💻 build train/dev from teacher labels, launch base (3 seeds) and large (1 seed) on Kaggle; 💻 E16 on gold-150 (👤+Claude chat labels), pick by dev.
- [x] **B2.5a ★ Student notebook + checks + serving code** · ☁️ C · **O** · `feat/b2.5-simplifier`
  Kaggle QLoRA notebook (Qwen ~3–4B, T4 fp16), merge + **GGUF Q4 export**, post-checks (verifier, forbidden phrases, length, certainty), priority queue (top 15 automatic, rest on click), llama.cpp serving (vLLM client optional), optional `COLAB_STEPS_student.md`; tests with fixtures.
- [x] **B2.5b Train + evaluate** · 💻 L (Kaggle CLI) + 👤 A (rating) · **S** · `eval/b2.5b-simplifier` · **moved to Phase 3 (C2.5)**
  💻 run QLoRA on Kaggle, export GGUF, run locally on CPU; E18–E20 + CPU seconds per rewrite; 👤 rate gold-50 (blind).
- [x] **B2.6a ★ Seriousness + risk level (code)** · ☁️ C · **O** · `feat/b2.6-risk-level`
  Seriousness rule, **normalised** points, threshold computation (2018–2023 reference), `behind_click` flag, guard update; tests.
- [x] **B2.6b Corpus thresholds + validation** · 💻 L · **S** · `eval/b2.6b-risklevel-validation` · **moved to Phase 3 (C2.8)**
  Compute normalised scores over the 2018–2023 corpus, write `configs/risklevel.yaml` (with `corpus_n`), E17, **E21** with an honest write-up (outcomes read only by `evaluate/outcomes.py`), E8 re-run.
- [x] ~~**B2.7 CPU smoke deploy**~~ · dropped (B-ADR-16, no Google Cloud) · `chore/b2.7-smoke-deploy`
  When GCP billing is enabled and **only with Akshat's "go"**: deploy the Cloud Run API + CPU job with Supabase; one small upload end to end; record cold start and stage timings.
- [x] **BG2 review** (Sun 18) · 💻 L — stop for Akshat. · **moved to Phase 3 (CG2–CG3 gates)**

### B3 — Product and hosting (Mon 19 – Sat 24 Oct) → BG3

- [x] **B3.1 Report UI: Overview + Risks** · ☁️ C · **S** · `feat/b3.1-report-ui`
  On mocks built from fixture `report.json`. 💻 follow-up (short): check against the real local API. *(Built on synthetic mocks overnight; refresh mocks from the fixture pack after B0.4.)*
- [x] **B3.2 Compare** · ☁️ C · **S** · `feat/b3.2-compare` · *(cuttable)*
  Peer table parser, issuer P/E, past-IPO percentiles (provisional), `/compare`, Compare tab on mocks. 💻 follow-up B3.2b: real reference quantiles + check on fixture tables.
- [x] **B3.3a ★ Infra as code (Google Cloud Run)** · removed again by B-ADR-16 (4 Oct) · ☁️ C · **O** · `feat/b3.3-hosting` · *pulled forward to Mon 12 Oct for B2.7*
  Dockerfiles (API without torch; CPU worker with ONNX + llama.cpp; L4 GPU worker with vLLM), manual GitHub Actions workflow → Artifact Registry, Cloud Run service + job definitions, optional HF single-container variant, Supabase wiring, budget and limits config, `scripts/cloud_smoke.py`, runbooks. **No deploy.**
- [x] ~~**B3.3b Deploy**~~ · dropped (B-ADR-16) · `chore/b3.3b-deploy`
  👤 logins, GCP billing and console clicks; 💻 build/push images, upload showcase artefacts + model weights to GCS, deploy, run the smoke test. **Only with Akshat's explicit "go" in chat.**
- [x] **B3.4 Cloud evaluation + Model Lab + site copy** · B3.4a ☁️ C (Model Lab sections, landing/How it works/About copy) + B3.4b 💻 L (E23/E24, E7 on the cloud profile) · **S** · **moved to Phase 3 (C3.6)**
  - [x] B3.4a cloud half (#160, overnight run 1): `GET /api/lab/b/{name}` (B06 §5 mapping, merged classifier/simplify payloads, file shapes documented); seven Lab sections (E13–E24) hidden until their files exist, E21 verdict generated from ρ and its interval; landing (B05 §2: hero, What you get, won't-do lines, two stats), How it works row 3 and About limits (B05 §8).
  - [ ] B3.4b 💻: E23/E24 and E7 on the laptop (`full` profile; no deploy).
- [x] **B3.5 Hardening** · B3.5a ☁️ C (security review, failure-path tests, admin page) + B3.5b 💻 L (full Playwright sweep on the real API) · **S** · **moved to Phase 3 (C3.8)**
  - [x] B3.5a cloud half (#158, overnight run 1): security review (`docs/security_review.md`) with three fixes (chunked upload body capped, stored size checked before download via `Storage.size()`, `uploads.trusted_proxy_hops` for the per-IP limit); failure-path tests over the B02 stage graph; `progress.cost_estimate` per job (`costs.*` settings, provisional rates); `/api/admin/costs` + `/api/admin/jobs` (admin allow-list, 403 `forbidden`); `/admin/costs` page on mocks.
  - [ ] B3.5b 💻: Playwright sweep on the real local API (no deploy; `trusted_proxy_hops` stays 0).
- [x] **BG3 review + FEATURE FREEZE** (Sun 25) · 💻 L. · **moved to Phase 3 (CG6)**

### B4 — Documentation and finish (Sun 25 Oct – Sun 1 Nov)

- [x] **B4.1 Industry-grade documentation** · ☁️ C · **S** — B09 in full (B10 Prompt 6 with the cloud note). 💻 follow-up: test the runbooks once.
  - [x] Cloud half (#153, overnight run 1): MkDocs Material site with full nav; generated pages (`poe docs-gen`: config + env vars, data formats, risk level, compare, ADR index, commands, glossary) and generated blocks in the evaluation page (E1–E24 registry and results), model cards (QA extractor, BiLSTM-CRF, MuRIL guard) and datasheets (corpus, weak labels, gold sets); C4 + sequence diagrams; tutorials, six how-tos, troubleshooting (15), runbooks (rotate secrets, restore DB, monitoring); CHANGELOG, CONTRIBUTING, SECURITY, PRIVACY, CODE_OF_CONDUCT; README for Phase 2; frontend README; docstrings 52 % → 84 %; docs CI hard on freshness, OpenAPI, strict build, 70 % docstrings and Markdown lint.
  - [ ] Left: model cards for the risk classifier and simplifier (they come with B2.4b / B2.5b); GitHub Pages publish (needs Akshat's go); runbooks tested once (💻 follow-up).
- [x] **B4.2 Report drafts update** · ☁️ C · **S** — #156: §4.4 Phase 2 data, §6.7 Phase 2 method, §7.9 generated E13–E24 status table (`poe docs-gen`), §8.2 and §11 notes, Phase 2 disclosures 7–11 in `report/README.md`. The Phase 2 results paragraphs are written after the local runs fill `eval_results/b/`.
- [x] **B4.3 [AKSHAT]** report, slides, video, viva · 👤 A · **moved to Phase 3 (C5.4)**
- [x] **Tag v2.0.0** (Sat 31 Oct) · 💻 L; **submit** Sun 1 Nov. · **moved to Phase 3 (C5.3)**

## 4. Akshat's hand-work calendar

| Date | Task | Time |
|---|---|---|
| Sun 4 – Mon 5 Oct | Setup (`HOSTING_SETUP_STEPS.md`: Supabase, Vercel, Kaggle GPU check) | 30 min |
| by Wed 7 Oct | Download 5 unseen recent RHPs to `data/raw/unseen/` | 20 min |
| by Fri 9 Oct | Verify gold v3 (pre-filled by Claude chat) | 1.5 h |
| Sat 10 Oct | Segmentation spot-check (50) + E13b boundaries (5 corpus excerpts) | 40 min |
| Sun 11 Oct | Rate quality-100 of the teacher pilot (with Claude chat): go/no-go | 30 min |
| Tue 13 Oct | τ spot-check (60 pairs) | 20 min |
| Wed 14 Oct | Category gold-150 verification | 45 min |
| Fri 16 Oct | Rate gold-50 rewrites (blind) | 45 min |
| Mon 19 – Sat 24 Oct | Test uploads; phone check on the local network | 1 h |
| Leftover Phase 1 items | ASR references, Hindi strings, E7 sample (with Claude chat) | 1 h total |
| Sun 25 Oct – Sat 31 Oct | Report, slides, video, viva | most evenings |

## 5. Daily rhythm
- Morning: `git pull`; read `PROGRESS.md` and `docs/AKSHAT_TODO.md` ("needs a LOCAL session" items); do the day's hand-work.
- Day: one local session per part, `/clear` between.
- Night (optional): overnight prompt for Sonnet-only sub-phases that need no hand-work.
