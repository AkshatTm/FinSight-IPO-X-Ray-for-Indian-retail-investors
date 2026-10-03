# B07 — Roadmap (Big Phase 2)

**Today:** Sun 4 Oct 2026 · **Feature freeze:** Sun 25 Oct · **Final tag v2.0.0:** Sat 31 Oct · **Submission:** Sun 1 Nov

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
- **Cloud sessions (☁️, B11):** one cloud part = one new cloud session (a fresh session replaces `/clear`). The cloud session ends by merging its PR, updating "Resume here", and writing the local follow-up (with the exact prompt) to `docs/AKSHAT_TODO.md` → "needs a LOCAL session".
- Hand-work for Akshat goes to `docs/AKSHAT_TODO.md` with a date; Claude Code continues with any unblocked sub-phase.
- Gates: Claude Code runs the gate review (B10 Prompt 5) and stops (except in overnight mode, where it writes `docs/gates/BGx.md` and continues).

## 1. Gates

| Gate | Date | Must be true | If it fails |
|---|---|---|---|
| **BG0** | Mon 5 Oct | Phase 1 IPO-click bug fixed; Phase 2 docs merged; CLAUDE.md updated; GCP project + budget alert + Supabase (Google OAuth) + Colab ready | Slip B1 by a day |
| **BG1** | Sun 11 Oct | Locally: upload an unseen RHP → facts + 13 red flags + progressive events; E14/E15 numbers on gold v3; upload UI with Google sign-in | Ship red flags for showcase only; uploads continue in week 2 |
| **BG2** | Sun 18 Oct | Risk report end-to-end locally (split → features → simplified with checks → risk level with reasons); E13, E16, E18–E22 have real numbers | Use zero-shot base model for rewrites; drop large classifier |
| **BG3** | Sun 25 Oct | **Public URL**: someone else signs in, uploads an RHP, gets a full report; E23/E24; Model Lab updated; **FEATURE FREEZE** | Uploads limited to Akshat; showcase-only public site |

## 2. Cut order (cut from the top if behind)
1. Report "Download summary (PDF)"
2. B3.2 Compare tab
3. M4 large classifier (keep base)
4. Student QLoRA → serve the zero-shot base instruct model with the same prompt and checks
5. Hindi polish for chat/voice
6. Public uploads → uploads only for Akshat's account; showcase public

**Never cut:** upload pipeline, red flags with pages, risk report with originals and number checks, risk level with reasons + disclaimer, E21 validation (reported whatever it shows), honesty rules.

## 3. Sub-phases

**Location marks (B11):** ☁️ **C** = Claude Code cloud session (repo only) · 💻 **L** = local session on the laptop · 👤 **A** = Akshat by hand. Split sub-phases have an **a** (cloud) and **b** (local) half; do them in order. Each ☁️ part = one new cloud session; each 💻 part ends with `/clear`.

### B0 — Setup (Sun 4 – Mon 5 Oct) → BG0

- [ ] **B0.0 Claim the cloud credit + push docs** · 👤 A + 💻 L · —
  👤 Claim the $100 credit (by Wed 7 Oct) and connect GitHub to Claude Code on the web. 💻 Commit and push `docs/phase2/` (a quick local session or plain git).
- [ ] **B0.K Kickoff review** · ☁️ C · **O**
  B10 Prompt C1: STEP 2 review and questions → (my answers via Claude chat) → STEP 3 `B_EXECUTION_PLAN.md`, part of B0.2.
- [ ] **B0.1 Fix the IPO workspace bug** · 💻 L · **S** · `fix/b0.1-workspace-error`
  Reproduce with Playwright against the real API; fix; regression test opening all 10 workspaces. Done when: all 10 open with facts and page images.
- [ ] **B0.2 Phase 2 docs + project rules** · ☁️ C · **S** · `docs/b0.2-phase2-docs`
  As before, plus: CLAUDE.md learns the **environment rule** (detect cloud vs local; in cloud, follow the cloud note and B11) and the hand-off loop; issues for B0–B1 with location labels (`cloud`, `local`, `akshat`).
- [ ] **B0.3 Cloud bootstrap (no deploy)** · ☁️ C · **S** · `chore/b0.3-cloud-bootstrap`
  `CLOUD_SETUP_STEPS.md`, gcloud scripts, `.env.example`, `cloud` profile. 👤 Follow the steps (~45 min).
- [ ] **B0.4 Fixture pack** · 💻 L · **S** · `test/b0.4-fixture-pack`
  `scripts/export_fixtures.py` → `tests/fixtures/real/` per B11 §3 (≤ 20 MB, no PDFs or weights). Done when: merged and the size is reported.

### B1 — Upload and red flags (Tue 6 – Sun 11 Oct) → BG1

- [ ] **B1.1a ★ Doc type + validation (fixtures)** · ☁️ C · **O** · `feat/b1.1-ingest-any-pdf`
  `ingest.upload` validation, dedupe, doc-type detection, rejection codes; synthetic PDF fixtures (RHP/DRHP/Prospectus/non-offer/scanned) generated in tests.
- [ ] **B1.1b Harden on real and unseen PDFs** · 💻 L · **S** · `fix/b1.1b-real-pdfs`
  Run on the 20 showcase PDFs + 5 unseen RHPs (👤 downloads them by Wed 7 Oct); fix what breaks; record timings.
- [ ] **B1.2 ★ Jobs, storage, database, events** · ☁️ C · **O** · `feat/b1.2-jobs-pipeline`
  As before (Local/GCS storage, SQLite/Postgres, jobs + events + replay, local worker), all tested with fixtures.
- [ ] **B1.3a ★ Summary + financial extraction (fixtures)** · ☁️ C · **O** · `feat/b1.3-summary-extraction`
  `summary` package developed and tested on the fixture pack (dev IPOs only for tuning).
- [ ] **B1.3b Run on full documents + E14** · 💻 L · **S** · `eval/b1.3b-summary-eval`
  Run on all 20 full documents; fix gaps; E14 vs gold v3. 👤+Claude chat: gold v3 pre-fill and verification by Fri 9 Oct.
- [ ] **B1.4 Red flags** · ☁️ C · **S** · `feat/b1.4-redflags`
  Rules + `configs/redflags.yaml` + API; tests with gold v3 values (committed) and fixture summaries. 💻 follow-up (short): E15 on the full pipeline output.
- [ ] **B1.5 Upload + processing UI + Google sign-in** · ☁️ C · **S** · `feat/b1.5-upload-ui`
  Frontend on mocks (Supabase Auth via env placeholders). 💻 follow-up (short): try with the real local API + Supabase project.
- [ ] **BG1 review** (Sun 11) · 💻 L — stop for Akshat.

### B2 — Risk intelligence (Mon 12 – Sun 18 Oct) → BG2

- [ ] **B2.1a ★ Risk segmentation (fixtures)** · ☁️ C · **O** · `feat/b2.1-risk-segmentation`
  Segmentation for PDF pages (bold/numbered) and corpus text, tested on the fixture pack.
- [ ] **B2.1b Risk bank + E13** · 💻 L · **S** · `data/b2.1b-risk-bank`
  Segment the full corpus, embed with bge-m3 (GPU, Ollama stopped, or Kaggle), build `risk_bank.parquet`; E13/E13b; export the teacher input set (5,000 risks) to Google Drive. 👤+Claude chat: segmentation spot-check.
- [ ] **B2.2a Unusualness, hedging, numbers (code)** · ☁️ C · **S** · `feat/b2.2-risk-features`
  Logic + API, tested with a tiny fake bank fixture.
- [ ] **B2.2b Run + τ choice + E22** · 💻 L · **S** · `eval/b2.2b-novelty`
  Run against the real bank; τ spot-check (👤+Claude chat); E22.
- [ ] **B2.3a ★ Teacher notebook + filters** · ☁️ C · **O** · `feat/b2.3-teacher`
  Prompt, notebook with checkpoint/resume, filters, quality-100 sheet generator, datasheet, `COLAB_STEPS_teacher.md`; smoke test on the fake fixture set.
- [ ] **B2.3b Teacher run** · 👤 A (Colab A100) + 💻 L · **S** · `data/b2.3b-teacher-outputs`
  👤 run the notebook; 💻 download, filter, report drop rates; 👤+Claude chat rate quality-100 (go/no-go).
- [ ] **B2.4a Classifier code + notebooks** · ☁️ C · **S** · `feat/b2.4-risk-classifier`
  TF-IDF+LR baseline, base notebook (Kaggle), large notebook (Colab) + `COLAB_STEPS_classifier_large.md`; smoke tests on fixtures.
- [ ] **B2.4b Train + evaluate** · 💻 L (Kaggle CLI) + 👤 A (Colab) · **S** · `eval/b2.4b-classifier`
  💻 build train/dev from teacher labels, launch base on Kaggle (3 seeds); 👤 run large on Colab; 💻 E16 on gold-150 (👤+Claude chat labels), pick by dev.
- [ ] **B2.5a ★ Student notebook + checks + serving code** · ☁️ C · **O** · `feat/b2.5-simplifier`
  QLoRA notebook, merge/export, post-checks (verifier, forbidden words, length, certainty), priority queue, Ollama/vLLM client code, `COLAB_STEPS_student.md`; tests with fixtures.
- [ ] **B2.5b Train + evaluate** · 👤 A (Colab) + 💻 L · **S** · `eval/b2.5b-simplifier`
  👤 run QLoRA on Colab; 💻 load locally (if it fits) or keep for cloud; E18–E20; 👤 rate gold-50 (blind).
- [ ] **B2.6a ★ Seriousness + risk level (code)** · ☁️ C · **O** · `feat/b2.6-risk-level`
  Seriousness rule, points system, threshold computation from `corpus_stats.json`, guard update; tests.
- [ ] **B2.6b Corpus thresholds + validation** · 💻 L · **S** · `eval/b2.6b-risklevel-validation`
  Compute points over the corpus, write `configs/risklevel.yaml`, E17 and **E21** with an honest write-up.
- [ ] **BG2 review** (Sun 18) · 💻 L — stop for Akshat.

### B3 — Product and cloud (Mon 19 – Sat 24 Oct) → BG3

- [ ] **B3.1 Report UI: Overview + Risks** · ☁️ C · **S** · `feat/b3.1-report-ui`
  On mocks built from fixture `report.json`. 💻 follow-up (short): check against the real local API.
- [ ] **B3.2 Compare** · ☁️ C · **S** · `feat/b3.2-compare` · *(cuttable)*
- [ ] **B3.3a ★ Infra as code** · ☁️ C · **O** · `feat/b3.3-cloud`
  Dockerfiles (API without torch, worker, vLLM), GitHub Actions → Artifact Registry → Cloud Run, Supabase/GCS wiring, budget and limits config, `scripts/cloud_smoke.py`, `DEPLOY_RUNBOOK.md`. **No deploy.**
- [ ] **B3.3b Deploy** · 💻 L + 👤 A · **O** · `chore/b3.3b-deploy`
  👤 logins and console clicks; 💻 build/push images, upload showcase artefacts + weights to GCS, deploy, run the smoke test. **Only with Akshat's explicit "go" in chat.**
- [ ] **B3.4 Cloud evaluation + Model Lab + site copy** · 💻 L (E23/E24) + ☁️ C (Model Lab sections, landing/How it works/About copy) · **S**
- [ ] **B3.5 Hardening** · ☁️ C (security review, failure-path tests, admin page) + 💻 L (full Playwright sweep on the real API) · **S**
- [ ] **BG3 review + FEATURE FREEZE** (Sun 25) · 💻 L.

### B4 — Documentation and finish (Sun 25 Oct – Sun 1 Nov)

- [ ] **B4.1 Industry-grade documentation** · ☁️ C · **S** — B09 in full (B10 Prompt 6 with the cloud note). 💻 follow-up: test the runbooks once.
- [ ] **B4.2 Report drafts update** · ☁️ C · **S**
- [ ] **B4.3 [AKSHAT]** report, slides, video, viva · 👤 A
- [ ] **Tag v2.0.0** (Sat 31 Oct) · 💻 L; **submit** Sun 1 Nov.

## 4. Akshat's hand-work calendar

| Date | Task | Time |
|---|---|---|
| Sun 4 – Wed 7 Oct | **Claim the $100 cloud credit (deadline 7 Oct)**, connect GitHub to Claude Code on the web | 5 min |
| Sun 4 – Mon 5 Oct | Cloud + Supabase + Colab setup (CLOUD_SETUP_STEPS.md) | 45 min |
| by Wed 7 Oct | Download 5 unseen recent RHPs to `data/raw/unseen/` | 20 min |
| by Fri 9 Oct | Verify gold v3 (pre-filled by Claude chat) | 1.5 h |
| Mon 12 – Tue 13 Oct | Segmentation spot-check (50) | 20 min |
| Tue 13 – Wed 14 Oct | Run teacher notebook on Colab; rate quality-100 (with Claude chat) | 30 min + waiting |
| Wed 14 – Thu 15 Oct | Category gold-150 verification; run large classifier on Colab | 45 min + waiting |
| Thu 15 – Sat 17 Oct | Run student QLoRA on Colab; rate gold-50 rewrites (blind) | 45 min + waiting |
| Mon 19 – Sat 24 Oct | Deploy steps needing your login; test uploads; phone check | 1–2 h |
| Leftover Phase 1 items | ASR references, Hindi strings, E7 sample (with Claude chat) | 1 h total |
| Sun 25 Oct – Sat 31 Oct | Report, slides, video, viva | most evenings |

## 5. Daily rhythm
- Morning: `git pull`; read `PROGRESS.md` and `docs/AKSHAT_TODO.md` ("needs a LOCAL session" items); do the day's hand-work.
- Day: start ☁️ cloud sessions for the next cloud parts (they run while you do other things); run short 💻 local sessions for the local halves, `/clear` between.
- Check the cloud credit balance after each cloud session (B11 §5).
- Night (optional): overnight prompt for Sonnet-only sub-phases that need no hand-work.
