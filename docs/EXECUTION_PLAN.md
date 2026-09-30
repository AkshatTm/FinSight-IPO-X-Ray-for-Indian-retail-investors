# EXECUTION PLAN — how each sub-phase gets built

**Scope:** files, tests, planned commits, owner and model for every sub-phase in `07_ROADMAP.md`. Dates, gates, checkboxes and the cut order stay in `07_ROADMAP.md`, which wins on any conflict. Field lists and payloads stay in `01`/`02`/`06`.
**Status:** proposed, awaiting Akshat's approval (PR `docs/execution-plan`). Written 30 Sep 2026.

---

## 0. Ground rules for this plan

- **Order, not dates.** Work moves to the next sub-phase as soon as the current one is merged. Dates in `07` are soft targets; the gates (G0–G5) are quality checkpoints and are never skipped.
- **Backend first.** The F track fills gaps when a backend sub-phase is waiting on Akshat (labelling, Kaggle runs, downloads).
- **Claude Pro budget.** Sonnet 5.5 is the default. **Opus** is used for ★ sub-phases and for any bug that failed twice. If usage runs out mid-sub-phase: commit what is green, push, write one line in `PROGRESS.md`, stop.
- **Autopilot (from 30 Sep, Akshat's instruction).** Sub-phases run back to back. For work > ~50 lines, the plan (≤ 15 lines) goes in the PR description instead of waiting for "go". Stop and wait only for: (a) hand-work from Akshat when nothing else is unblocked (continue the F track or any other unblocked sub-phase first); (b) gate reviews G0–G5 (Prompt 5 + checklist); (c) proposed edits to `01_PRD`, `02_ARCHITECTURE` or `06_API_CONTRACT`; (d) anything destructive or irreversible; (e) `BLOCKED.md`; (f) a **model switch** (see "Model check" below). After every merged sub-phase update `PROGRESS.md` and the `07` checkboxes.
- **Model check (before starting every sub-phase, both directions).** Look up the sub-phase's Model column (★ sub-phases, and bugs that failed twice on Sonnet, are Opus). If it differs from the running model, stop before any work and print exactly: "🔁 MODEL SWITCH: next is <ID> (<title>) — recommended <Opus/Sonnet>. Type /model <opus/sonnet>, then say continue." If it matches, print "✓ Model OK: <ID> on <model>" and continue. After merging a ★ sub-phase whose successor is S, stop with the switch message.
- **Sub-phase loop** (from the kickoff prompt): re-read → plan if > ~50 lines → branch from fresh `main` → tests first → small green commits → lint/typecheck/test → tick `07`, update `PROGRESS.md`, append `10` Part C, add ADRs (proposed) → PR (closes issue) → CI green → `gh pr merge --rebase --delete-branch` → hand-off list → "✅ done".
- **Commit format:** Conventional Commits, `Refs #n`, trailer as set by the session. Commits below are the *planned* shape (3–10 each); actual messages follow the work.
- **Model column:** S = Sonnet 5.5, O = Opus 5.5.

## 1. Fixes approved in STEP 2 (and where each lands)

| Fix | Decision | Lands in |
|---|---|---|
| B1 | RHPs leave price, total and OFS ₹ as `[●]`. Fields: `fresh_issue_size`, `ofs_shares` (count), `ofs_amount` (may be `[●]`), `offer_price` (from Prospectus), `price_band` (optional; RHP or price-band ad). Each IPO has **two documents**: RHP and final Prospectus, parsed by the same pipeline. A placeholder in the RHP is a normal ⚠️ | docs PR (01, 02, 06, 05), ADR-023, P0.3, P1.1, P2.1 |
| B2 | Answers use Western digits only. Normalizer parses लाख/करोड़/हज़ार/अरब/रुपये and Devanagari digits if they appear in a document | ADR-028, P1.4 |
| B3 | `scale_mismatch` only when ratio is 10ᵏ **and** (scale words differ **or** printed digits are identical); otherwise `wrong_value` | ADR-027, 02 §10.3, P3.3 |
| B4 | Ladder field list written down. Names propagate by normalized fuzzy match. Lists scored with list-F1. `objects_of_offer` uses the table extractor only | 05 §3/§4, P2.1, P2.3, P2.6 |
| B5 | PDF page in the chip, printed page in the popover; both stored | ADR-025, 02 §6, 06, P1.1 |
| C1 | 10 demo IPOs = **3 dev / 7 test**; gold v1 labelled in Phase 1 before any extractor exists; rules and extractor choice tuned on dev only | ADR-026, 05 §1, P1.7 |
| C2 | Headline claim = overall NVM + bootstrap CI + paired comparison; per-field results descriptive. Gold v2 (10 more IPOs) downloaded during Phase 1 | 01 §8, 05 §4, P5.1 |
| C3 | Ladder reported on the full document **and** body-only (cover masked) | ADR-031, P2.6 |
| C4 | Advice/factual test set written by Akshat + friends before P3.4; my lines go to classifier training only | 05 §1.1, P3.4 |
| C5 | E5 is called a unit benchmark; add verifier runs on real LLM answers (E7) and frontier answers (E9) with a hand-checked sample | 05 §6, P3.6, P5.2 |
| C6 | Test one full-RHP upload to a frontier app in Phase 1; add a same-top-5-passages condition if truncated | Akshat hand list, P5.2 |
| D1 | Contract-first: FastAPI skeleton with every route + SSE event models in OpenAPI at P0.3; `gen-openapi` works from day 1 | ADR-024, P0.3, F1 |
| D2 | One alignment commit fixes 02 §6 vs 06 mismatches (`kind`, text/list/table values, `reason_code`, `derived`, `char_to_bbox`, timing keys, `rate_limited`, SQLite names) | P0.3, docs PR |
| D3 | `configs/suggested_questions.yaml`, filled from `xray.json` | P4.1 |
| D4 | `configs/` holds `config.yaml`, `fields.yaml`, `demo_ipos.yaml`, `suggested_questions.yaml` | 02 §9, P0.3, P0.4 |
| D5 | Dependency groups `api` / `ml` / `asr` / `dev`; CI installs no torch | ADR-029, P0.2 |
| D6 | Ollama RAM counted; demo runs `next start`, not `next dev`; measured in P3.1 | 02 §12, P3.1 |
| D7 | Deploy: browser calls the Space directly; `deploy_cpu` = BM25 + small rerank + smallest LLM; scripted questions from demo cache | ADR-022, P6.1 |
| E1 | Rule reworded: one *primary* package per sub-phase; wiring in others only via `__init__`. P3.2 CLI is `finsight.generate ask` | CLAUDE.md, P3.2 |
| E2 | `pipeline inspect`: prints ≤ 40 lines, writes ≤ 30 truncated snippets to `data/samples/` | CLAUDE.md, P1.1 |
| E3/E4 | F track slips first; this file holds only files/tests/commits/model | this file |
| E5 | Branch protection on `main` (CI required, linear history); `.gitattributes` LF | STEP 4, P0.2 |
| E6 | Gold v2 downloads in Phase 1; question sets and advice set on Sundays in Phase 2 | hand list |
| F | Repo name in 04, version string, pure-OFS `not_in_document`, Flow E copy, default profile `dev_light`, data-licence NOTICE, demo voice clip (approved, `frontend/public/demo/`) | docs PR, P0.2, F8 |

**Demo set deviations from `05` §1.4** (10 IPOs, all 2025, all with RHP + Prospectus): the mix requirement (≥ 3 pure fresh) cannot be met from what is downloaded. As far as I know, Hexaware and LG are pure OFS and the other eight are mixed; **P0.4 recon confirms this from the Prospectus offer tables**. Akshat may add 2 pure-fresh IPOs later (`configs/demo_ipos.yaml` takes more rows). Gate numbers scale: "≥ 10 of 12" becomes "≥ 9 of 10". Proposed split (confirm in P0.4): **dev** = hexaware-technologies-2025 (pure OFS), ather-energy-2025 (mixed), urban-company-2025 (mixed, smallest); **test** = the other seven, including LG (pure OFS), HDB and Tata Capital (financial), Lenskart (1083 pages, performance test).

---

## Phase 0 — Foundation → G0

### P0.1 Environment and repo — [AKSHAT]
Done so far: `gh auth` (AkshatTm), `core.autocrlf=false`, both emails verified, docs merged to `main` (PR #1). Left: `pnpm` (`corepack enable` from admin PowerShell, else `npm i -g pnpm`), Ollama + GPU test (`ollama ps`), idle RAM and `nvidia-smi` into `PROGRESS.md`. Tell CC "P0.1 done".

### P0.2 Scaffold — [CC] · S · branch `chore/p0.2-scaffold` · issue "P0.2 Scaffold: uv project, poe tasks, CI, pre-commit"
- **Files:** `pyproject.toml` (uv; dependency groups `api`, `ml`, `asr`, `dev`; poe tasks per 04 §3; ruff, mypy, pytest config with `slow` marker), `uv.lock`, `src/finsight/<15 packages>/__init__.py` (layout per 02 §5), `tests/test_smoke.py`, `.gitattributes` (LF), `.env.example`, `.pre-commit-config.yaml` (ruff, ruff-format, nbstripout, end-of-file, 5 MB guard), `.github/workflows/backend.yml`, `.github/pull_request_template.md` (08 §5), `README.md` stub, `NOTICE` (code MIT; data and derived model NC-SA), `CHANGELOG.md`.
- **Tests:** `test_smoke.py` imports every package; `uv run poe lint|typecheck|test` green locally and in CI.
- **Commits:** (1) `build: initialise uv project with dependency groups and poe tasks` · (2) `build: configure ruff, mypy and pytest markers` · (3) `feat: add empty package skeleton per architecture map` · (4) `test: add package import smoke test` · (5) `chore: add pre-commit hooks including 5 MB file guard` · (6) `ci: add backend lint, typecheck and test workflow` · (7) `docs: add README stub, NOTICE and PR template`.
- **Note:** a CUDA torch wheel is pinned under the `ml` group only; CI never installs it.

### P0.3 Core and contract-first API skeleton — [CC] · S · branch `feat/p0.3-core` · issue "P0.3 Core schemas, interfaces, config, API skeleton"
- **Files:** `core/{schemas,interfaces,registry,config,ids,logging}.py`, `configs/config.yaml` (profiles; default `dev_light`), `api/app.py` + routers (every route in 06 returns 501 with its response model), `api/events.py` (one pydantic model per SSE event, registered in OpenAPI), `scripts/gen_openapi.py` → `openapi.json` (committed), `tests/core/*`, `tests/api/test_openapi.py`.
- **Schema alignment (D2):** `Amount` gets a `kind` discriminator; add `TextValue`/`ListValue`/`TableValue`; `FieldResult.reason_code`; `derived` as decimal strings; `Passage.char_to_bbox` required when built from parsed docs; `doc_type: rhp|prospectus` on `ParsedDoc`/`Passage`/`Candidate`; `page` (PDF) and `printed_page`; reason codes for X-Ray cases; `rate_limited` error code; timing keys equal stage names; SQLite tables `ipos`, `traces`, `demo_cache` only.
- **Tests:** schema round-trips (every union member), registry lazy-load, profile loading and env override, ULID ordering, OpenAPI snapshot includes every SSE event model; mypy clean on `core`.
- **Commits:** (1) `test(core): schema round-trip tests for amounts and results` · (2) `feat(core): pydantic schemas with kind-discriminated amounts` · (3) `feat(core): protocols and registry decorators` · (4) `feat(core): profile-based settings and config.yaml` · (5) `feat(core): ULID trace ids and JSON logging` · (6) `feat(api): route skeleton returning 501 with response models` · (7) `feat(api): SSE event models registered in OpenAPI` · (8) `build(api): gen-openapi task and committed openapi.json` · (9) `docs(arch): align 02 schemas and 06 contract`.

### P0.4 Data recon — [CC→AKSHAT] · S · branch `data/p0.4-recon` · issue "P0.4 Data recon and demo set registry"
- **Already done (30 Sep):** 20 PDFs moved to `data/raw/{rhp,prospectus}/<ipo_id>.pdf`; page-1 titles checked (10 RHP titled RED HERRING PROSPECTUS, 10 Prospectus titled PROSPECTUS); Meesho's two files confirmed different (286 of 689 pages differ); `configs/demo_ipos.yaml` written (id, company, pages, sha256, cover dates); dataset downloaded (README, mainline Excel, mainline text zip, questions CSV).
- **Files:** `ingest/recon.py` (prints summary only), `ingest/registry.py` (`list_demo_ipos()`), `configs/demo_ipos.yaml` (+ `split: dev|test`), `data/samples/ipo_dataset_rows.jsonl` (5 truncated rows), `tests/ingest/*`, ADR-016 in `09`.
- **Recon must answer (05 §1.2):** full RHP text or partial? mainboard vs SME counts and years? usable company/ISIN/date for de-duplication? Also: which text-zip entries are RHP-derived (`most_relevant_link`, `File_Rename_1st`); how the Excel's Fresh Issue / OFS / Total / Price Band / Face Value columns cross-check seeds; confirm the Ather/Hexaware/etc. offer structures from the Prospectus. Broker/member subscribe-avoid columns and listing-day targets are never read.
- **Tests:** registry loads the YAML, ids are slugs, split has 3 dev / 7 test, sha256 format valid, files exist when `data/raw` is present (skipped in CI).
- **Commits:** (1) `data: register 10 demo IPOs with RHP and Prospectus checksums` · (2) `feat(ingest): demo IPO registry loader` · (3) `test(ingest): registry and split invariants` · (4) `feat(ingest): recon script that prints dataset summary only` · (5) `data: add 5 truncated dataset sample rows` · (6) `docs(decisions): ADR-016 training corpus source`.
- **Gate G0 review** after merge (Prompt 5).

---

## Phase 1 — Understand the documents → G1 (thresholds scaled to 10 IPOs: ≥ 9 of 10)

### P1.1 ★ PDF text, words, page images — [CC] · O · `feat/p1.1-pdf-text` · "P1.1 PDF text, words and page images"
- **Files:** `parse/pdf_text.py`, `parse/page_images.py`, `parse/clean.py` (repeated header/footer strip, scanned-page flag), `pipeline/cli.py` (`build --ipo <id> --doc rhp|prospectus --stage parse`, `inspect`), `tests/fixtures/make_fixture_pdf.py` + committed 3-page fixture, `tests/parse/*`.
- **Printed vs PDF page (B5):** `Page.number` is the PDF page; `printed_page` is read from the page footer where present.
- **`pipeline inspect` (E2):** prints ≤ 40 lines per call (page count, chars/page stats, first lines of chosen pages, scanned flags) and can write ≤ 30 truncated snippets to `data/samples/`. This is how CC "sees" a document.
- **Tests:** fixture words/bboxes exact; header/footer stripping; scanned detection; WebP written; parsing 20 documents logs timing (slow-marked, local only).
- **Commits:** (1) `test(parse): fixture PDF generator and expected words` · (2) `feat(parse): PyMuPDF words with boxes and font info` · (3) `feat(parse): strip repeated headers and footers` · (4) `feat(parse): detect scanned pages` · (5) `feat(parse): render WebP page images` · (6) `feat(pipeline): parse stage CLI with per-document timing` · (7) `feat(pipeline): inspect command with output caps` · (8) `docs(explained): C1 parsing`.
- **Akshat:** run on all 20 documents, compare 3 by eye, paste problems next session.

### P1.2 ★ Sections — [CC] · O · `feat/p1.2-sections` · "P1.2 RHP section detection"
- **Files:** `parse/sections.py` (TOC parse + printed→PDF offset, heading regexes, font cues, voting, confidence), `parse/rhp_adapter.py` (`DocTypeAdapter`), `pipeline` report command → `eval_results/sections.json`, `tests/parse/test_sections.py`.
- **Prospectus:** same adapter; its cover and "The Offer" section are the sources for `offer_price` (P2.1).
- **Tests:** synthetic TOC with offset; heading regex variants; voting/confidence; matrix script shape. **Done:** the 4 key sections in ≥ 9 of 10 RHPs (Prospectus tracked separately).
- **Commits:** (1) `test(parse): TOC lines and page-offset cases` · (2) `feat(parse): parse table of contents with printed-page offset` · (3) `feat(parse): SEBI heading regexes` · (4) `feat(parse): font-cue detector` · (5) `feat(parse): vote across methods with confidence` · (6) `feat(parse): RhpAdapter` · (7) `eval(parse): section found/not-found matrix` · (8) `docs(explained): C2 sections`.

### P1.3 Tables — [CC] · S · `feat/p1.3-tables` · "P1.3 Table extraction and pdfplumber vs Docling bake-off"
- **Files:** `parse/tables.py` (header-scale detection "₹ in million"), `scripts/table_bakeoff.py`, ADR-017, `tests/parse/test_tables.py`.
- **Done:** Objects-of-the-offer rows for every IPO that has fresh issue (pure-OFS IPOs correctly report `not_in_document`).
- **Commits:** (1) `test(parse): header-scale detection cases` · (2) `feat(parse): pdfplumber table extraction for key sections` · (3) `feat(parse): apply header scale to cells` · (4) `eval(parse): table bake-off on 3 pages` · (5) `docs(decisions): ADR-017 table extractor`.

### P1.4 ★ Numeral normalization — [CC] · O · `feat/p1.4-numerals` · "P1.4 Indian numeral normalization"
- **Files:** `normalize/numerals.py`, `normalize/periods.py`, `normalize/equality.py` (`equal`, `to_unit`), `tests/normalize/{test_cases_table.py,test_properties.py}`.
- **Scope adds (B2):** लाख/करोड़/हज़ार/अरब/रुपये/₹, Devanagari digits in input; output always Western digits. Placeholders `[●]`/`[•]`, ranges, bps, parentheses negatives, NBSP and dash variants, table header scale.
- **Tests first:** ≥ 80 table cases (incl. ≥ 12 Hindi) + hypothesis round-trip (format a random amount in many styles → parse → `equal`). mypy clean.
- **Commits:** (1) `test(normalize): table cases for lakh, crore and million` · (2) `feat(normalize): Indian and Western digit grouping` · (3) `feat(normalize): scale words and currency tags` · (4) `feat(normalize): ranges, percent and bps` · (5) `feat(normalize): placeholders never parse as zero` · (6) `feat(normalize): Hindi scale words and Devanagari digits` · (7) `feat(normalize): equality with stated-precision tolerance` · (8) `test(normalize): hypothesis round-trip` · (9) `feat(normalize): fiscal-period parsing` · (10) `docs(explained): C3 normalization`.

### P1.5 Training corpus — [CC→AKSHAT] · S · `data/p1.5-corpus` · "P1.5 Training corpus from the IPO dataset"
- **Files:** `ingest/corpus.py` (RHP-derived pagewise text → `data/processed/corpus/<ipo_id>.json`, section-tagged with the P1.2 detector adapted to text), `ingest/exclusion.py`, `data/gold/excluded_ipos.txt`, `eval_results/corpus_stats.json`, `tests/ingest/test_exclusion.py` (no demo or gold-v2 overlap).
- **Done:** ≥ 150 corpus IPOs (target ≥ 300). Plan B (`05` §1.3) only if the recon ADR says text is unusable.
- **Commits:** (1) `feat(ingest): read RHP-derived texts from the dataset zip` · (2) `feat(ingest): section-tag corpus text` · (3) `feat(ingest): fuzzy exclusion of demo and gold IPOs` · (4) `test(ingest): assert no overlap with excluded list` · (5) `eval(ingest): corpus statistics`.

### P1.6 Buffer and G1 review — [CC] · S · `chore/p1.6-g1` · tag `v0.1.0`
Fix parser problems from Akshat's eye-check; update `10` Part C; run Prompt 5 for G1; tag and release.

### P1.7 Gold v1 labelling (new) — [AKSHAT] with [CC] tooling · S · `data/p1.7-gold-v1` · "P1.7 Gold v1 tooling and labelling"
- **Files:** `evaluate/gold.py` (schema + validator for `gold_values.jsonl`), `scripts/gold_template.py` (writes an empty per-IPO template — no values), `data/gold/gold_values.jsonl` (Akshat), `tests/evaluate/test_gold.py`.
- **Rule:** blind labelling from the PDFs before any extractor output exists; first authoritative occurrence with **PDF page**; fields per ADR-023: fresh amount, OFS shares, OFS amount, offer price (Prospectus), price band (if stated), face value, BRLMs, registrar, promoters, objects of the offer.
- **Commits:** (1) `feat(evaluate): gold value schema and validator` · (2) `test(evaluate): gold validator cases` · (3) `feat(evaluate): per-IPO gold template generator` · (4) `data: gold v1 values for 10 IPOs` (Akshat's labels; committed by CC after validation).

---

## Phase 2 — Extraction and our model → G2

### P2.1 Field registry + rules (Rung 1) — [CC] · S · `feat/p2.1-rules` · "P2.1 Field registry and rules extractor"
- **Files:** `configs/fields.yaml` (fields per ADR-023, EN/HI labels, doc type, sections, questions, extractor, fallback, `ladder: true|false`; `offer_price`, `price_band` and `objects_of_offer` are `ladder: false`), `extract/{fields,rules}.py`, `data/samples/*` sentence samples, `tests/extract/*`.
- **`offer_price` (review decision):** rules-only, read from the Prospectus cover; `ladder: false` because RHP training texts contain `[●]` for it, so there are no positives to learn from. Same treatment as `objects_of_offer`.
- **Gold v1 findings:** `price_band` is `[●]` in all 10 RHPs (expect `placeholder`). `total_issue_size` and `ofs_amount` are stated in the RHP for HDB, Hexaware, PhysicsWallah and Urban Company and blank for the other six: handle both. Tata Capital `fresh_issue_size` is a placeholder in the RHP (shares only): test case.
- **Tuning discipline:** rules are developed and checked against the 3 **dev** IPOs only; test IPOs are first scored in P2.6.
- **Commits:** (1) `feat(extract): field registry loader` · (2) `test(extract): cover-page sentences for fresh issue and OFS shares` · (3) `feat(extract): rules for fresh issue, OFS shares, offer price` · (4) `feat(extract): rules for face value, BRLMs, registrar` · (5) `feat(extract): promoter rules` · (6) `test(extract): placeholder handling` · (7) `docs(explained): C4 rules`.

### P2.2 Pretrained QA + X-Ray v0 — [CC] · S · `feat/p2.2-qa-pretrained` · "P2.2 Pretrained QA and X-Ray v0"
- **Files:** `extract/qa_pretrained.py`, `extract/select.py`, `extract/xray.py`, `verify/consistency.py`, `tests/extract/*`, `tests/verify/test_consistency.py`. Consistency: fresh + OFS amount ≈ total *when all present*; derived percentages "at offer price" from Prospectus values; placeholder → ⚠️ with `placeholder` reason.
- **Commits:** (1) `feat(extract): section-restricted passage builder` · (2) `feat(extract): pretrained QA extractor on GPU fp16` · (3) `feat(extract): candidate selection with disagreement handling` · (4) `feat(verify): consistency checks` · (5) `feat(extract): X-Ray builder` · (6) `feat(pipeline): xray stage for all demo IPOs` · (7) `test(extract): selection and X-Ray golden fixture`.

### P2.3 ★ Weak labelling — [CC] · O · `feat/p2.3-weaklabel` · "P2.3 Distant supervision pipeline"
- **Files:** `weaklabel/{seeds,propagate,negatives,build_squad,audit}.py`, `eval_results/weaklabel_stats.json`, `data/gold/weaklabel_audit.jsonl` (50 stratified). Seeds cross-checked against the dataset Excel columns (fresh/OFS/total/price/face value) where they exist.
- **Field handling (B4):** numeric fields propagate by `normalize.equal`; names by normalized fuzzy match; lists get one span covering the list; `objects_of_offer` and `offer_price` are excluded from QA training (table extractor / Prospectus rules only).
- **Tests:** seed unambiguity, propagation filters, negatives ratio, SQuAD 2.0 schema, split by IPO with seed 2026, no demo/gold IPO in output.
- **Commits:** (1) `test(weaklabel): seed unambiguity cases` · (2) `feat(weaklabel): high-precision seed extraction` · (3) `feat(weaklabel): propagate seeds by normalized value` · (4) `feat(weaklabel): fuzzy name propagation` · (5) `feat(weaklabel): negatives` · (6) `feat(weaklabel): SQuAD 2.0 export with IPO-level split` · (7) `feat(weaklabel): stratified audit sampler` · (8) `test(weaklabel): leakage assertions` · (9) `docs(explained): C6 weak labelling`.

### P2.4 Audit + fine-tune notebook — [CC→AKSHAT] · S · `feat/p2.4-finetune-nb`
- **Files:** `notebooks/01_finetune_extractor.ipynb` (params, seeds 13/42/2026, checkpoint + resume, fp32 fallback, `metrics.json`), `evaluate/metrics.py` (EM, F1, NVM, list-F1, bootstrap CI), `scripts/package_kaggle_dataset.py`, `tests/evaluate/test_metrics.py`.
- **Akshat:** audit 50 labels (~1 h) → E1.
- **Commits:** (1) `test(evaluate): EM, F1 and NVM cases` · (2) `feat(evaluate): metrics with bootstrap intervals` · (3) `feat(notebooks): fine-tune notebook with resume` · (4) `feat(weaklabel): Kaggle dataset packager` · (5) `docs: Kaggle run instructions`.

### P2.5 Training runs — [AKSHAT]
3 seeds on Kaggle; weights to `models/extractor/`; metrics JSON committed; ablations E4 if quota allows.

### P2.6 Fine-tuned extractor + ladder — [CC] · S · `feat/p2.6-ladder`
- **Files:** `extract/qa_finetuned.py`, `evaluate/{ladder,run_gold}.py`, `eval_results/ladder_table.{csv,json,tex}`, ADR-018 (extractor per field, chosen on **dev**, reported on **test**), `tests/evaluate/*`.
- **Reporting (C2, C3):** headline = overall NVM + bootstrap CI + paired difference; settings **full-document** and **body-only**; per-field table labelled descriptive; `n` printed.
- **Commits:** (1) `feat(extract): fine-tuned QA extractor` · (2) `feat(evaluate): gold runner for all rungs` · (3) `feat(evaluate): body-only setting with cover masked` · (4) `feat(evaluate): ladder table builder` · (5) `eval: E2 and E3 results on gold v1` · (6) `docs(decisions): ADR-018 extractor per field` · (7) `feat(pipeline): rebuild X-Rays with chosen extractors`.

### P2.7 Buffer and G2 review — [CC] · S · tag `v0.2.0`
Update `10` Parts C4–C6 and B-section touch-ups; Prompt 5 for G2.

---

## Phase 3 — Trustworthy chat → G3

### P3.1 Retrieval — [CC] · S · `feat/p3.1-retrieval`
- **Files:** `retrieve/{chunk,bm25,dense,fuse,rerank,retriever}.py`, `scripts/measure_memory.py`, `eval_results/retrieval.json`, ADR-019, `tests/retrieve/*`. Chunks keep `doc_type`; tables never split.
- **Measure:** RAM/VRAM in `full` with Ollama running (D6). Abstain threshold tuned on **dev** questions only.
- **Commits:** (1) `feat(retrieve): chunker that never splits tables` · (2) `feat(retrieve): bm25s index` · (3) `feat(retrieve): bge-m3 dense index (offline GPU, online ONNX int8)` · (4) `feat(retrieve): reciprocal rank fusion` · (5) `feat(retrieve): reranker with BM25-only fallback` · (6) `eval(retrieve): E6 on dev questions` · (7) `docs(decisions): ADR-019 measured memory`.

### P3.2 Generation + LLM bake-off — [CC→AKSHAT] · S · `feat/p3.2-generate`
- **Files:** `generate/{llm_backend,prompts}.py` (EN + HI, thinking disabled), `generate/__main__.py` (`python -m finsight.generate ask`), `scripts/llm_bakeoff.py`, ADR-020, `tests/generate/test_injection.py`.
- **Commits:** (1) `feat(generate): Ollama backend with streaming` · (2) `feat(generate): grounded EN and HI prompts` · (3) `test(generate): adversarial-chunk injection test` · (4) `feat(generate): ask CLI` · (5) `eval(generate): bake-off script` · (6) `docs(decisions): ADR-020 LLM choice`.

### P3.3 ★ Verifier + seeded errors — [CC] · O · `feat/p3.3-verifier`
- **Files:** `verify/{claims,numeric_check,verdict}.py`, `evaluate/seeded_errors.py`, `eval_results/verifier.json`, `tests/verify/*`. Scale rule per ADR-027; reason codes verified / scale_mismatch / wrong_value / wrong_metric / not_found / placeholder; Hindi answers verified through the same path.
- **Commits:** (1) `test(verify): one table per reason code` · (2) `feat(verify): claim splitter skipping years and citations` · (3) `feat(verify): metric keyword map` · (4) `feat(verify): equal-value and scale-mismatch rules` · (5) `feat(verify): wrong-metric and placeholder rules` · (6) `feat(verify): answer score` · (7) `feat(evaluate): seeded-error harness` · (8) `eval(verify): E5 unit benchmark` · (9) `docs(explained): C9 verifier`.

### P3.4 Advice guard — [CC] · S · `feat/p3.4-guard`
- **Files:** `guard/advice.py` (keyword/regex EN/HI/Hinglish + facts payload), `data/gold/advice_set.jsonl` (Akshat's ≥ 50 + ≥ 50 in, mine kept separate), `eval_results/guard.json`, `tests/guard/*`. Refusal copy says "Here's what the prospectus says" (no nudge to decide).
- **Commits:** (1) `test(guard): advice and factual cases in EN, HI, Hinglish` · (2) `feat(guard): keyword and regex advice detector` · (3) `feat(guard): facts payload from X-Ray` · (4) `eval(guard): E8 keyword row on Akshat's set`.

### P3.5 Voice — [CC→AKSHAT] · S · `feat/p3.5-voice`
- **Files:** `voice/{asr,manager}.py` (lazy load, unload after 120 s idle), `scripts/asr_bakeoff.py`, `eval_results/asr.json`, ADR-021, `tests/voice/*`. Akshat records 10 Hindi questions (`data/raw/audio/`, local) and one demo clip (`frontend/public/demo/`, committed).
- **Commits:** (1) `feat(voice): ASR protocol and faster-whisper backend` · (2) `feat(voice): lazy load and idle unload` · (3) `eval(voice): CER and latency bake-off` · (4) `docs(decisions): ADR-021 ASR choice`.

### P3.6 Chat orchestrator + traces — [CC] · S · `feat/p3.6-chat`
- **Files:** `chat/{orchestrator,traces,__main__}.py` (event order per 06; `python -m finsight.chat ask`), `evaluate/answers.py` (E7 + verifier on real LLM answers with hand-checked sample), `tests/chat/*`.
- **Commits:** (1) `feat(chat): orchestrator emitting contract events` · (2) `feat(chat): trace store in SQLite` · (3) `feat(chat): abstain and advice short-circuits` · (4) `feat(chat): ask CLI` · (5) `eval(chat): E7 answer quality` · (6) `docs(explained): C12 chat`.

### P4.1 API — [CC] · S · `feat/p4.1-api` · tag `v0.3.0` after G3 review
- **Files:** fill in every route from the P0.3 skeleton, ModelManager + `/health`, demo cache + `poe record-demo`, `configs/suggested_questions.yaml`, glossary endpoint, lab endpoints reading `eval_results/`, contract tests.
- **Commits:** (1) `feat(api): ipo list, detail, xray and page images` · (2) `feat(api): page words endpoint` · (3) `feat(api): chat SSE endpoint` · (4) `feat(api): voice endpoint` · (5) `feat(api): traces and lab endpoints` · (6) `feat(api): ModelManager and health` · (7) `feat(api): demo cache recorder and replay` · (8) `test(api): contract tests against models` · (9) `feat(api): suggested questions from X-Ray`.

---

## Frontend track (mocks until F6) — model S throughout

Each F sub-phase: issue "Fn <title>", branch as in `07`, commits below, verify with `pnpm lint && pnpm typecheck && pnpm test && pnpm build`, and Akshat reviews 10 min in the browser.

| ID | Files | Planned commits |
|---|---|---|
| **F1** scaffold | `frontend/` Next.js + Tailwind tokens + fonts + shadcn + Zustand + TanStack Query + MSW, `frontend/CLAUDE.md`, `lib/api/types.ts` **generated from committed `openapi.json`**, AppShell, `/ipos`, `.github/workflows/frontend.yml` | `build(web): scaffold Next.js with strict TypeScript` · `feat(web): design tokens and IBM Plex fonts` · `feat(web): store and query providers` · `feat(web): MSW fixtures from schemas` · `feat(web): app shell and library page` · `ci(web): frontend workflow` |
| **F2** viewer | `PageViewer`, `HighlightLayer`, `ThumbnailStrip`, `SectionJumpList`, workspace layout | `feat(web): resizable workspace layout` · `feat(web): page viewer with prefetch` · `feat(web): highlight layer` · `feat(web): thumbnails and section jump` · `test(web): highlight latency budget` |
| **F3** X-Ray | `XRayPanel`, `FactRow`, `FactPopover`, `VerdictMark`, `UnitToggle`, charts, `lib/format.ts` | `test(web): Indian formatting cases` · `feat(web): format helpers` · `feat(web): X-Ray panel and fact rows` · `feat(web): verdict marks` · `feat(web): unit toggle` · `feat(web): composition and proceeds charts` · `feat(web): extractor compare` |
| **F4** chat | `lib/sse.ts`, `ChatPanel`, reveal, `EvidenceDrawer`, cards | `test(web): SSE parser` · `feat(web): SSE client` · `feat(web): chat panel and stage line` · `feat(web): citation chips` · `feat(web): tick-and-tie reveal` · `feat(web): evidence drawer` · `feat(web): abstain and advice cards` |
| **F5** voice + inspector | `MicButton`, `lib/i18n.ts`, `InspectorDrawer`, `GlossaryDrawer` | `feat(web): i18n dictionary and language toggle` · `feat(web): mic recorder` · `feat(web): inspector drawer` · `feat(web): glossary drawer` |
| **F6** integration | regenerate types, switch off mocks, `ColdStartBanner`, `HealthDot` | `build(web): regenerate API types` · `fix(web): contract mismatches found on real API` · `feat(web): health dot and warm-up banner` |
| **F7** lab + landing | `/lab`, `/`, `/how-it-works` | `feat(web): ladder table and chart` · `feat(web): field heatmap` · `feat(web): verifier and weak-label panels` · `feat(web): landing page from eval results` · `feat(web): how-it-works diagram` |
| **F8** demo mode | `DemoController`, hotkeys, `e2e/demo-flow.spec.ts`, `e2e.yml`, demo voice clip | `feat(web): demo controller and hotkeys` · `test(e2e): demo flow on mocks` · `test(e2e): demo flow on real API` · `ci: e2e workflow` · `fix(web): polish list from device test` → **G4**, tag `v0.4.0` |

---

## Phase 5 — Depth and rigour (cut in this order if behind)

| ID | Owner · Model | Branch | Files | Planned commits |
|---|---|---|---|---|
| P5.1 Gold v2 | Akshat + CC · S | `data/p5.1-gold-v2` | `evaluate/gold_assist.py` (page hints only), `data/gold/gold_values_v2.jsonl` | `feat(evaluate): page-hint assistant` · `data: gold v2 labels` · `eval: final ladder on gold v1+v2` |
| P5.2 Frontier comparison | Akshat runs · CC scores · S | `eval/p5.2-frontier` | `data/gold/frontier_raw/`, `evaluate/frontier.py`, `eval_results/frontier.json` | `feat(evaluate): frontier answer scorer` · `feat(evaluate): run verifier on frontier answers` · `eval: E9 results with conditions` |
| P5.3 BiLSTM-CRF | CC→Akshat · S | `feat/p5.3-bilstm-crf` | `extract/bilstm_crf.py`, `notebooks/02_bilstm_crf.ipynb` | `feat(weaklabel): BIO conversion` · `feat(notebooks): BiLSTM-CRF notebook` · `feat(extract): BiLSTM-CRF extractor` · `eval: E11` |
| P5.4 Advice classifier | CC→Akshat · S | `feat/p5.4-guard-clf` | `guard/clf.py`, `notebooks/03_muril_guard.ipynb` | `feat(notebooks): MuRIL guard notebook` · `feat(guard): classifier backend via config` · `eval: E8 classifier row` |
| P5.5 NLI text check | CC · S | `feat/p5.5-nli` | `verify/nli.py` | `feat(verify): NLI check for non-numeric claims` · `test(verify): NLI cases` · `feat(core): profile switch` |
| P5.6 Glossary | CC drafts, Akshat reviews HI · S | `feat/p5.6-glossary` | `configs/glossary.{en,hi}.yaml` | `docs: glossary drafts` · `docs: Hindi review fixes` |
| P5.7 Latency | CC · S | `eval/p5.7-latency` | `scripts/benchmark.py`, `eval_results/latency.json` | `feat(evaluate): stage benchmark` · `eval: E10 both profiles` |

## Phase 6 — Deploy and harden → G5

| ID | Owner · Model | Branch | Files | Planned commits |
|---|---|---|---|---|
| P6.1 Backend deploy | CC + Akshat clicks · S | `feat/p6.1-deploy-api` | `Dockerfile` (CPU, no torch), `scripts/bundle_artifacts.py`, `deploy/space/*`, llama-cpp backend, ADR-022 | `build: CPU Dockerfile` · `feat(generate): llama-cpp backend` · `feat(pipeline): artifact bundle` · `docs(decisions): ADR-022` |
| P6.2 Frontend deploy | CC + Akshat · S | `feat/p6.2-deploy-web` | Vercel config, env, slow-public-demo note | `build(web): production config` · `feat(web): public demo notice` |
| P6.3 Hardening | CC · S | `fix/p6.3-hardening` | rate limits, 404/500 pages, README with GIFs and results table | `feat(api): rate limits` · `fix(web): error copy` · `docs: README with results` → tag `v1.0.0-rc.1` |

## Phase 7 — Report, slides, viva (no new features)
`docs/p7-report`, `docs/p7-readme`, `fix/*` only. Freeze `eval_results/`, regenerate tables and figures by script, clean-clone reproducibility check ([CC], S); report drafted by CC and rewritten by Akshat; slides and backup video ([AKSHAT]); tag `v1.0.0` with report PDF attached.

---

## Hand-work list for Akshat (needed-by is when the next CC step would otherwise stall)

| Needed by | Task | Blocks |
|---|---|---|
| Now | Finish P0.1: pnpm, Ollama + GPU test, RAM and `nvidia-smi` into `PROGRESS.md`; say "P0.1 done" | P0.2 CI parity, F1 |
| Approve this PR | Confirm dev/test split (proposed above) after P0.4 recon | P2.1 |
| Before P1.1 review | Run parse on all 20 documents; eyeball 3; paste problems | P1.2 |
| Sat 3 Oct | Test one full-RHP upload to Claude/ChatGPT/Gemini: is it truncated? | P5.2 design |
| Mon 5 Oct | **Gold v1 labelling** (blind, ~3 h) into `data/gold/gold_values.jsonl` | P2.1 rules review, P2.6 |
| Sat 10 Oct | Optional: add 2 pure-fresh IPOs (RHP + Prospectus) to `data/raw/` and tell CC; download 10 more IPOs for gold v2 (2025–26, RHP + Prospectus each) | P5.1 |
| Sat 10 Oct | Audit 50 weak labels (~1 h) | P2.4 → E1 |
| Sun 11 Oct | Write advice + factual question set (≥ 50 + ≥ 50, EN/HI/Hinglish) with friends | P3.4 |
| Sun 11 Oct | Kaggle: upload dataset, run 3 seeds, download weights, commit metrics | P2.6 |
| Wed 14 Oct | Write dev (~20) and test (~60) questions; 30 % Hindi | P3.1 |
| Fri 16 Oct | Judge Hindi fluency 1–5 in the LLM bake-off | ADR-020 |
| Sun 18 Oct | Record 10 Hindi questions + the demo clip | P3.5, F8 |
| Each F sub-phase | 10 minutes in the browser; file issues | next F |
| Thu 22 Oct | Review every Hindi UI string and glossary entry | F7, freeze |
| Fri 23 Oct | Phone and laptop device test | F8 polish |
| Sat 24 Oct | Create Vercel and Hugging Face Space accounts; do the deploy clicks | P6.1/P6.2 |
| Tue 27 Oct → Sun 1 Nov | Own the report, slides, video, viva prep, submit | Phase 7 |

## STEP 4 checklist (after approval)
Labels from `08` §6; issues for every Phase 0 and Phase 1 sub-phase (including P1.7); `.github/pull_request_template.md` ships with P0.2; branch protection on `main` (required CI check, linear history, no force-push); merge this PR with `--rebase`.
