# 4 Data and licences

> **DRAFT — Akshat to rewrite in his voice.** Numbers come from `eval_results/corpus_stats.json`,
> `weaklabel_stats.json`, ADR-016, ADR-026 and ADR-035.

## 4.1 Training corpus (weak labels)

The corpus is the public Indian IPO text collection of Ghosh et al. (Hugging Face
`sohomghosh/Indian_IPO_datasets`, CC BY-NC-SA 4.0), mainboard issues only, close years 2009 to 2023.
The text archive holds 424 files; file names are unreliable (about 170 of 219 files named `_RHP`
open with a cover titled PROSPECTUS), so each text is classified by its cover into RHP, final
Prospectus, DRHP or unknown (ADR-016). DRHPs (5) and unknown or too-short texts (24) are dropped,
leaving **389 IPOs: 110 RHP and 279 Prospectus** (median 450 pages; the four key sections were found
in 331 of 389). No IPO of the demo set is in the corpus. The dataset's Apply/Avoid ratings and
listing-gain targets are never read (ADR-005).

Weak labels (v2) come from seeds read off the cover and cross-checked against the Excel columns, then
propagated by normalised value match. Seed coverage per field ranges from 96 of 389 (OFS amount) to
255 of 389 (face value); most dropped seeds are `no_match` (the Excel value does not occur in the
text) or `excel_disagrees` (`eval_results/weaklabel_stats.json`). The result is 1,818 positive and 2,720
negative examples (train 272 IPOs, dev 30; ADR-041).

## 4.2 Demo set and gold

Ten 2025 IPOs, each with its RHP and its final Prospectus (ADR-023): Ather Energy, Groww, HDB
Financial Services, Hexaware Technologies, Lenskart, LG Electronics India, Meesho, PhysicsWallah, Tata
Capital, Urban Company. **Dev** = Ather, Hexaware, Urban Company (rules and thresholds are tuned on
these); **test** = the other seven (ADR-026). Gold v1 is 110 values (11 fields × 10 IPOs); the extractor
ladder scores the eight ladder fields (80 rows: dev 24, test 56) in the full-document and
body-only settings.

**Gold provenance.** The gold values were pre-filled by Claude (chat) from the PDFs and checked by the
author (`label_source = ai_assisted_verified`, ADR-035); hand corrections are not recorded. The 50-row
weak-label audit, the dev and test question sets (50 and 67 questions, English and Hindi) and the
advice-guard set (60 advice and 60 factual questions) were also drafted by Claude chat. The guard set
has not been reviewed by the author. These are disclosed in §7 and §9.

## 4.3 Licences

Code is MIT. The weak-label corpus is CC BY-NC-SA 4.0, so the fine-tuned weights inherit
non-commercial share-alike terms and are not published; the repository holds code, configs, results and
truncated sample excerpts only. RHPs and Prospectuses are public regulatory filings (SEBI, stock
exchanges); the PDFs are not redistributed. Base models keep their own licences
(`docs/04_TECH_STACK_AND_RESOURCES.md` §4; `NOTICE`).

## 4.4 Phase 2 data (uploads and risk factors)

> Sources: `docs/phase2/B04_DATA_AND_EVALUATION.md`, B-ADR-03, B-ADR-11, the datasheets in `docs/datasheets/`
> and `docs/phase2/datasheets/teacher_outputs.md`. **Status:** the code that builds each set is written and
> tested on synthetic inputs; the sets themselves are built in local sessions. No count below is final until
> its file exists.

- **Risk bank.** Risk factors segmented from the corpus, with company, year, title, body and a bge-m3
  embedding of the title and first two sentences (`risks.bank`). Novelty is computed only against the
  **2018–2023** part, so that newer disclosure styles are not called "unusual" just for being new, and the
  issuer's own past documents are excluded (B02 §7.1).
- **Teacher outputs.** About 5,000 corpus risks labelled by an open-weight teacher (`Qwen/Qwen3-14B-AWQ`
  on vLLM, Kaggle) with a category (10 classes), a seriousness rating (1–5), a hard-fact flag and a
  plain-English rewrite. Eight deterministic filters drop bad rows and log why. Every row carries
  `label_source = teacher:<model>:<prompt_version>`. These labels train the category classifier and the
  simplifier student; they are **never** used as evaluation ground truth.
- **Phase 2 gold.** All drawn from the ten showcase IPOs (never from training data):
  red-flag inputs (gold v3: 270 rows, 27 per IPO; the template is committed and not yet filled),
  risk segmentation boundaries, 150 risks with categories (gold-150) and 50 risks for rating rewrites
  (gold-50). Claude chat may pre-fill them; Akshat verifies; `label_source` and the number of values he
  changed are recorded.
- **Outcome data.** The corpus Excel has listing-day returns and broker opinions. Under the proposed
  B-ADR-03 they may be read by one evaluation script only (E21), to check that the risk level behaves
  sensibly; they are never used to train or tune anything and never shown in the product.
- **Uploads.** Documents users upload are processed for their report only, deleted after 30 days, and
  never added to any training set (`PRIVACY.md`).
