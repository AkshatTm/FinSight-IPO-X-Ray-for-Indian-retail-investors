# C02 — Data: newest IPOs, time split, no leakage

## 1. Why new data

The corpus ends in 2023; every showcase IPO is from 2025; users will upload documents from now on. Training, the risk bank and the "unusual" comparison must reflect **how offer documents are written today**. The newest IPOs are also what Akshat shows in class.

The 389 old corpus IPOs **stay in training** (free data; RHP language changes slowly). They are not shown in the product, and they stop being the comparison baseline for new IPOs (§5).

## 2. What to collect

- **Scope:** every **mainboard** IPO offer document (RHP; the final Prospectus where the RHP is missing) from **2024 to the latest listing available** when C1.1 runs. SME excluded (C-ADR-09).
- **Universe file:** `configs/ipo_universe.csv` (committed, metadata only):
  `ipo_id, company, exchange, doc_type, doc_date, listing_date, source_url, sha256, pages, status, split`.
  `status` ∈ `listed | downloaded | parsed | failed | excluded` with a `reason` column.
- **Count first.** C1.1 builds the list and prints the count before anything is downloaded. Akshat approves the list (and can drop companies).

## 3. Sources and downloader (C1.2, C-ADR-08)

- **Order of sources:** SEBI's public filings pages (RHPs filed with RoC; Prospectus), then the NSE/BSE issue pages, then the company / lead-manager site. Official sources only.
- **`scripts/fetch_offer_docs.py`:** reads the universe file, downloads to `data/raw/offer_docs/<ipo_id>.pdf`, one request every few seconds, honest User-Agent, resume, sha256 recorded, never retries a 4xx more than twice, writes `status`. No browser automation unless a source requires it, and then only after Akshat says so.
- **Never** commit, re-host or publish the PDFs. Only metadata is committed.
- **Sources with bot protection** (NSE/BSE) are not scraped around; their rows go on the manual-download list.
- **Multi-part filings** (one offer document published as several PDFs) are merged in page order into one file with each part's sha256 recorded, or marked `excluded` with the reason.
- **Size check:** ~10–30 MB per document (about 2.5–7.5 GB for ~250 documents) plus parsed outputs of unknown size (C1.3 records bytes per document). The script stops and asks if free disk is below **15 GB** (same limit as C06).
- If a source blocks scripted downloads, the script prints the list of URLs and Akshat downloads those by hand into the same folder (the pipeline does not care how the file arrived).

## 4. The time split (C1.4, C-ADR-02)

All new documents are sorted by `doc_date` and assigned once, then frozen in `configs/splits.yaml`. The split is **strict** (C-ADR-02): every `train` document is dated before every `test` document.

| Slice | What | Used for |
| --- | --- | --- |
| `train` | Corpus 2009–2023 + every new document dated **before the earliest test-slice document** (the earliest test showcase RHP sets the cut, so roughly 2024 + early 2025) | Teacher input, classifier/student training, weak labels, risk bank |
| `dev` | The 3 dev showcase IPOs (hexaware, ather, urban-company) + about the older third of the non-showcase new documents after the cut | Tuning, thresholds, error analysis, bake-offs, bench-dev |
| `test` | The 7 test showcase IPOs + the remaining (newest) non-showcase documents | Final numbers (E-experiments) |
| `bench` | A fixed subset of `test` (C04 §2) | FinSight Bench vs frontier models |
| `demo` | The newest few IPOs (subset of `test`) | Class presentation, landing page |

Rules:

- **Showcase roles come from `configs/demo_ipos.yaml`** (`split: dev|test`, read by `ingest/registry.py`). `splits.yaml` is generated from it plus the universe; a test asserts the two agree. There is one source of truth for each showcase role.
- Split is by **IPO**, never by passage or risk. Both documents of a showcase IPO (RHP and Prospectus) share its slice.
- **Identity:** new rows use the same `ipo_slug(company, year)` as the corpus (`ingest/corpus.py`). Leakage checks match on `ipo_id` **and** on `company_key` (`risks/bank.py`), so a company that filed again or changed its name is caught.
- **Manifests:** every training or reference artefact has a committed manifest `data/manifests/<artefact>.json` (`artefact`, `kind` = `train` | `eval_reference` | `product_reference`, `ipo_ids`, artefact sha256, the script that wrote it). The export script writes it when it writes the artefact; Colab/Kaggle outputs inherit the manifest of their exported input. Artefacts themselves stay in `data/processed/` (gitignored).
- **Retro manifests:** C1.4 writes manifests for the existing Phase 1 artefacts (weak labels, extractor v1 training ids, guard data). They are corpus-only, so they pass.
- **Leakage test** `tests/test_split_leakage.py` reads only `data/manifests/` and `configs/splits.yaml` (no processed data), so it runs in `poe test`. It fails if a `test`/`bench` IPO appears in any `kind: train` manifest (training files, risk bank, teacher input, weak labels) or in the inputs used to fit thresholds (τ, risk-level `low_below`/`high_from`, `unusual_below`). `product_reference` manifests are exempt (§5) but may never be listed as a threshold-fitting input.
- C1.4 prints the resulting counts per slice and per year; Akshat confirms before freezing.
- Once frozen, the split changes only by a new C-ADR (e.g. a document that turns out to be broken moves to `excluded`).

## 5. Rolling reference window (C-ADR-03)

Anything that says "compared with past IPOs" (novelty, percentiles, risk-level percentile, Compare tab) uses only IPOs dated **before** the document being analysed, within the last **4 years** (`configs/reference.yaml: window_years: 4`). For a 2026 IPO that means roughly 2022–2025.

- **Corpus rows by close year.** The corpus has only `close_year`, no `doc_date`. A corpus IPO is in the window when its close year is in the 4 calendar years before the as-of year (it never counts as "before" a document in its own close year).
- No look-ahead: a test IPO is never compared with an IPO filed after it.
- **Two references** (C-ADR-03):
  - *eval*: computed **as of each test IPO's date** from `train` + `dev` only, excluding all test/bench IPOs. It is computed at evaluation time and never stored in `configs/`. Stricter than the product; documented.
  - *product*: for an upload, "the last 4 years before today" over all collected IPOs except the upload itself (in the product, all collected IPOs are history). It is its own artefact with a `product_reference` manifest. It is never an input to τ or threshold fitting.
- **Code shape** (wired by the parts that build each artefact, not by C1.4): the risk bank gains `ipo_id`, `doc_date` and `split` (today it has only `company`, `year`, `title`, `embedding`, and `load_bank` hard-codes 2018–2023). A per-IPO `reference_scores` table (`ipo_id`, `doc_date`, risk-level score, compare metrics) gives deciles for any as-of date on the fly. `risklevel.percentile` and `compare.percentiles` keep taking a decile list; the YAML keeps `window_years` and the fitted thresholds only.
- **Window n** (number of IPOs in the window) is reported with every percentile, per as-of date. Early-2024 documents have a window that is mostly corpus (2022–2023 = 91 IPOs).
- **Corpus limit:** the corpus is page text only, with no financial tables, so red flags and risk-level scores cannot be computed for corpus IPOs. Risk-level references therefore come from new PDFs (2024+). Novelty uses the corpus normally.
- This replaces the fixed "2018–2023 reference" of B02 §7 and B04 §1 for new documents. **E21** (outcome validation) runs on corpus years with outcomes using a **risk-points-only** variant (no red flags, because the corpus has no tables). The limitation is stated with the result.

## 6. Parsing everything (C1.3)

Every downloaded document goes through the existing upload stages (`validated → parsed → sections → risks_split`) in a batch script (`scripts/batch_parse.py`, one document at a time, resumable, Ollama off). This **is** the old B1.1b hardening and E23 robustness test, at scale:

- Record per document: doc type detected, pages, stage timings, peak RAM, output bytes, sections found, risks found, failures with reason → `eval_results/c/parse_batch.json`.
- Fix the parser for repeated failures with a regression test (fixture-pack based; `scripts/export_fixtures.py` may add a few new pages within the 20 MB cap).
- Documents that still fail go to `excluded` with the reason; they are reported, not hidden.

## 7. Old corpus upgrade (C1.5, cut)

The BIR spreadsheet lists a PDF link per IPO for far more IPOs than we have text for. A small script checks how many links still download (`eval_results/c/bir_links.json`). Akshat decides whether to backfill 2018–2023 PDFs (gives font cues for better risk splitting of old IPOs). Low priority: Akshat cares about new IPOs. **Cut** (C05 §5 cut 2); kept here for future work.

## 8. New gold data (summary; details in C04 §3 and C06)

| Set | Docs | Purpose |
| --- | --- | --- |
| gold v3 (existing template) | 10 showcase | Red-flag inputs (E14/E15) |
| gold v4 (bench facts) | bench IPOs not in gold v3 (the 4 newest 2026 bench IPOs) | Bench facts and red flags; fields = Task A ∪ every red-flag input (C04 §3) |
| bench questions + answers | bench IPOs | Risk Q&A task |
| bench rewrite set | 10 risks × bench IPOs | Blind rewrite rating |
| teacher bake-off sheet | 100 risks (dev/train) | Choose the teacher |
| quality-100, gold-150, gold-50, novelty-60 | as in B04 | As in B04, now drawn with the time split |

## 9. Licences and ethics

- Offer documents are public regulatory filings; we store them locally and never redistribute them.
- BIR corpus: CC BY-NC-SA 4.0 → teacher outputs derived from it and models trained on it are **non-commercial and ShareAlike**. HF repos stay private; model cards and datasheets say so.
- Teacher (Qwen family, Apache-2.0) outputs may train the student; the chosen teacher's licence is re-checked in C2.2.
- Frontier-model answers collected for the bench are stored as evaluation data only, with the app, plan and model name recorded.
