# Datasheet: training corpus

## Motivation

The extractors need many examples of how Indian offer documents state their facts, and Phase 2 needs past risk factors to compare a new document with. FinSight does not crawl SEBI or the exchanges; it uses a published research dataset (ADR-016).

## Composition

One JSON text per IPO (`data/processed/corpus/<ipo_id>.json`, gitignored), pages as text with detected sections. Counts from `eval_results/corpus_stats.json`:

<!-- generated:stats start -->

- IPOs: 389 (prospectus 279, rhp 110); one text per IPO: true
- Median length: 450 pages
- Key sections found: 331/389
- Skipped: drhp 5, too_short 9, unknown 15

| Year | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IPOs | 17 | 48 | 27 | 9 | 3 | 5 | 20 | 24 | 35 | 22 | 15 | 12 | 61 | 37 | 54 |

<!-- generated:stats end -->

## Collection process

- **Source:** `sohomghosh/Indian_IPO_datasets` on Hugging Face (Ghosh, Maji, Vardhan, Naskar 2024): a pagewise text zip of mainboard IPO documents and an Excel sheet of IPO details.
- **Build:** `uv run python -m finsight.ingest.corpus build` keeps RHP- and Prospectus-derived texts (judged from the cover, not the file name), drops draft (DRHP), unreadable and too-short texts, and tags sections with the Phase 1 section detector.
- **Excel columns:** only allow-listed columns are read. Outcome, listing-day and broker columns are never read when building the corpus or training. The proposed B-ADR-03 would let one evaluation script (`evaluate/outcomes.py`, E21) read them to check the risk level, never to train or tune anything.

## Preprocessing and exclusions

The demo IPOs (`configs/demo_ipos.yaml`) and the gold-set IPOs (`data/gold/excluded_ipos.txt`) are removed, so no model trains on a document it is scored on.

## Uses

- **Use it for:** weak labels for the extractors, the risk-factor training pool for the teacher, the risk bank used for "unusual" risks, and the past-IPO reference values of the risk level and Compare tab.
- **Never:** to predict listing gains, returns or ratings, or to rank IPOs.

## Distribution and licence

CC BY-NC-SA 4.0 (non-commercial, share-alike). The corpus is never committed or redistributed by FinSight; anyone rebuilding it downloads it from the source. Models trained on it inherit the non-commercial terms (see `NOTICE`).

## Maintenance

Rebuilt only when the source dataset or the exclusion list changes; `corpus_stats.json` is regenerated with it.
