# 07 — Roadmap: Phases, Sub-phases, Gates

**Today:** Tue 29 Sep 2026 · **Feature freeze:** Mon 26 Oct · **Submission:** Sun 1 Nov 2026

How to use this file
- Each **sub-phase** = one GitHub issue = one branch = one PR (see `08_GIT_WORKFLOW.md`). Branch names are given below.
- Each sub-phase lists **Done when** criteria. A sub-phase is not done until those pass and the PR is merged.
- Claude Code ticks the boxes and adds a one-line status note (`→ merged #12, 2026-10-02`) in the PR that completes the work.
- One sub-phase per Claude Code session is the norm; `/clear` between sessions.
- Backend (B) and frontend (F) tracks run in parallel from Phase 1. If usage limits bite, backend comes first.
- Model hint: **Opus** for the starred ★ sub-phases (hardest logic), Sonnet for the rest, Opus for any bug that failed twice.

---

## Gates

| Gate | Date | Must be true | If it fails |
|---|---|---|---|
| **G0** | Wed 30 Sep | Repo + CI green; `uv run poe test` passes; Ollama runs on GPU; dataset recon done; 10 demo IPOs (RHP + Prospectus) downloaded and registered | Slip P1 by one day; do not skip recon |
| **G1** | Tue 6 Oct | ≥ 9 of 10 demo IPOs parse (both documents); 4 key sections (Cover, The Offer, Capital Structure, Objects) found in ≥ 9; numeral suite green; training-corpus text available for ≥ 150 RHPs; gold v1 labelled | Demo set → 8 IPOs; Plan B corpus (`05` §1.3) |
| **G2** | Wed 14 Oct | X-Ray JSON for every demo IPO; ladder has 3 rows with real numbers; weak-label audit done | Ship with pretrained QA as the X-Ray extractor; keep fine-tune results as an experiment |
| **G3** | Tue 20 Oct | `/api/chat` end to end with citations + verdicts; scale-trick caught; guard works; Hindi voice question answered | Voice → P2; chat limited to suggested questions |
| **G4** | Fri 23 Oct | Full UI on the real API locally; Playwright demo test green on real API; demo cache recorded | Cut per list below |
| **G5** | Mon 26 Oct | **Feature freeze.** Deployed lite version reachable (or explicitly cut); all P0 stable | Remove anything unstable from the UI; write it up as future work |

## Cut order (if behind, cut from the top)
1. P2 items (compare, playgrounds, palette, v1.1 fields, QLoRA, upload)
2. Deployment (FR-20) → local demo + recorded video only
3. NLI text check (FR-17), advice classifier (FR-18) → keyword guard stays
4. BiLSTM-CRF rung (FR-15)
5. Inspector live mode → cached traces only
6. Hindi voice → typed Hindi only
7. Demo set 10 → 8 IPOs

**Never cut:** X-Ray with click-to-page highlight, chat verdict marks + evidence drawer, the scale-mismatch catch, the extractor ladder with real numbers, honest reporting.

---

## Phase 0 — Foundation (Tue 29 – Wed 30 Sep) → G0

### P0.1 Environment and repo [AKSHAT] — Tue 29 Sep
- [ ] Tools per `04_TECH_STACK_AND_RESOURCES.md` §2 (Git, gh, uv, Python 3.11, Node 22 + pnpm, Ollama, driver)
- [ ] GitHub repo created, docs committed, `gh auth` done
- [ ] Note idle RAM with normal apps open; `nvidia-smi` output saved to `PROGRESS.md`
**Done when:** `gh repo view` works; `ollama ps` shows GPU use for a test model.

### P0.2 Scaffold `chore/p0.2-scaffold` [CC]
- [x] Repo tree per `02_ARCHITECTURE.md` §5/§9 with empty packages + `__init__.py`
- [x] `pyproject.toml` (uv; dependency groups `api` / `ml` / `asr` / `dev`, torch only in `ml`), poe tasks, ruff, mypy config, pytest config (`slow` marker), `.gitignore` (done 30 Sep), `.gitattributes` (LF), `.env.example`, `NOTICE` (data licences)
- [x] pre-commit: ruff, ruff-format, nbstripout, end-of-file, large-file guard (> 5 MB)
- [x] GitHub Actions CI: backend lint/type/test (fast)
- [x] `README.md` stub with badge, `LICENSE` decision noted (code MIT; data/model NC-SA)
**Done when:** CI green on the PR; `uv run poe test` passes (one smoke test). → merged #14, 2026-09-30

### P0.3 Core `feat/p0.3-core` [CC]
- [x] `core/schemas.py`, `core/interfaces.py`, `core/registry.py`, `core/config.py` (profiles), `core/ids.py`, `core/logging.py`
- [x] `configs/config.yaml` with `dev_light` (default), `full`, `deploy_cpu`
- [x] Contract-first API skeleton: every route in `06` returns 501 with its response model; each SSE event is a pydantic model registered in OpenAPI; `poe gen-openapi` writes `openapi.json` (ADR-024)
- [x] Align `02` §6 with `06` (kind discriminator, value types, reason codes)
- [x] Tests: schema round-trips, registry, config profile loading
**Done when:** tests green; mypy clean on `core`. → merged #15, 2026-09-30

### P0.4 Data recon `data/p0.4-recon` [CC→AKSHAT]
- [x] [AKSHAT] Download the HF IPO dataset to `data/raw/ipo_dataset/`
- [x] [AKSHAT] Demo set chosen (10 IPOs, RHP + final Prospectus each) → `data/raw/rhp/` and `data/raw/prospectus/` ✅ 30 Sep
- [x] [CC] `ingest/recon.py` → summary printed; [CC] `configs/demo_ipos.yaml` (ids, files, pages, sha256, cover dates) ✅ 30 Sep; confirm offer structure per IPO; propose the 3 dev / 7 test split
- [x] [CC] 5 sample rows to `data/samples/`; ADR "Training corpus source" in `09_DECISIONS.md`
**Done when:** ADR written with the answers to `05` §1.2 Q1–Q3. **Gate G0 review.** → merged #16, 2026-09-30

---

## Phase 1 — Understand the documents (Thu 1 – Tue 6 Oct) → G1

### P1.1 ★ PDF text, words, page images `feat/p1.1-pdf-text` [CC] — Thu 1 Oct
- [x] `parse/pdf_text.py` (PyMuPDF words + bboxes + font info), `parse/page_images.py` (WebP ~110 DPI), scanned-page detection, header/footer stripping
- [x] Synthetic fixture PDF generator script (`tests/fixtures/make_fixture_pdf.py`) + committed 3-page fixture
- [x] `pipeline` CLI: `build --ipo <id> --stage parse`
- [x] `pipeline inspect` prints ≤ 40 lines and can write ≤ 30 truncated snippets to `data/samples/` (how CC sees a document without reading it)
- [ ] [AKSHAT] Run on all 20 demo documents; compare 3 by eye; paste problems into the next session
**Done when:** fixture tests green; all 20 demo documents produce `parsed.json` + page images; timing per document logged. → merged #17, 2026-09-30 (fixture generated at test time, not committed: PDFs are gitignored)

### P1.2 ★ Sections `feat/p1.2-sections` [CC] — Fri 2 Oct
- [x] `parse/sections.py`: TOC parse + printed→PDF page offset, heading regexes, font cues, voting, confidence
- [x] `RhpAdapter` implementing `DocTypeAdapter`
- [x] Report script: section found/not-found matrix for the demo set → `eval_results/sections.json`
**Done when:** the 4 key sections found in ≥ 9 of 10 RHPs (Prospectus tracked separately). → 10/10 RHPs, 10/10 Prospectuses; merged #18, 2026-09-30

### P1.3 Tables `feat/p1.3-tables` [CC] — Sat 3 Oct
- [x] Bake-off pdfplumber vs Docling on 3 table pages (Capital Structure, Objects) → ADR
- [x] `parse/tables.py` with header-scale detection ("₹ in million")
**Done when:** Objects-of-the-offer rows extracted for every demo IPO that has a fresh issue (pure-OFS IPOs correctly give `not_in_document`). → 8/8 RHPs + 8/8 Prospectuses; Hexaware and LG not_in_document; ADR-017 (Docling primary, PyMuPDF fallback); merged #19, 2026-09-30

### P1.4 ★ Numeral normalization `feat/p1.4-numerals` [CC] — Sun 4 Oct
- [x] Tests first: table-driven cases from `02_ARCHITECTURE.md` §10.4 and the list below, then hypothesis round-trip
- [x] `normalize/numerals.py`: ₹/Rs./INR/Rupees, $/USD tagging, lakh/lac/crore/cr/million/mn/billion/bn/thousand, Indian + Western grouping, decimals with scale, table header scale, parentheses negatives, `[●]`/`[•]`, ranges, percent + bps, NBSP and dash variants
- [x] `normalize/periods.py`: FY24, FY2024-25, Q3FY25, "quarter ended December 31, 2024"
- [x] `equal()` with precision tolerance; `to_unit()` for UI equivalents
**Done when:** ≥ 80 table cases + property tests green; mypy clean. → 96 table cases (18 Hindi) + 10 sentence/span tests + 5 hypothesis properties + 29 equality + 25 period tests; mypy strict clean; ADR-034; merged #20, 2026-09-30

### P1.5 Training corpus `data/p1.5-corpus` [CC→AKSHAT] — Mon 5 Oct
- [x] `ingest/corpus.py`: build `data/processed/corpus/<ipo_id>.json` from dataset text, or Plan B download + parse
- [x] Exclusion of demo IPOs (and later gold v2) + overlap test
- [x] Corpus stats → `eval_results/corpus_stats.json`
**Done when:** ≥ 150 (target ≥ 300) corpus IPOs with section-tagged text. → 389 IPOs (110 RHP, 279 Prospectus), 331 with all 4 key sections; merged #21, 2026-09-30. [AKSHAT] add the 10 gold-v2 company names to `data/gold/excluded_ipos.txt` and rerun `uv run python -m finsight.ingest.corpus build` (no overlap expected: the dataset ends in 2023).

### P1.6 Buffer + G1 review — Tue 6 Oct
- [x] `10_FINSIGHT_EXPLAINED.md` updated (C1 parsing, C2 sections, C2b tables, C2c corpus, C2d gold, C3 numerals)
- [ ] [AKSHAT] Eye-check 3 parsed documents; fix parser problems found
- [x] G1 passed (gold v1 labelled, validate --complete OK) → tag `v0.1.0`

### P1.7 Gold v1 tooling and labelling `data/p1.7-gold-v1` [AKSHAT + CC] — runs alongside P1.1–P1.5
- [x] [CC] `evaluate/gold.py` schema + validator; empty per-IPO template generator (no values) → merged #22; `uv run python -m finsight.evaluate.gold template|validate [--complete]|consistency`; empty template committed at `data/gold/gold_template.jsonl` (110 rows: copy to `gold_values.jsonl` and fill)
- [x] [AKSHAT] Gold v1: 110 values AI-prefilled then verified by Akshat, PDF page recorded (`05` §2, ADR-035) → `data/gold/gold_values.jsonl` (`gold import-prefill`)
- [ ] [AKSHAT, low priority] Download 10 more IPOs (2025–26, RHP + Prospectus each) for gold v2; test one full-RHP upload in a frontier app (`05` §7)
**Done when:** validator passes on all ~110 values; committed before P2.1 starts. → passes, 110 rows, `label_source: ai_assisted_verified`.

---

## Phase 2 — Extraction and our model (Wed 7 – Wed 14 Oct) → G2

### P2.1 Field registry + rules (Rung 1) `feat/p2.1-rules` [CC] — Wed 7 Oct
- [x] `configs/fields.yaml` (11 fields, EN/HI labels, document (RHP or Prospectus), sections, questions, extractor, fallback, `ladder` flag; `offer_price` = rules-only on the Prospectus cover, `ladder: false`, like `objects_of_offer`; `price_band` is `[●]` in all 10 RHPs: `ladder: false`, expect status `placeholder` on RHPs)
- [x] Extractor cases from gold v1: `total_issue_size` and `ofs_amount` are stated in the RHP for HDB, Hexaware, PhysicsWallah and Urban Company and `[●]` for the other six (handle both); Tata Capital `fresh_issue_size` is a placeholder in the RHP (shares only)
- [x] `extract/rules.py` against SEBI standard wording (cover page, The Offer); tests with real-looking sentences in `data/samples/`
- [x] Tune rules on the 3 dev IPOs only; gold v1 already exists from P1.7 (33/33 dev values agree; `scripts/rules_dev_check.py`)
**Done when:** rules produce candidates for all demo IPOs; tests green. → 10/10 IPOs, both documents; `eval_results/rules_candidates.json`; ADR-036; #26.

### P2.2 Pretrained QA + X-Ray v0 `feat/p2.2-qa-pretrained` [CC] — Thu 8 Oct
- [x] `extract/qa_pretrained.py` (deberta-v3-base-squad2, GPU fp16, section-restricted passages)
- [x] `extract/select.py` candidate selection; `verify/consistency.py`; `extract/xray.py`
- [x] `pipeline build --stage xray` for all demo IPOs (`--stage qa` first, ml group)
**Done when:** `xray.json` exists for every demo IPO; consistency checks run. → 10/10; `eval_results/xray_summary.json`; ADR-037; #28.

### P2.3 ★ Weak labelling `feat/p2.3-weaklabel` [CC] — Fri 9 Oct
- [x] `weaklabel/seeds.py`, `propagate.py`, `negatives.py`, `build_squad.py`, `audit.py`
- [x] SQuAD 2.0 JSONL train/dev split by IPO; stats file; audit sample file
**Done when:** train/dev JSONL built; stats committed; audit file ready for Akshat. → `python -m finsight.weaklabel build`: 302 IPOs, 1,869 positives / 2,791 negatives, train 272 IPOs, dev 30; `eval_results/weaklabel_stats.json`; `data/gold/weaklabel_audit.jsonl` (50 rows); ADR-038; #30.

### P2.4 Audit + fine-tune notebook `feat/p2.4-finetune-nb` [CC→AKSHAT] — Sat 10 Oct
- [ ] [AKSHAT] Audit 50 weak labels (~1 h) → E1
- [x] [CC] `notebooks/01_finetune_extractor.ipynb`: parameterized, seeds 13/42/2026, checkpoint + resume, fp32 fallback, writes `metrics.json`
- [x] [CC] `evaluate/metrics.py` (EM, F1, NVM, list F1) with tests
- [x] [CC] Upload helper: package JSONL as a private Kaggle dataset (instructions for Akshat)
**Done when:** notebook runs end to end on a 200-example slice on Kaggle.

### P2.5 Training runs [AKSHAT] — Sun 11 Oct (runs in background)
- [ ] 3 seeds on Kaggle; download weights to `models/extractor/`; commit metrics JSON
- [ ] Optional ablations E4 if quota allows

### P2.6 Fine-tuned extractor + ladder `feat/p2.6-ladder` [CC] — Mon 12 – Tue 13 Oct
- [ ] `extract/qa_finetuned.py`; `evaluate/ladder.py` → `ladder_table.{csv,json,tex}`
- [ ] `evaluate/run_gold.py` runs all rungs on gold v1 → E2, E3
- [ ] Choose extractor per field in `fields.yaml` from results (ADR); regenerate X-Rays
**Done when:** ladder table has 3 rows with real numbers and `n`.

### P2.7 Buffer + G2 review — Wed 14 Oct
- [ ] Update `10_FINSIGHT_EXPLAINED.md` (extractive QA, distant supervision, fine-tuning, metrics); tag `v0.2.0`

---

## Phase 3 — Trustworthy chat (Thu 15 – Tue 20 Oct) → G3

### P3.1 Retrieval `feat/p3.1-retrieval` [CC] — Thu 15 Oct
- [x] `retrieve/chunk.py`, `bm25.py`, `dense.py` (offline GPU fp16 build; online ONNX int8), `fuse.py`, `rerank.py`, `Retriever`
- [x] Index all demo IPOs; **measure RAM/VRAM** in `full` profile → ADR updating `02` §12
- [ ] [AKSHAT+CC] Write dev/test questions (`05` §8) — can start earlier
**Done when:** E6 run on dev questions; abstain threshold tuned on dev only. *(Harness built; waits on the question sets, which are [AKSHAT]: `python -m finsight.retrieve.evaluate --dense --rerank`.)*

### P3.2 Generation + LLM bake-off `feat/p3.2-generate` [CC→AKSHAT] — Fri 16 Oct
- [x] `generate/llm_backend.py` (Ollama; llama-cpp stub), `prompts.py` (EN + HI), thinking disabled
- [x] Prompt-injection test with adversarial chunk
- [x] Bake-off script; [AKSHAT] judge Hindi fluency (`data/gold/hindi_fluency_sheet.csv`, 1-5) → finalises ADR-020
**Done when:** CLI `python -m finsight.generate ask --ipo <id> "question"` prints a cited answer (`finsight.chat ask` arrives in P3.6).

### P3.3 ★ Verifier + seeded errors `feat/p3.3-verifier` [CC] — Sat 17 Oct
- [ ] `verify/claims.py`, `numeric_check.py` (all reason codes), `verdict.py`; tests per reason code
- [ ] `evaluate/seeded_errors.py` → E5
**Done when:** scale-mismatch recall on seeded set ≥ 95 % (or the miss is explained in an ADR); CLI shows verdicts.

### P3.4 Advice guard `feat/p3.4-guard` [CC] — Sun 18 Oct (morning)
- [ ] `guard/advice.py` keyword/regex EN/HI/Hinglish + facts payload; scored on Akshat's advice set (≥ 50 advice + ≥ 50 factual, written by him and friends) + tests → E8 (keyword row)

### P3.5 Voice `feat/p3.5-voice` [CC→AKSHAT] — Sun 18 Oct (afternoon)
- [ ] `voice/asr.py` backends + lazy load/unload; ASR bake-off script → E12 + ADR
- [ ] [AKSHAT] Record 10 Hindi questions to `data/raw/audio/`

### P3.6 Chat orchestrator + traces `feat/p3.6-chat` [CC] — Mon 19 Oct
- [ ] `chat/orchestrator.py` emitting the event sequence of `06_API_CONTRACT.md`; traces to SQLite; E7 script
**Done when:** CLI streams events for normal, trick, abstain, advice cases.

### P4 — API (overlaps: Mon 19 – Tue 20 Oct)
#### P4.1 API `feat/p4.1-api` [CC]
- [ ] All endpoints in `06_API_CONTRACT.md`, SSE via sse-starlette, error envelope, CORS, `/health` with ModelManager
- [ ] Demo cache + `poe record-demo`; OpenAPI export; contract tests
**Done when:** contract tests green; `curl` streams a full event sequence. **Gate G3 review; tag `v0.3.0`.**

---

## Frontend track (runs on mocks until F6)

| Sub-phase | Date | Branch | Scope | Done when |
|---|---|---|---|---|
| **F1** | Fri 2 Oct | `feat/f1-scaffold` | Next.js scaffold, Tailwind + tokens (`03` §2), fonts, shadcn, Zustand store, TanStack Query, MSW + fixtures generated from pydantic schemas, AppShell, `/ipos` Library, `frontend/CLAUDE.md` from template, CI job | Library renders on mocks; lint/typecheck/build green |
| **F2** | Sat 3 Oct | `feat/f2-viewer` | Workspace layout (resizable, mobile tabs), PageViewer, HighlightLayer, thumbnails, section jump, prefetch | Clicking a mock source highlights in < 300 ms |
| **F3** | Mon 5 Oct | `feat/f3-xray` | XRayPanel, FactRow, popover, VerdictMark, UnitToggle, composition + proceeds charts, extractor compare, `lib/format.ts` + Vitest | All X-Ray acceptance items on mocks |
| **F4** | Fri 9 Oct | `feat/f4-chat` | `lib/sse.ts`, ChatPanel, stage line, citation chips, tick-and-tie reveal, EvidenceDrawer, Abstain/Advice cards, meter, suggested chips | 4 mock streams (normal/trick/abstain/advice) render correctly |
| **F5** | Sun 11 Oct | `feat/f5-voice-inspector` | MicButton (MediaRecorder), language toggle + i18n dictionary, InspectorDrawer, GlossaryDrawer | Inspector fills from mock SSE; Hindi strings render |
| **F6** | Wed 21 Oct | `feat/f6-integration` | Generate types from real OpenAPI, switch off mocks, fix contract mismatches, ColdStartBanner, HealthDot | Full flow works on the real API |
| **F7** | Thu 22 Oct | `feat/f7-lab-landing` | Model Lab (ladder, heatmap, verifier, weak-label, frontier), Landing, How-it-works | Pages read real `eval_results` |
| **F8** | Fri 23 Oct | `feat/f8-demo-mode` | DemoController + hotkeys, Playwright `e2e/demo-flow.spec.ts`, polish list from Akshat's phone/laptop test | Playwright green on real API. **Gate G4; tag `v0.4.0`** |

[AKSHAT] after each F sub-phase: review in the browser for 10 minutes and file issues for anything off.

---

## Phase 5 — Depth and rigour (Wed 21 – Mon 26 Oct, cuttable in order)

| Sub-phase | Branch | Owner | Scope |
|---|---|---|---|
| P5.1 Gold v2 | `data/p5.1-gold-v2` | [AKSHAT] + [CC] tooling | +10 held-out IPOs (RHP + Prospectus), parse + label (assisted, disclosed) → final ladder numbers |
| P5.2 Frontier comparison | `eval/p5.2-frontier` | [AKSHAT] runs, [CC] scoring | E9 incl. verifier on frontier answers |
| P5.3 BiLSTM-CRF rung | `feat/p5.3-bilstm-crf` | [CC→AKSHAT] | BIO conversion, notebook, 3 seeds → E11, auto-appears in ladder |
| P5.4 Advice classifier | `feat/p5.4-guard-clf` | [CC→AKSHAT] | MuRIL on advice set → E8 row; swap via config |
| P5.5 NLI text check | `feat/p5.5-nli` | [CC] | Inference-only check for non-numeric claims; off in `deploy_cpu` |
| P5.6 Glossary content | `feat/p5.6-glossary` | [CC] drafts, [AKSHAT] reviews HI | FR-19 |
| P5.7 Latency + memory benchmark | `eval/p5.7-latency` | [CC] | E10, both profiles |

## Phase 6 — Deploy and harden (Sat 24 – Mon 26 Oct) → G5

### P6.1 Deploy backend `feat/p6.1-deploy-api` [CC] + [AKSHAT] clicks
- [ ] Dockerfile (CPU torch, `deploy_cpu` profile), artifact bundle script → HF dataset repo, HF Space config, llama-cpp backend
### P6.2 Deploy frontend `feat/p6.2-deploy-web` [CC] + [AKSHAT]
- [ ] Vercel project, env vars, API base URL, "public demo is slower" note
### P6.3 Hardening `fix/p6.3-hardening` [CC]
- [ ] Rate limits, error copy review, 404/500 pages, README with GIFs + architecture diagram + results table + live link
**Done when:** someone else opens the link on their phone and completes Flow A–C. **Feature freeze; tag `v1.0.0-rc.1`.**

---

## Phase 7 — Report, slides, viva (Tue 27 Oct – Sun 1 Nov). No new features.

| Day | Work | Owner |
|---|---|---|
| Tue 27 | Freeze `eval_results/`; `poe ladder` + all figure scripts; reproducibility check from a clean clone | [CC] |
| Tue 27 – Wed 28 | Report draft from committed results (structure below); CC drafts, Akshat rewrites in his voice and owns every claim | joint |
| Thu 29 | Slides (≤ 12) + 3-min demo script; record backup demo video | [AKSHAT], [CC] outline |
| Fri 30 | Viva prep: `10_FINSIGHT_EXPLAINED.md` questions aloud without notes; bug fixes only | [AKSHAT] |
| Sat 31 | Final README, release notes, tag **`v1.0.0`**, GitHub Release with report PDF | joint |
| Sun 1 Nov | **Submit** | [AKSHAT] |

Branches in this phase: `docs/p7-report`, `docs/p7-readme`, `fix/*` only.

### Report skeleton
1 Abstract (contribution claim from `01_PRD.md` §1 with real numbers) · 2 Introduction · 3 Related work · 4 Data (+ licences) · 5 Preprocessing (PDF parsing, sections, **Indian numeral normalization**) · 6 Method (ladder, distant supervision, retrieval, generation, verifier, guard, voice) · 7 Results · 8 Error analysis (10 real failures) · 9 Ethics and limitations · 10 Future work · 11 Reproducibility statement.

### Demo script (3 min)
Hook (20 s) → X-Ray + click-to-page (40 s) → cited answer with ✅ (30 s) → scale-trick ❌ + evidence drawer (30 s) → Hindi voice (25 s) → advice guard (15 s) → Model Lab ladder (20 s). Run with `?demo=1` hotkeys; backup video open in another tab.

---

## Weekly rhythm

- **Daily:** CC updates `PROGRESS.md` (≤ 10 lines) in the last PR of the day.
- **Every gate:** Akshat runs the full slow test suite, opens the UI, and decides cuts.
- **Sundays:** lighter day; labelling/review tasks rather than new modules.
