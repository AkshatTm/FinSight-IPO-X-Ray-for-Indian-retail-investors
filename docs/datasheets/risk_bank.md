# Datasheet: risk bank

## Motivation

To say how unusual a risk factor is, FinSight compares it with the risk factors of past IPOs. The bank holds those past risks as vectors. It also feeds the teacher's input (C2.3) and the classifier's train/dev data.

## Composition

Built by `scripts/build_risk_bank.py` from the frozen split (`configs/splits.yaml`):

- `data/processed/bank/risk_bank.parquet` (gitignored): one row per risk of every **train** and **dev** IPO — `risk_id`, `company`, `year`, `title`, `embedding` (bge-m3 on the title and the first two sentences), `ipo_id`, `doc_date`, `split`.
- `data/processed/bank/risk_eval.parquet` (gitignored): the same for **test** IPOs. Used only when evaluating; never read by training code.
- Committed manifests `data/manifests/risk_bank.json` (kind `train`), `risk_eval.json` (kind `eval`) and `risk_bank_product.json` (kind `product_reference`). The leakage test checks them without reading any data.

Segmentation counts and the automatic checks (E13) are in `eval_results/b/segmentation.json`; the hand-checked boundaries (E13b) are pending Akshat's spot-check.

## How novelty reads the bank

Novelty of a risk = the share of distinct past companies, inside the **rolling 4-year window** before the document (`configs/reference.yaml`, `finsight.splits.reference_bank`), with a similar risk. Evaluation windows contain train and dev IPOs only; the product window contains every collected IPO. The issuer itself is always left out.

## Real build

29,677 risk rows from 440 train + dev IPOs (`risks_by_year` in `eval_results/b/segmentation.json`); 8,819 eval rows from 110 test IPOs. 114 split IPOs have no document (mostly 2009–2013 filings and a few later ones) and are skipped. 20 documents segmented into fewer than 10 risks (for example angel-one-2020, devyani-international-2021, inox-india-2023); they stay in the bank as they are and are listed for the spot-check.

Teacher input (`data/processed/teacher/risks.jsonl`, gitignored; manifest `data/manifests/teacher_input.json`): 25,330 candidates from train IPOs, **8,889 achievable** under the 25-per-company cap, below the 12,000 target. Dropped: 13,099 over the company cap, 3,189 too long, 117 too short, 36 duplicate titles. Only 400 rows are from 2025, so the 2024+ weighting is thin.

## Known limits

- Corpus documents (2009–2023) are page text without fonts. They are split by risk numbers, which fail on a few layouts (about 3 of 20 sampled excerpts gave fewer than 10 risks). Documents that give no risks are listed in the build output and the E13 file.
- Embeddings are of the title and the first two sentences only, so two risks with the same heading but different bodies look alike.
- The bank is not a record of what happened to those IPOs; it only records what they disclosed.
