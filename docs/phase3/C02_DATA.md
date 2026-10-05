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
- **Size check:** ~10–30 MB per document; the laptop needs a few GB free. The script stops and asks if free disk is below 10 GB.
- If a source blocks scripted downloads, the script prints the list of URLs and Akshat downloads those by hand into the same folder (the pipeline does not care how the file arrived).

## 4. The time split (C1.4, C-ADR-02)

All new documents are sorted by `doc_date` and assigned once, then frozen in `configs/splits.yaml`:

| Slice | What | Used for |
|---|---|---|
| `train` | Corpus 2009–2023 + the oldest ~70 % of new documents | Teacher input, classifier/student training, weak labels, risk bank |
| `dev` | Next ~10 % + the 3 dev showcase IPOs (hexaware, ather, urban-company) | Tuning, thresholds, error analysis, bake-offs |
| `test` | Next ~20 % + the 7 test showcase IPOs | Final numbers (E-experiments) |
| `bench` | A fixed subset of `test` (C04 §2) | FinSight Bench vs frontier models |
| `demo` | The newest few IPOs (subset of `test`) | Class presentation, landing page |

Rules:
- A showcase IPO keeps its B04 role (dev or test) whatever its date.
- Split is by **IPO**, never by passage or risk.
- **Leakage test** `tests/test_split_leakage.py`: no `test`/`bench` IPO appears in any training file, the risk bank parquet, teacher input, weak-label files, `configs/risklevel.yaml` reference, or `configs/compare.yaml` reference. It runs in `poe test` against the committed manifests (each training artefact writes a manifest of IPO ids).
- Percentages are defaults; C1.4 prints the resulting counts and Akshat confirms before freezing.
- Once frozen, the split changes only by a new C-ADR (e.g. a document that turns out to be broken moves to `excluded`).

## 5. Rolling reference window (C-ADR-03)

Anything that says "compared with past IPOs" (novelty, percentiles, risk-level thresholds, Compare tab) uses only IPOs whose `doc_date` is **before** the document being analysed, within the last **4 years** (`configs/reference.yaml: window_years: 4`). For a 2026 IPO that means roughly 2022–2025.

- No look-ahead: a test IPO is never compared with an IPO filed after it.
- For an upload, the window is "the last 4 years before today" over `train` + `dev` + `test` IPOs **that are not the upload itself** (in the product, all collected IPOs are history).
- For evaluation, the window is computed **as of each test IPO's date** and excludes all other test/bench IPOs (stricter than the product; documented).
- This replaces the fixed "2018–2023 reference" of B02 §7 and B04 §1 for new documents. E21 (outcome validation) still uses the corpus years where listing outcomes exist.

## 6. Parsing everything (C1.3)

Every downloaded document goes through the existing upload stages (`validated → parsed → sections → risks_split`) in a batch script (`scripts/batch_parse.py`, one document at a time, resumable, Ollama off). This **is** the old B1.1b hardening and E23 robustness test, at scale:

- Record per document: doc type detected, pages, stage timings, sections found, risks found, failures with reason → `eval_results/c/parse_batch.json`.
- Fix the parser for repeated failures with a regression test (fixture-pack based; `scripts/export_fixtures.py` may add a few new pages within the 20 MB cap).
- Documents that still fail go to `excluded` with the reason; they are reported, not hidden.

## 7. Old corpus upgrade (optional, C1.5)

The BIR spreadsheet lists a PDF link per IPO for far more IPOs than we have text for. A small script checks how many links still download (`eval_results/c/bir_links.json`). Akshat decides whether to backfill 2018–2023 PDFs (gives font cues for better risk splitting of old IPOs). Low priority: Akshat cares about new IPOs.

## 8. New gold data (summary; details in C04 §3 and C06)

| Set | Docs | Purpose |
|---|---|---|
| gold v3 (existing template) | 10 showcase | Red-flag inputs (E14/E15) |
| gold v4 (bench facts) | bench IPOs not in gold v3 | Bench facts and red flags |
| bench questions + answers | bench IPOs | Risk Q&A task |
| bench rewrite set | 10 risks × bench IPOs | Blind rewrite rating |
| teacher bake-off sheet | 100 risks (dev/train) | Choose the teacher |
| quality-100, gold-150, gold-50, novelty-60 | as in B04 | As in B04, now drawn with the time split |

## 9. Licences and ethics

- Offer documents are public regulatory filings; we store them locally and never redistribute them.
- BIR corpus: CC BY-NC-SA 4.0 → models trained on it are non-commercial (model cards say so).
- Teacher (Qwen family, Apache-2.0) outputs may train the student; the chosen teacher's licence is re-checked in C2.2.
- Frontier-model answers collected for the bench are stored as evaluation data only, with the app, plan and model name recorded.
