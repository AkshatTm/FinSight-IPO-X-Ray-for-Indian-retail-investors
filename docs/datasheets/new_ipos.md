# Datasheet: newest IPO offer documents (2024 onward) — draft

## Motivation

The corpus ends in 2023, but offer documents change and users will upload new ones. This set holds the mainboard IPO offer documents filed from 1 January 2024, used for the time split, the risk bank and the benchmark (Phase 3, C02).

## Composition

`configs/ipo_universe.csv` (metadata only, committed): one row per company with `ipo_id`, company, document type, date, source page and, later, `sha256`, `pages` and `status`. The PDFs live in `data/raw/` (gitignored) and are never committed or re-hosted.

<!-- generated:universe start -->

289 companies. Status: listed 289.

| Year | RHP | Prospectus only | Total |
| --- | --- | --- | --- |
| 2024 | 89 | 5 | 94 |
| 2025 | 94 | 4 | 98 |
| 2026 | 89 | 8 | 97 |

<!-- generated:universe end -->

## Collection process

`scripts/build_ipo_universe.py` reads SEBI's public filings pages (*Filings → Public Issues*: Red Herring Documents filed with ROC, and Final Offer Documents), one request every 3 seconds, with an honest User-Agent. It drops addenda and corrigenda, keeps the RHP for each company (the Prospectus when no RHP is listed), merges spelling variants of one name and gives the 10 showcase IPOs their existing ids. Code: `src/finsight/ingest/universe.py`.

## Known limits (stated, not hidden)

- **Dates are SEBI posting dates**, a day or two after the date on the document cover. C1.3 reads the real cover date.
- **Exchange is `both` and the listing date is empty.** SEBI does not say where an issue lists; NSE and BSE block scripted access, so those fields are not scraped around.
- **Possible SME contamination.** SEBI's pages are mainboard filings, but a few SME-looking prospectuses appear there (mostly Prospectus-only rows). C1.3 flags documents whose cover names an SME platform and excludes them with a reason (C-ADR-09).
- **An RHP is not a completed IPO.** Rows dated close to the build date may belong to issues that had not yet opened or listed.
- Coverage depends on what SEBI lists; a company whose filing is missing there is missing here.
