# B_EXECUTION_PLAN — how each Phase 2 part gets built

**Scope:** for every sub-phase/part in `B07_ROADMAP.md`: location, issue, branch, model, files, tests that prove it is done, planned commits, dependencies and Akshat's hand-work. `B07` wins on dates, gates and the cut order; `B11` on where work runs; `B06` on payloads; `B02` on module boundaries.
**Status:** proposed in PR `docs/b0.2-phase2-docs` (B0.K kickoff review + B0.2). Written Sat 3 Oct 2026, after Akshat's answers to the STEP 2 review.

---

## 0. Ground rules

- **Where:** ☁️ C = cloud session (repo only) · 💻 L = local session on the laptop · 👤 A = Akshat by hand. One ☁️ part = one new cloud session (prompt C0 + C2). One 💻 part = one local session ending with `/clear` (prompt L1).
- **Model:** O = Opus, S = Sonnet. Model check in both directions before every part (B07 §0). B1.1a runs on Sonnet at high effort (Akshat, Q23).
- **Loop per part:** issue → branch from fresh `main` → tests first → small green commits (Conventional Commits, `Refs #n`) → `uv run poe lint && uv run poe typecheck && uv run poe test` → docs updated in the same PR (B09) → PR (closes the issue; plan in the description when > 50 lines) → CI green → rebase-merge → `PROGRESS.md` "Resume here" + B07 ticks → local follow-up in `docs/AKSHAT_TODO.md` → "needs a LOCAL session" with its exact L1 prompt.
- **GitHub in cloud sessions:** no `gh` CLI; use the GitHub MCP tools (create issue / PR, merge with `merge_method: rebase`). Local sessions keep `gh`.
- **Tests:** `@pytest.mark.local` = needs `data/processed`, full PDFs, the corpus or model weights. `poe test` (and CI) runs `-m "not slow and not local"`. `poe test-all` runs everything.
- **No spend, no deploy** without Akshat's explicit "go" in chat. No credentials in any cloud session or commit.
- **Hosting is cloud-agnostic and CPU-first** (B-ADR-04, revised): Supabase (Auth, Postgres via the pooler, Storage) + Vercel + one CPU host chosen in B0.3 (Azure Container Apps for Students, or a Hugging Face Docker Space on PRO). GCP Cloud Run L4 + vLLM stays designed but optional (profile `cloud_gpu`).
- **Training is Kaggle-first** (Q12 was left open; this plan works either way). Teacher (Qwen ~14B AWQ, vLLM), classifiers and student QLoRA all run on Kaggle T4 / T4×2, launched by local sessions through the Kaggle CLI (ADR-042). If Akshat buys Colab Pro, B2.3b and B2.5b may switch to Colab (teacher up to ~32B AWQ; `COLAB_STEPS_*.md` written as the optional path). Nothing else in this plan changes.

## 1. Fixes approved in STEP 2 (all of 1–45, with the hosting change) and where each lands

| # | Decision | Lands in |
|---|---|---|
| H | **Hosting:** CPU-first and cloud-agnostic. Default host = Azure Container Apps (Azure for Students, Consumption plan, scale to zero; API app + worker *job*). Alternative = HF Docker Space (needs HF PRO, $9/month, since free accounts can no longer create Docker/Gradio CPU Spaces). Supabase for Auth + Postgres + Storage; Vercel for the site. GPU path optional | B-ADR-04 (revised), B02 §10–12, B01 §7, B11, B0.3, B3.3a/b |
| H2 | **CPU speed plan:** auto-simplify only the top 15 risks by importance; the rest on click (priority queue). Targets on CPU: facts ≤ 3 min, red flags + level ≤ 5 min, rewrites progressive (≈ 15 s each, measured in E23) | B01 §7, B02 §3.1/§8, B1.2, B2.5a |
| H3 | **Upload limit 50 MB** while Storage is on the Supabase Free plan (its per-file limit is 50 MB); config key `uploads.max_mb` | B01 B-FR-01, B05 §3 copy, B06 §2, B1.1a |
| 1 | Risk level uses a **normalised score** (points ÷ max points over the checks available) and a **2018–2023 reference population**; UI shows `corpus_n` from config, never a hard-coded 389 | B02 §7.4, B04 E21, B05 §2/§5.3/§6.3/§8, B2.6a/b |
| 2 | Fixture pack: B0.4 adds section patterns (restated financial information, cash flows, outstanding litigation, auditor's report), exports pre-extracted tables, cash-flow / auditor / litigation pages; gzip JSON ≤ 5 MB per file, ~10 MB total; README maps each RF to its source pages | B11 §3, B0.4 |
| 3 | B2 ☁️ parts (B2.1a, B2.3a, B2.4a, B2.5a) pulled into week 1; teacher pilot (500) by Sun 11 Oct | B07 §3, §5 below |
| 4 | Week-2 **CPU smoke deploy** on the chosen free host (only with Akshat's "go") instead of a vLLM-on-L4 smoke | new part B2.7, B07 |
| 5 | **CPU worker job** for every stage; simplification on CPU with the student as GGUF Q4 via llama.cpp; optional GPU job (vLLM offline + bge-m3) for simplify + index | B02 §10, B1.2, B2.5a, B3.3a |
| 6 | Region: Supabase Mumbai (`ap-south-1`) if offered, else Singapore; Azure Central India if Container Apps + Students policy allow it, else Southeast Asia | B0.3 |
| 7 | GPU path only: vLLM AWQ from a mounted bucket; cold start measured, not assumed | B02 §10 (optional path) |
| 8 | API image has no torch: chat retrieval on the deployed CPU host is BM25 (+ optional ONNX int8 bge-m3 query encoder if measured fast enough); API memory ≥ 4 GiB | B02 §10, B3.3a |
| 9 | Caps: 10 uploads/day global, 3/user/day, `UPLOADS_ENABLED` kill switch, budget alerts where the host supports them (Azure budgets: yes) | B01 §4/§7, B02 §12, B1.2, B1.5 |
| 10 | Supabase: pooler (6543, transaction mode, no prepared statements), SSE replay by polling `job_events` (~1 s), JWKS + HS256 fallback with `aud`/`iss` checks, Vercel preview redirect URLs, OAuth consent screen published; 7-day pause noted in runbooks | B02 §9/§11, B1.2, B1.5, B0.3 |
| 11 | Signed upload URLs come from Supabase Storage (`createSignedUploadUrl`) or S3 presign; bucket CORS documented | B02 §9, B1.2, B0.3 |
| 12 | `complete` recomputes SHA-256 server-side; mismatch → 422 `hash_mismatch` | B06 §2, B1.2 |
| 13 | Retention: delete everything for non-showcase docs after 30 days (source, pages, report, rows except `uploads` counts); a later dedupe hit re-processes | B01 §7, B02 §9, B1.2 |
| 14 | Summary extraction anchors on ICDR Summary items; `not_found` over guessing; E14 NVM on test IPOs; unseen RHPs → coverage only | B02 §6a (new), B04 E14, B1.3a/b |
| 15 | RHP `[●]` prices: parse a price-band addendum if present; showcase reports read prices from the companion Prospectus; no price input box (Q19) | B02 §3.2, B1.3a, B1.4 |
| 16 | RF05 WACA = share-weighted average over selling shareholders' offered shares (per-shareholder table), else NA | B01 §5, `configs/redflags.yaml`, B1.4 |
| 17 | `is_financial_company` = keyword rules (RBI / NBFC / IRDAI registration, "banking company") + corpus Excel sector for the corpus | B1.3a |
| 18 | Segmentation rule: line-start bold run at the left margin, ≥ 5 words, followed by non-bold text; numbering raises confidence; words inside table bboxes ignored; only inside Risk Factors after its preamble; golden tests on real fixture pages | B02 §6, B2.1a |
| 19 | E13b gold: boundaries for 5 of the 20 corpus excerpts (👤 + Claude chat, ~20 min) | B04 §2, B2.1b |
| 20 | Novelty reference = 2018–2023 bank; disclosed in Lab and About | B02 §7.1, B05 §8, B2.2a/b |
| 21 | Teacher via vLLM + AWQ only; output JSONL checkpointed every 100 items; 500-item pilot first | B03 §2–3, B2.3a/b |
| 22 | Qwen family (Apache-2.0): teacher best Qwen that fits AWQ (~14B on Kaggle; ~32B if Colab); student ~3–4B QLoRA served as GGUF Q4 on CPU; optional ~8B variant only if a GPU host appears | B03 §1/§5, B-ADR-07, B2.3a, B2.5a |
| 23 | `label_source` + "values changed by Akshat" count on every AI-assisted gold set; disclosed in Lab and report | B04 §2, all gold parts |
| 24 | **Forbidden phrases**, not words: `configs/forbidden_phrases.yaml` (instruction-style patterns + allow-list for disclaimers), one tested filter for UI copy and rewrites | B01 §6, B05 §9, B2.5a, B3.1 |
| 25 | Guard: allow risk-level questions; E8 re-run on both sets in B2.6b | B02 §4, B04 (E8r), B2.6a/b |
| 26 | Cloud chat = CPU qwen3.5:2b Q4 (llama.cpp) + demo cache for showcase (Q4 = c); E7 re-run on the `cloud` profile in B3.4 | B03 M7, B3.4 |
| 27 | 13 checks everywhere (not "~12") | B01 §1/§4 |
| 28 | `POST …/simplify`: auth optional, rate-limited per IP | B06 §1 |
| 29 | B06 events win; B02 §3.1 column renamed "detail"; stage → event map written in B06 | B02 §3.1, B06 §2 |
| 30 | Core: `DocType` gains `drhp`; `doc_id` beside `ipo_id` (showcase mapping in `configs/demo_ipos.yaml`); `Amount := Money | Count | Percent`; `Evidence` new | B02 §5, B1.1a, B1.2 |
| 31 | Showcase report primary doc = RHP, `companion_doc_id` = Prospectus (prices); `/ipos/[id]` redirects; demo hotkeys and `e2e/demo-flow.spec.ts` updated | B02 §3.2, B05 §1, B1.2, B3.1 |
| 32 | `/api/lab/b/*` → file mapping table | B06 §5 |
| 33 | Missing RF sentence templates: default NA = "FinSight couldn't find this in the document."; gaps listed for Akshat's copy approval | B05 §5.4, AKSHAT_TODO |
| 34 | Profiles: `dev_light`, `full`, **`cloud`** (CPU host), **`cloud_gpu`** (optional); `deploy_cpu` kept as the showcase-only fallback (ADR-022) | B02 §1/§10, configs/config.yaml (B0.3) |
| 35 | `evaluate/outcomes.py`: allow-listed outcome loader used only by E21; a test asserts no other module imports it | B-ADR-03, B2.6b |
| 36 | B07 date fixed (today Sat 3 Oct); B0.2 done in the Opus kickoff session | B07 |
| 37 | `local` pytest marker registered; `poe test` excludes it | pyproject (this PR) |
| 38 | CLAUDE.md exception for `tests/fixtures/real/` | CLAUDE.md (this PR) |
| 39 | CLAUDE.md: GitHub MCP tools in cloud sessions | CLAUDE.md (this PR) |
| 40 | Postgres tests via a GitHub Actions `services: postgres` job (`@pytest.mark.postgres`), not in the cloud VM | B1.2 |
| 41 | Phase 1 PROGRESS lines archived in `docs/PROGRESS_PHASE1.md`; "Resume here" block on top | this PR |
| 42 | B0.1: reproduce on the real API; regression test only if nothing fails (Q2) | B0.1 |
| 43 | Docs CI lints only the MkDocs sources; `interrogate` warn-only until B4.1 | B09 §9, B4.1 |
| 44 | B1.1a → Sonnet (high effort); check the cloud credit after every session | B07, B11 §5 |
| 45 | Phase 1 leftovers (ADR-022/053/054 reviews, E7 hand-check, Hindi strings) listed in AKSHAT_TODO as "after BG1" | AKSHAT_TODO (this PR) |

## 1a. Issues created in B0.2

| Part | Issue | Label | Part | Issue | Label |
|---|---|---|---|---|---|
| B0.2 | #120 | cloud | B1.2 | #127 | cloud |
| B0.1 | #121 | local | B1.3a | #128 | cloud |
| B0.3 | #122 | cloud | B1.3b | #129 | local |
| B0.4 | #123 | local | B1.4 | #130 | cloud |
| hand-work B0/B1 | #124 | akshat | B1.5 | #131 | cloud |
| B1.1a | #125 | cloud | B2.1a | #132 | cloud |
| B1.1b | #126 | local | B2.3a | #133 | cloud |
| B2.4a | #134 | cloud | B2.5a | #135 | cloud |

Later issues (B2 local halves, B2.2a, B2.6a, B3, B4) are opened by the session that starts them.

## 2. Calendar at a glance (2026)

| Day | ☁️ cloud (parallel sessions) | 💻 local | 👤 Akshat |
|---|---|---|---|
| Sat 3 Oct | B0.K + B0.2 (this PR) | — | answer review ✔, approve PR |
| Sun 4 | B0.3 hosting bootstrap | B0.1 workspace bug; B0.4 fixture pack | claim cloud credit; accounts (Azure for Students, Supabase, Vercel, Kaggle check) |
| Mon 5 **BG0** | B1.1a doc type + validation | BG0 review | follow `docs/phase2/HOSTING_SETUP_STEPS.md` (~45 min); pick Azure vs HF |
| Tue 6 | B1.2 jobs/storage/db; B2.3a teacher notebook | B1.1b (after B1.1a) | download 5 unseen RHPs (by Wed 7) |
| Wed 7 | B1.3a summary extraction; B2.1a segmentation | — | credit claim deadline 23:59 PT |
| Thu 8 | B1.5 upload UI; B2.4a classifier code; B2.5a student code | — | gold v3 pre-fill with Claude chat |
| Fri 9 | B1.4 red flags (after gold v3) | B1.3b + E14 | **verify gold v3** (1.5 h) |
| Sat 10 | — | B1.4 follow-up (E15); B2.1b risk bank + teacher input export; B2.3b **pilot (500)** on Kaggle | segmentation spot-check (50) + E13b (5 excerpts) |
| Sun 11 **BG1** | B2.2a features | BG1 review | rate pilot quality-100 (go/no-go) |
| Mon 12 | B3.3a infra as code (CPU host) | B2.3b full teacher run (Kaggle) | — |
| Tue 13 | B2.6a seriousness + risk level | B2.2b τ + E22 | τ spot-check (60 pairs) |
| Wed 14 | B3.1 report UI (on mocks) | B2.4b classifiers (Kaggle) ; **B2.7 CPU smoke deploy** (after "go") | category gold-150 verification; smoke-deploy console steps |
| Thu 15 | B3.2 compare (cuttable) | B2.5b student QLoRA (Kaggle) + GGUF | — |
| Fri 16 | B3.5a hardening (cloud half) | B2.5b eval E19/E20 | rate gold-50 rewrites (blind) |
| Sat 17 | — | B2.6b thresholds + E17/E21 + E8 re-run | — |
| Sun 18 **BG2** | — | BG2 review | — |
| Mon 19 – Thu 22 | B3.4a Model Lab + site copy | B3.3b deploy (after "go"); B3.4b E23/E24 + E7 cloud | logins, test uploads, phone check |
| Fri 23 – Sat 24 | — | B3.5b Playwright sweep on the real API | — |
| Sun 25 **BG3 + freeze** | — | BG3 review | — |
| Mon 26 – Thu 29 | B4.1 docs; B4.2 report drafts | B4.1 follow-up: runbooks tested | report, slides, video |
| Sat 31 | — | tag v2.0.0 | — |
| Sun 1 Nov | — | — | submit |

## 3. Parts

Each part: **Where · Model · Branch · Issue title** — then Depends / Files / Tests (done when) / Commits / Hand-work.

### B0 — Setup → BG0 (Mon 5 Oct)

#### B0.K Kickoff review — ☁️ · O · (no branch) — done
STEP 2 review in chat (Sat 3 Oct); Akshat's answers recorded in §1.

#### B0.1 Fix the IPO workspace bug — 💻 · S · `fix/b0.1-workspace-error` · "B0.1 Fix the IPO workspace error on the real API"
- **Depends:** none. Bug details unknown (Q2 default): reproduce first.
- **Files:** `frontend/e2e/workspace-all.spec.ts` (new), the failing component or route, `tests/api/test_real_api.py` (+ a case per IPO, `@pytest.mark.local`).
- **Tests:** Playwright opens all 10 `/ipos/[id]` workspaces on the real API with facts + page image visible; if nothing fails, the PR is the regression test only (note in PROGRESS).
- **Commits:** `test(e2e): open all 10 workspaces on the real API` · `fix(<pkg>): <root cause>` · `docs: progress for B0.1`.
- **Hand-work:** none (Akshat describes the bug in the L1 prompt if he can).

#### B0.2 Phase 2 docs + project rules — ☁️ · O (kickoff session) · `docs/b0.2-phase2-docs` · "B0.2 Phase 2 docs, execution plan, CLAUDE.md and B-ADRs"
- **Files:** this plan; B01/B02/B03/B04/B05/B06/B07/B08/B11 fixes; pointers in `docs/02`, `05`, `06`, `07`, `09`, `12`, `EXECUTION_PLAN.md`, `00_README.md`; B-ADR-01..15 (proposed) in `docs/09_DECISIONS.md`; `CLAUDE.md`; `PROGRESS.md` + `docs/PROGRESS_PHASE1.md`; `pyproject.toml` (`local` marker); `data/gold/gold_v3_template.jsonl` (Q21); `docs/AKSHAT_TODO.md`; issues for B0–B1 + pulled-forward B2 ☁️ parts.
- **Tests:** `poe test` green (1124 before), `poe lint` green; marker test (`pytest --strict-markers -m local --collect-only` works).
- **Commits:** `docs(phase2): execution plan with approved review fixes` · `docs(phase2): apply review fixes to B01–B11` · `docs: B-ADRs 01–15 proposed, ADR-022 and ADR-005 notes` · `docs: Phase 1 pointers to Phase 2 docs` · `docs: CLAUDE.md Phase 2 rules` · `chore(test): register local marker` · `data(gold): gold v3 template` · `docs: progress archive and Resume here`.

#### B0.3 Hosting bootstrap (no deploy) — ☁️ · S · `chore/b0.3-hosting-bootstrap` · "B0.3 Hosting bootstrap: Azure for Students + Supabase + Vercel steps, cloud profile"
- **Depends:** B0.2.
- **Files:** `docs/phase2/HOSTING_SETUP_STEPS.md` (Azure for Students sign-up with no card, resource group, Container Apps environment, budget alert; Supabase project in Mumbai/Singapore, Google provider, Storage bucket `docs`, pooler URL; Vercel env; Kaggle check), `docs/phase2/HOSTING_COMPARISON.md` (Azure Container Apps vs HF Docker Space: CPU/RAM per replica, free grant 180k vCPU-s + 360k GiB-s per month, sleep behaviour, cold start, jobs support, cost, region; Akshat picks), `.env.example`, `configs/config.yaml` (`cloud`, `cloud_gpu` profiles; `uploads.*` limits; `UPLOADS_ENABLED`), `src/finsight/core/config.py` (new keys with defaults), `tests/core/test_config_profiles.py`, `scripts/check_env.py` (prints which settings are missing, never their values).
- **Tests:** every profile loads; `cloud` resolves storage `s3`, db `postgres`, llm `llama-cpp`; `.env.example` lists every env key the settings read (test parses both).
- **Commits:** `docs(phase2): hosting setup steps and Azure vs HF comparison` · `feat(core): cloud and cloud_gpu profiles with upload limits` · `chore: .env.example and check_env script`.
- **Hand-work:** 👤 follow the steps (~45 min, Mon 5 Oct); pick the host and write the choice in the issue.

#### B0.4 Fixture pack — 💻 · S · `test/b0.4-fixture-pack` · "B0.4 Real-section fixture pack for cloud sessions"
- **Depends:** B0.2 (CLAUDE.md exception).
- **Files:** `src/finsight/parse/sections.py` (+ `restated_financial_information`, `cash_flows`, `outstanding_litigation`, `auditors_report`, `financial_indebtedness` patterns), `tests/parse/test_sections.py`, `scripts/export_fixtures.py`, `tests/fixtures/real/README.md`, `tests/fixtures/real/<ipo_id>/<doc>.pages.json.gz` (Summary of the Offer Document, Risk Factors, Capital Structure, Objects, Basis for Offer Price, summary financials, cash-flow statement pages, auditor qualifications, litigation summary; words + bbox + bold/size; pre-extracted `Table`s), `tests/fixtures/real/corpus_risk_factors/*.txt.gz` (20, stratified by year), `samples/{parsed,xray,report}_*.json.gz` (2 IPOs), `fake_training/risks_20.jsonl`, `corpus_stats.json` copy, `tests/fixtures/real/loader.py` + `tests/test_fixture_pack.py` (shape, size ≤ 5 MB per file, ≤ 20 MB total, no PDFs).
- **Tests:** pack loads; every RF in the README maps to ≥ 1 exported page for ≥ 8/10 IPOs (report the gaps); size printed.
- **Commits:** `feat(parse): section patterns for financial statements, litigation and auditor report` · `feat(scripts): export_fixtures for the cloud fixture pack` · `test(fixtures): real-section pack for 10 IPOs and 20 corpus excerpts` · `docs: fixture pack README and size`.
- **Hand-work:** none.

### B1 — Upload and red flags → BG1 (Sun 11 Oct)

#### B1.1a Doc type + validation (fixtures) — ☁️ · **S (high effort)** · `feat/b1.1-ingest-any-pdf` · "B1.1a Upload validation, dedupe and document-type detection"
- **Depends:** B0.2. (Fixture pack not needed: synthetic PDFs.)
- **Files:** `src/finsight/ingest/upload.py` (`validate_pdf()` → size / pages / password / scanned via text density / not-offer-document; `detect_type()` → rhp / drhp / prospectus / unknown from the first 3 pages; `sha256_file()`), `src/finsight/ingest/__init__.py`, `src/finsight/core/schemas.py` (`DocType` + `drhp`; `DocRecord`, `Evidence`, `Amount` alias), `src/finsight/core/ids.py` (`make_doc_id`), `configs/config.yaml` (`uploads.max_mb: 50`, `max_pages: 1500`), `tests/fixtures/make_fixture_pdf.py` (RHP / DRHP / Prospectus / non-offer / scanned / password builders), `tests/ingest/test_upload.py`.
- **Tests:** table-driven: each synthetic PDF → expected type or rejection code; the 50 MB and 1,500-page edges; same bytes → same `doc_id`; `passage_id` still rejects unknown types.
- **Commits:** `feat(core): doc_id, drhp doc type and upload records` · `test(ingest): synthetic offer-document PDFs` · `feat(ingest): validate uploads and reject with friendly codes` · `feat(ingest): detect RHP, DRHP and Prospectus from the cover`.
- **Local follow-up:** B1.1b.

#### B1.1b Harden on real and unseen PDFs — 💻 · S · `fix/b1.1b-real-pdfs` · "B1.1b Validation and detection on 20 showcase + 5 unseen PDFs"
- **Depends:** B1.1a; 👤 5 unseen RHPs in `data/raw/unseen/` (by Wed 7 Oct).
- **Files:** fixes in `ingest/upload.py`, `parse/*`; `eval_results/b/ingest_unseen.json` (type, pages, parse s, sections found).
- **Tests:** `@pytest.mark.local` test runs detection on all 25 files: 25/25 correct type; ≥ 4 key sections found in each.
- **Commits:** `fix(ingest): <cases found>` · `eval(ingest): detection and timing on unseen RHPs`.

#### B1.2 ★ Jobs, storage, database, events — ☁️ · O · `feat/b1.2-jobs-pipeline` · "B1.2 Jobs, storage, database and stage events"
- **Depends:** B1.1a (schemas).
- **Files:** `src/finsight/storage/` (`Storage` protocol, `LocalStorage`, `S3Storage` for Supabase Storage / any S3 endpoint, `signed_upload_url()`), `src/finsight/db/` (SQLAlchemy 2 Core tables `users, docs, jobs, job_events, uploads, traces, demo_cache`; Alembic migrations; SQLite local, Postgres cloud via pooler with prepared statements off), `src/finsight/jobs/` (stage runner with idempotent stages, events with `seq`, priority queue table for simplification, retries, `UPLOADS_ENABLED`, quotas, retention sweep), `src/finsight/reports/` (assemble `report.json` from stage outputs), `src/finsight/api/routes_uploads.py` + `routes_docs.py` (B06 §2–3 skeletons; `complete` recomputes SHA-256), `api/events.py` (SSE with `Last-Event-ID` replay by polling), `configs/demo_ipos.yaml` (+ `doc_id`, `companion_doc_id`), `openapi.json`, `frontend/lib/api/types.ts`, `.github/workflows/backend.yml` (+ `postgres` service job running `-m postgres`), `pyproject.toml` (`sqlalchemy`, `alembic`, `psycopg[binary]`, `boto3` or `httpx` in `api`), tests in `tests/{storage,db,jobs,reports}/`.
- **Tests:** stage runner on a fake 3-stage pipeline (success, one stage failing → `partial`, earlier outputs kept); event replay from any `seq`; dedupe returns `exists`; hash mismatch → 422; quota 3/user and 10/global with the kill switch; priority bump reorders the queue; retention deletes only non-showcase; contract tests for every B06 §2 endpoint on the local profile; Postgres job green in CI.
- **Commits:** `feat(storage): local and S3 storage behind one protocol` · `feat(db): repositories and migrations for SQLite and Postgres` · `feat(jobs): stage runner, events and priority queue` · `feat(jobs): quotas, kill switch and retention` · `feat(api): upload, doc and event endpoints` · `feat(reports): assemble report.json` · `ci: Postgres service job` · `chore(api): regenerate openapi and frontend types`.
- **Local follow-up:** run one showcase doc end to end with the local worker (5 min).

#### B1.3a ★ Summary + financial extraction (fixtures) — ☁️ · O · `feat/b1.3-summary-extraction` · "B1.3a Summary and financial extraction for red-flag inputs"
- **Depends:** B0.4, B1.1a.
- **Files:** `src/finsight/summary/` (`extract_summary(doc) -> FinancialSummary`; one module per input: `financials.py` (revenue, PAT, net worth, borrowings from the ICDR summary table; OCF from the cash-flow statement), `waca.py`, `litigation.py`, `rpt.py`, `shareholding.py` (promoter post-issue, pledged), `customers.py` (regex over Risk Factors), `peers.py`, `auditor.py`, `sector.py` (`is_financial_company`), `price.py` (price band addendum, companion prospectus)), `configs/summary.yaml` (anchors and patterns), `tests/summary/` on the fixture pack (dev IPOs for tuning; test IPOs only in `@pytest.mark.local` E14).
- **Tests:** each extractor on ≥ 2 dev fixtures with expected values; `[●]` → `placeholder`; missing section → `not_found`; units preserved; fuzz test that no extractor raises on any fixture page.
- **Commits:** `feat(summary): financial summary schema and table anchors` · `feat(summary): restated financials and cash flow` · `feat(summary): WACA, shareholding and pledges` · `feat(summary): litigation, related parties and auditor remarks` · `feat(summary): customers, peers and sector` · `feat(pipeline): financials stage`.
- **Local follow-up:** B1.3b.

#### B1.3b Run on full documents + E14 — 💻 · S · `eval/b1.3b-summary-eval` · "B1.3b Summary extraction on 20 documents + E14"
- **Depends:** B1.3a; 👤 gold v3 verified (Fri 9 Oct).
- **Files:** fixes in `summary/`; `src/finsight/evaluate/summary_eval.py`; `eval_results/b/summary_extraction.json` (NVM + coverage on test IPOs; coverage on 5 unseen).
- **Tests:** `@pytest.mark.local` run; eval file schema test (cloud-safe).
- **Commits:** `fix(summary): <gaps on full documents>` · `eval(summary): E14 on gold v3`.

#### B1.4 Red flags — ☁️ · S · `feat/b1.4-redflags` · "B1.4 Red-flag rules, config and API"
- **Depends:** B1.3a; gold v3 committed (Fri 9).
- **Files:** `src/finsight/redflags/` (`evaluate(summary, xray) -> list[RedFlag]`, sentence templates from B05 §5.4, NA default), `configs/redflags.yaml` (13 checks, thresholds, explanations, `version`), `api/routes_docs.py` (`/redflags`), `scripts/redflag_status_gold.py` (computes status gold from gold v3), `data/gold/redflag_status_gold.jsonl`, `tests/redflags/` (table-driven edge tests for every threshold; financial-company RF03; DRHP NA).
- **Tests:** every threshold edge; 13 flags always returned; no forbidden phrase in any sentence (uses fix 24 filter once B2.5a lands; until then a local list).
- **Commits:** `feat(redflags): rules engine and config` · `feat(redflags): sentences and evidence` · `data(gold): red-flag status gold from gold v3` · `feat(api): red flags endpoint`.
- **Local follow-up:** E15 on the full pipeline output (`eval_results/b/redflags.json`).

#### B1.5 Upload + processing UI + Google sign-in — ☁️ · S · `feat/b1.5-upload-ui` · "B1.5 Upload page, processing screen and Google sign-in"
- **Depends:** B1.2 (openapi types).
- **Files:** `frontend/app/upload/page.tsx`, `frontend/app/reports/[doc_id]/page.tsx` (processing state), `frontend/app/me/uploads/page.tsx`, `frontend/lib/auth/supabase.ts` (`@supabase/supabase-js`, env placeholders), `frontend/lib/upload.ts` (WebCrypto SHA-256, init → PUT → complete), `frontend/lib/sse.ts` reuse for job events, MSW handlers + fixtures for every stage path, `frontend/lib/i18n.ts` (B05 §3–4 copy), Vitest + Playwright `e2e/upload-flow.spec.ts` (mocks).
- **Tests:** signed-out → sign-in → upload → processing → "See what's ready"; each rejection copy; duplicate → toast; quota copy.
- **Commits:** `feat(frontend): Supabase sign-in` · `feat(frontend): upload page with hashing and rejections` · `feat(frontend): processing screen on job events` · `feat(frontend): my uploads` · `test(e2e): upload flow on mocks`.
- **Local follow-up:** try with the real local API + the Supabase project.

#### BG1 review — 💻 · S · (Sun 11 Oct) — prompt 5; `docs/gates/BG1.md`.

### B2 — Risk intelligence → BG2 (Sun 18 Oct). ☁️ parts pulled into week 1

#### B2.1a ★ Risk segmentation (fixtures) — ☁️ · O · `feat/b2.1-risk-segmentation` · "B2.1a Risk segmentation for PDFs and corpus text"
- **Depends:** B0.4.
- **Files:** `src/finsight/risks/segment.py` (PDF rule per fix 18; corpus rule: numbered headings + sentence shape; `group` from "Internal / External / Offer" sub-headings; skip the Summary's top-10 list and the preamble), `src/finsight/risks/__init__.py`, `core/schemas.py` (`Risk`), `tests/risks/test_segment.py` (3 synthetic + real fixture pages from 3 dev IPOs with hand-checked counts), `pipeline/risks_stage.py`.
- **Tests:** synthetic bold / numbered / mixed; real dev fixtures: title list matches a committed expected list; bold table headers don't start risks; page-break merges.
- **Commits:** `feat(risks): segment PDF risk factors by bold and numbered headings` · `feat(risks): segment corpus text without fonts` · `test(risks): golden segmentation on real dev pages` · `feat(pipeline): risks_split stage`.
- **Local follow-up:** B2.1b.

#### B2.1b Risk bank + E13 — 💻 · S · `data/b2.1b-risk-bank` · "B2.1b Risk bank, E13/E13b and teacher input export"
- **Depends:** B2.1a; 👤 segmentation spot-check + E13b labels (Sat 10).
- **Files:** `scripts/build_risk_bank.py` (corpus → `data/processed/bank/risk_bank.parquet`, embeddings with bge-m3 on the laptop GPU with Ollama stopped, or on Kaggle), `scripts/export_teacher_input.py` (5,000 risks, 40–600 words, ≤ 20 per company, stratified; → Kaggle private dataset), `data/gold/segmentation_gold.jsonl`, `eval_results/b/segmentation.json`.
- **Tests:** exclusion test (no showcase / gold IPO in the bank); E13 file schema.
- **Commits:** `data(risks): risk bank from the corpus` · `eval(risks): E13 and E13b segmentation` · `data(teacher): export teacher input set`.

#### B2.2a Unusualness, hedging, numbers (code) — ☁️ · S · `feat/b2.2-risk-features` · "B2.2a Risk features: novelty, hedging, numbers"
- **Depends:** B2.1a.
- **Files:** `risks/bank.py` (load, filter 2018–2023, exclude same company), `risks/novelty.py`, `risks/hedging.py` (Loughran–McDonald uncertainty subset + own list in `configs/hedges.yaml`), `risks/numbers.py` (reuse `normalize`), tiny fake bank fixture (`tests/fixtures/fake_bank.parquet` ≤ 200 KB with random unit vectors), `api` `/risks` + `/risks/{rid}`.
- **Tests:** novelty on the fake bank (known neighbours), same-company exclusion, hedge counts, hard-fact detection, sort orders, filters.
- **Commits:** `feat(risks): risk bank loader and novelty` · `feat(risks): hedging and hard facts` · `feat(risks): numbers in risks` · `feat(api): risks endpoints`.
- **Local follow-up:** B2.2b.

#### B2.2b Run + τ + E22 — 💻 · S · `eval/b2.2b-novelty` · "B2.2b Novelty threshold and E22"
- **Depends:** B2.1b, B2.2a; 👤 τ spot-check (Tue 13).
- **Files:** `scripts/novelty_pairs.py` (60-pair sheet at τ ∈ {0.75, 0.80, 0.85}), `data/gold/novelty_pairs.csv`, `eval_results/b/novelty.json`, `configs/risks.yaml` (`tau`), ADR.
- **Commits:** `data(gold): novelty spot-check sheet` · `eval(risks): E22 and the chosen threshold`.

#### B2.3a ★ Teacher notebook + filters — ☁️ · O · `feat/b2.3-teacher` · "B2.3a Teacher prompt, Kaggle notebook and filters"
- **Depends:** B0.2 (uses its own fake set if B0.4 is not merged yet).
- **Files:** `src/finsight/risks/teacher.py` (prompt from B03 §3.2, JSON schema, parse), `src/finsight/risks/filters.py` (B03 §3.3 drops with reasons; uses the verifier and the forbidden-phrase filter), `configs/forbidden_phrases.yaml` + `src/finsight/guard/phrases.py` (fix 24, shared), `notebooks/b2_teacher_kaggle.ipynb` (vLLM + Qwen ~14B AWQ, T4 fp16, batch, checkpoint every 100 items, resume), `scripts/quality_sheet.py` (quality-100 sheet), `docs/phase2/datasheets/teacher_outputs.md`, `docs/phase2/COLAB_STEPS_teacher.md` (optional ~32B path), `src/finsight/weaklabel/kaggle.py` reuse for push/poll, `tests/risks/test_teacher.py`, `tests/guard/test_phrases.py`.
- **Tests:** filters on hand-made bad outputs (each drop reason); phrase filter passes all B05 copy and blocks the instruction list; notebook smoke on 20 fake risks with a tiny HF test model on CPU (HF reachable from the cloud).
- **Commits:** `feat(guard): forbidden phrases shared by UI copy and rewrites` · `feat(risks): teacher prompt and output schema` · `feat(risks): deterministic filters with drop reasons` · `feat(notebooks): Kaggle teacher notebook with checkpoint and resume` · `docs(phase2): teacher datasheet and optional Colab steps`.
- **Local follow-up:** B2.3b.

#### B2.3b Teacher run — 💻 (Kaggle CLI) · S · `data/b2.3b-teacher-outputs` · "B2.3b Teacher pilot and full run on Kaggle"
- **Depends:** B2.1b, B2.3a; 👤 quality-100 on the pilot (Sun 11).
- **Steps:** pilot 500 (Sat 10) → filters → quality-100 → go/no-go (≥ 85 % "same meaning: yes") → full 5,000 (Mon 12).
- **Files:** `eval_results/teacher_quality.json`, `eval_results/b/teacher_filters.json` (drop rates), data in `data/processed/teacher/` (gitignored).
- **Commits:** `data(teacher): pilot outputs and quality check` · `data(teacher): full run, filters and drop rates`.

#### B2.4a Classifier code + notebooks — ☁️ · S · `feat/b2.4-risk-classifier` · "B2.4a Risk classifier: baseline, Kaggle notebooks"
- **Depends:** B2.1a.
- **Files:** `risks/classify.py` (TF-IDF+LR baseline with scikit-learn in a new `ml-cpu` group; DeBERTa inference via ONNX int8 for the CPU host), `notebooks/b2_classifier_base_kaggle.ipynb`, `notebooks/b2_classifier_large_kaggle.ipynb` (T4 fp16, 1 seed; Colab optional), `scripts/export_onnx_classifier.py`, `tests/risks/test_classify.py` (baseline on the fake set; ONNX path `@pytest.mark.local`).
- **Commits:** `feat(risks): TF-IDF baseline classifier` · `feat(notebooks): DeBERTa classifier notebooks for Kaggle` · `feat(risks): ONNX classifier inference`.

#### B2.4b Train + evaluate — 💻 (Kaggle CLI) · S · `eval/b2.4b-classifier` · "B2.4b Classifier training and E16"
- **Depends:** B2.3b, B2.4a; 👤 gold-150 verified (Wed 14).
- **Files:** `eval_results/b/classifier_*.json`, `docs/model_cards/risk_classifier.md`, ADR (pick by dev).
- **Commits:** `data(classifier): train/dev split by company` · `eval(classifier): E16 ladder on gold-150` · `docs: classifier model card`.

#### B2.5a ★ Student notebook + checks + serving code — ☁️ · O · `feat/b2.5-simplifier` · "B2.5a Simplifier: QLoRA notebook, post-checks, priority queue, CPU serving"
- **Depends:** B2.3a (filters, phrases), B1.2 (queue).
- **Files:** `risks/simplify.py` (prompt contract, post-checks in order: verifier numbers, forbidden phrases, length, certainty), `risks/certainty.py`, `jobs/simplify_worker.py` (auto top 15 by importance, then on click), `generate/llama_cpp_backend.py` reuse for the student GGUF, `generate/vllm_backend.py` (optional GPU path, OpenAI-compatible), `notebooks/b2_student_qlora_kaggle.ipynb` (Qwen ~3–4B, T4 fp16, LoRA r16, checkpoint + resume, merge, GGUF Q4_K_M export), `docs/phase2/COLAB_STEPS_student.md` (optional), `tests/risks/test_simplify.py`.
- **Tests:** every post-check with crafted rewrites; queue order + click bump; fallback model flagged in trace; notebook smoke with a tiny model on CPU.
- **Commits:** `feat(risks): rewrite post-checks for numbers, phrases, length and certainty` · `feat(jobs): simplification queue with top-15 auto and click bump` · `feat(generate): optional vLLM backend` · `feat(notebooks): student QLoRA on Kaggle with GGUF export`.
- **Local follow-up:** B2.5b.

#### B2.5b Train + evaluate — 💻 (Kaggle CLI) · S · `eval/b2.5b-simplifier` · "B2.5b Student training and E18–E20"
- **Depends:** B2.3b, B2.5a; 👤 gold-50 rating (Fri 16).
- **Files:** `models/simplifier/*.gguf` (not committed; private HF repo), `eval_results/b/{simplify_human,readability,simplify_checks}.json`, `docs/model_cards/simplifier.md`, `data/gold/simplify_gold50.csv`.
- **Commits:** `eval(simplify): E19/E20 on 10 IPOs` · `data(gold): blind gold-50 sheet` · `eval(simplify): E18 human ratings` · `docs: simplifier model card`.

#### B2.6a ★ Seriousness + risk level (code) — ☁️ · O · `feat/b2.6-risk-level` · "B2.6a Seriousness rule, normalised risk level and guard update"
- **Depends:** B1.4, B2.2a.
- **Files:** `risks/seriousness.py`, `src/finsight/risklevel/` (points, normalised score, thresholds from `configs/risklevel.yaml`, reasons with links, `corpus_n`, hide-behind-click flag), `guard/advice.py` (risk-level questions allowed; buy/apply still refused with the level shown as facts), `configs/risklevel.yaml` (placeholder thresholds marked `provisional: true`), `api` `/risk-level`, `tests/risklevel/`, `tests/guard/` (new cases).
- **Tests:** points and normalisation table tests; percentile; NA-heavy docs don't inflate; guard allows "how risky is this?" and refuses "should I apply?".
- **Commits:** `feat(risks): rule-based seriousness and importance` · `feat(risklevel): normalised points and corpus thresholds` · `feat(guard): allow risk-level questions` · `feat(api): risk level endpoint`.

#### B2.6b Corpus thresholds + validation — 💻 · S · `eval/b2.6b-risklevel-validation` · "B2.6b Thresholds, E17, E21 and E8 re-run"
- **Depends:** B2.6a, B1.3a run over the 2018–2023 corpus, B2.4b.
- **Files:** `scripts/corpus_points.py`, `configs/risklevel.yaml` (real thresholds, date, `corpus_n`), `src/finsight/evaluate/outcomes.py` (allow-listed, E21 only) + import-guard test, `eval_results/b/{seriousness,risklevel_validation}.json`, `eval_results/guard_b.json`, honest write-up in `docs/10_FINSIGHT_EXPLAINED.md` Part C.
- **Commits:** `feat(evaluate): outcome loader for E21 only` · `data(risklevel): corpus thresholds` · `eval(risklevel): E17 and E21` · `eval(guard): E8 re-run after the risk-level change`.

#### B2.7 CPU smoke deploy — 💻 + 👤 · S · `chore/b2.7-smoke-deploy` · "B2.7 CPU smoke deploy on the chosen free host" — **only after Akshat's "go"**
- **Depends:** B0.3 choice, B1.2, B3.3a (minimal image).
- **Steps:** build the API image, push, deploy API + worker job, Supabase wired, upload one fixture-sized PDF, record cold start and stage timings in `eval_results/b/smoke_deploy.json`; tear down or scale to zero.

#### BG2 review — 💻 · S · (Sun 18 Oct).

### B3 — Product and hosting → BG3 (Sun 25 Oct)

#### B3.1 Report UI: Overview + Red flags + Risks — ☁️ · S · `feat/b3.1-report-ui` · "B3.1 Report page: Overview, Red flags, Risks"
- **Depends:** B1.4, B2.2a, B2.6a (schemas).
- **Files:** `frontend/app/reports/[doc_id]/` tabs, `components/report/*` (RiskLevelCard with fixed disclaimer, RedFlagCard, RiskCard, StatusIcon in stamp-blue), `/ipos/[id]` redirect, MSW fixtures from the fixture pack `report.json`, `e2e/demo-flow.spec.ts` + demo hotkeys updated, i18n (Hindi note on risk tabs), phrase test over i18n.
- **Commits:** `feat(frontend): report shell and tabs` · `feat(frontend): risk level card` · `feat(frontend): red flags tab` · `feat(frontend): risks tab with sort, filter and search` · `test(e2e): report states and demo flow on /reports`.

#### B3.2 Compare — ☁️ · S · `feat/b3.2-compare` · *(cuttable)* · "B3.2 Compare tab: peers and corpus percentiles"
- `src/finsight/compare/`, `/compare`, frontend tab; percentiles from `corpus_stats.json` (2018–2023 subset).

#### B3.3a ★ Infra as code (CPU host) — ☁️ · O · `feat/b3.3-hosting` · "B3.3a Dockerfiles, CI images and deploy scripts for the CPU host"
- **Depends:** B0.3, B1.2. Pulled to Mon 12 for B2.7.
- **Files:** `deploy/api.Dockerfile` (no torch; llama.cpp, ONNX runtime), `deploy/worker.Dockerfile` (CPU; parse + ONNX + llama.cpp), `deploy/gpu/` (optional vLLM worker, documented only), `deploy/azure/` (Container Apps app + job definitions; KEDA Postgres scaler on `jobs.status='queued'`), `deploy/hf_space/` (single-container variant), `.github/workflows/images.yml` (build + push to GHCR on tags), `scripts/cloud_smoke.py`, `docs/runbooks/DEPLOY_RUNBOOK.md`, `ROLLBACK.md`, `COST_INCIDENT.md`.
- **Tests:** actionlint + hadolint in CI; `cloud_smoke.py` against the local API in CI (fixture PDF).
- **Commits:** `feat(deploy): CPU API and worker images` · `feat(deploy): Azure Container Apps app and queue-scaled job` · `feat(deploy): HF Space single-container variant` · `ci: image builds and Dockerfile lint` · `feat(scripts): cloud smoke test` · `docs(runbooks): deploy, rollback and cost incident`.

#### B3.3b Deploy — 💻 + 👤 · O · `chore/b3.3b-deploy` · "B3.3b Public deployment" — **only after Akshat's "go"**
- Upload showcase artefacts + GGUF models to Storage, deploy, run `cloud_smoke.py`, set budget alerts, Vercel env.

#### B3.4 Cloud evaluation + Model Lab + site copy — split
- **B3.4a ☁️ S** `feat/b3.4a-lab-b` "B3.4a Model Lab Phase 2 sections and site copy": `/api/lab/b/*` per the B06 mapping, Lab §7 sections, landing / How it works / About copy (B05 §2, §8).
- **B3.4b 💻 S** `eval/b3.4b-cloud-eval` "B3.4b E23/E24 and E7 on the cloud profile": 5 unseen + 3 showcase uploads; `latency_cloud.json`, `cost.json`, `e7_cloud.json`.

#### B3.5 Hardening — split
- **B3.5a ☁️ S** `fix/b3.5a-hardening` "B3.5a Security review, failure-path tests, admin page": `/security-review` pass, every stage-failure path, `/api/admin/*` + `/admin/costs`.
- **B3.5b 💻 S** `test/b3.5b-sweep` "B3.5b Playwright sweep on the real API".

#### BG3 review + FEATURE FREEZE — 💻 · (Sun 25 Oct).

### B4 — Documentation and finish

- **B4.1 ☁️ S** `docs/b4.1-docs-site` "B4.1 Industry-grade documentation (B09)": MkDocs site, generated references, model cards, datasheets, runbooks, root files, docs CI (lint only site sources; interrogate warn-only). 💻 follow-up: run the deploy + rollback runbooks once.
- **B4.2 ☁️ S** `docs/b4.2-report-drafts` "B4.2 Report drafts for Phase 2".
- **B4.3 👤** report, slides, video, viva.
- **Tag v2.0.0 💻** Sat 31 Oct.

## 4. Akshat's hand-work (dated)

| By | Task | For |
|---|---|---|
| Sat 3 Oct | Approve this PR | B0.2 |
| Sun 4 | Claim the cloud credit (deadline Wed 7, 23:59 PT); describe the B0.1 bug if you can | B0 |
| Mon 5 | Follow `HOSTING_SETUP_STEPS.md` (~45 min); pick Azure vs HF; confirm Kaggle phone verification + GPU quota | B0.3, BG0 |
| Wed 7 | 5 unseen RHPs → `data/raw/unseen/` | B1.1b, E23 |
| Thu 8 – Fri 9 | Gold v3 pre-fill (Claude chat, from `gold_v3_template.jsonl`) + verify (1.5 h) | B1.3b, B1.4 |
| Sat 10 | Segmentation spot-check (50) + E13b boundaries for 5 corpus excerpts | B2.1b |
| Sun 11 | Rate teacher pilot quality-100 (go/no-go) | B2.3b |
| Tue 13 | τ spot-check (60 pairs) | B2.2b |
| Wed 14 | Category gold-150 verification; "go" + console steps for the smoke deploy | B2.4b, B2.7 |
| Fri 16 | Rate gold-50 rewrites (blind) | B2.5b |
| Mon 19 – Thu 22 | Deploy logins; test uploads; phone check | B3.3b |
| after BG1 | Phase 1 leftovers (ADR-022/053/054, E7 sample, Hindi strings, ASR references) | report |
| Sun 25 – Sat 31 | Report, slides, video, viva | B4.3 |

## 5. Dependencies (critical path)

`B0.4 → B2.1a → B2.1b → B2.3b pilot → quality-100 → B2.3b full → {B2.4b, B2.5b} → B2.6b → BG2`
`B1.1a → B1.2 → B1.5 / B3.3a → B2.7 smoke → B3.3b → BG3`
`B0.4 + gold v3 → B1.3a → B1.3b → B1.4 → E15 → BG1`

If the teacher pilot is a no-go on Sun 11: fix the prompt and regenerate 500 on Mon 12 (≈ 1 h on Kaggle); if still no-go, cut item 4 of B07 §2 (serve the zero-shot base model with the same checks).
