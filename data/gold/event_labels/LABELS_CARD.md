# L2 Event Classification Dataset Card (`data/gold/event_labels/`)

Generated deterministically by `ml/l2_build_event_labels.py` (Task **AR-03**, for **M3 Event Classifier** and **M4 Severity v2** severe-band augmentation).

## 1. Summary & Split Integrity
- **Total sentences:** **1007** across **275 unique IPOs** (target: ~800 sentences, ≥150 per class, ≥60 IPOs).
- **Zero-leakage guarantee:** `train.jsonl` (416 rows, 113 IPOs) and `dev.jsonl` (194 rows, 52 IPOs) contain **0 IPOs** from `ml/handoff/data/excluded_ipos.json` (verified by `tests/ml/test_no_leakage.py`, including filtering out the 18 rows in `serious_finding_hits.jsonl.gz` that had `slice="dev"` with `excluded=true`).
- **Test set alignment (`test.jsonl`):** 397 rows across 110 test-slice IPOs, 100% drawn from `serious_finding_hits.jsonl.gz` (`hit*` IDs) so CC's baseline (`rules_decision`) evaluates on the exact same items.
- **Provenance:** Every row carries `label_source: "ai"`, `page`, and an exact substring `evidence_quote` (≤ 25 words).

## 2. Class Distribution by Split

| Class (`label`) | `train.jsonl` | `dev.jsonl` | `train + dev` | `test.jsonl` (eval only) | **Total** |
|---|---:|---:|---:|---:|---:|
| `actual_event` | 187 | 73 | 260 | 121 | **381** |
| `hypothetical` | 70 | 23 | 93 | 63 | **156** |
| `negated` | 70 | 71 | 141 | 94 | **235** |
| `not_relevant` | 89 | 27 | 116 | 119 | **235** |
| **Total** | **416** | **194** | **610** | **397** | **1007** |

> [!NOTE]
> **Honesty note on `actual_event` counts:** Across the entire corpus (all 2,801 `serious_finding_hits` rows + Risk Factor mining across all non-excluded `train`/`dev` RHPs), there are **381** genuine `actual_event` sentences (**260** in `train`+`dev` [187 `train`, 73 `dev`] and **121** in `test`). Per Akshat's instruction, `train`+`dev` is reported at its true natural count (260 rows) rather than padding with borderline or synthetic rows.

## 3. Distribution by Severe `check_id` and `rules_decision`

| `check_id` | Total Rows | `actual_event` Rows |
|---|---:|---:|
| `default_or_recall` | 394 | 49 |
| `regulator_order` | 373 | 139 |
| `qualified_audit` | 103 | 94 |
| `going_concern` | 96 | 89 |
| `fraud` | 41 | 10 |

| `rules_decision` | Total Rows | `actual_event` Rows | Notes |
|---|---:|---:|---|
| `fired` | 313 | 207 | All non-excluded `fired` rows audited; false positives are mostly NBFC/bank customer-default recovery suits, definitions, or covenant boilerplate |
| `blocked_soft` | 658 | 153 | **Rescued real events** blocked by `_SOFT` words (`"may"`, `"without"`, `"not"`, `"no."`) |
| `blocked_no_debt` | 16 | 1 | Statutory / non-debt rows |
| `missed_by_regex` | 20 | 20 | Mined from non-excluded `train`/`dev` Risk Factor pages |

## 4. Key Audit Findings on `serious_finding_hits.jsonl.gz`
1. **Why `fired` had false positives (`106/313` non-actual):**
   - **Ordinary-course lender/insurer litigation against customers (`not_relevant`):** In NBFCs, housing finance companies, small finance banks, and insurers (`aadhar-housing-finance-2024`, `bajaj-housing-finance-2024`, `capital-small-finance-bank-2024`, `jana-small-finance-bank-2024`, `manba-finance-2024`, `hdb-financial-services-2025`, `tata-capital-2025`, `aye-finance-2026`), sentences describing *customers/borrowers* defaulting on loans taken *from* the issuer or FIRs against third-party insurance/loan fraud triggered `default_or_recall` and `fraud`.
   - **Definitions, table headers, and covenant boilerplate (`not_relevant` / `hypothetical`):** Glossary definitions of `"Wilful Defaulter or Fraudulent Borrower"`, loan schedule table captions, and cross-default clauses without any past breach.
   - **Disposed / exonerated regulatory proceedings (`negated`):** E.g., SEBI orders in `national-securities-depository-2025` (`hit001672`–`hit001674`, `hit001678`) where proceedings were disposed of without penalty or directions.
2. **Why `blocked_soft` hid `153` real severe events (`actual_event`):**
   - **Going concern (`going_concern`):** Standard statutory auditor wording (*"indicate that a material uncertainty exists that **may** cast significant doubt on the Company's ability to continue as a going concern"* or *"Without qualifying our opinion..."*) was blocked by `"may"` or `"without"`.
   - **Loan repayment delays (`default_or_recall`):** CARO Clause ix(a) and Risk Factor disclosures (*"The Company has **not** defaulted in repayment of loans... except for the following delays"*) were blocked by `"not"`.
   - **Regulator penalty orders (`regulator_order`):** Blocked when the sentence stated *"had **not** complied with Regulation... and BSE/RBI/SEBI imposed a penalty"* or cited *"adjudication order bearing **no.** ..."* (matching `\bno\b`).
   - **Qualified/Disclaimer of audit opinions (`qualified_audit`):** Basis for Qualified Opinion paragraphs containing *"was **not** operating effectively which **could**..."* or *"did **not** observe"* were blocked by `"not"`/`"could"`.

## 5. Akshat Verification Sheet (`akshat_verification_gold.csv` & `BAND_AND_LABEL_GUIDE.md`)
- Contains **481 rows**, sorted so **all 381 `actual_event` rows come first** (`train` rows 1–187, then `dev`, then `test`), followed by **100 random rows** from `hypothetical`, `negated`, and `not_relevant` (`seed=42`).
- Includes `rhp_page` and `quote_25w` (≤ 25-word RHP quote) directly alongside `label`, `verified_label`, and `severity_band_1_to_4` so verification can be done without opening PDFs.
- `severity_band_1_to_4` is **completely blank** so pre-filled values do not bias verification; see `BAND_AND_LABEL_GUIDE.md` for band 1–4 definitions and one real example per band from the handoff pack.
