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
