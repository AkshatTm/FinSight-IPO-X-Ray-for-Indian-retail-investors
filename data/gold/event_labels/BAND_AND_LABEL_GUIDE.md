# Verification & Seriousness Band Guide (`akshat_verification_gold.csv`)

Use this sidecar guide while verifying `data/gold/event_labels/akshat_verification_gold.csv`.

## 1. Columns to Fill
1. **`verified_label`**: Confirm or override `label` (`actual_event`, `hypothetical`, `negated`, `not_relevant`). Leave blank if `label` is correct (the ingestion script treats blank `verified_label` as confirming `label` and promotes `label_source` to `"human_verified_ai"`).
2. **`severity_band_1_to_4`**: **Left intentionally blank** so pre-filled values do not bias your rating. An `actual_event` is **not** automatically Band 4 (`severe`). For `train`-split rows you verify as `actual_event` (rows 1–187 at the top of the CSV), assign a seriousness band `1`, `2`, `3`, or `4` so the row can be used in **M4 (Severity v2)** training per P-3.
3. **`rhp_page` and `quote_25w`**: Placed right next to `label` so you can verify directly from the CSV without opening the PDF.

---

## 2. Seriousness Band Definitions & Handoff Pack Examples (`1` to `4`)
Per `ml/handoff/context/interfaces.md`, `ml/handoff/context/phase3_models.md`, and `ml/handoff/eval/vendor/finsight_lite/clf_metrics.py` (`SEVERE_BAND = 4`, levels 4 and 5 merged):

| Band | Label | Definition (Handoff Pack) | Real Handoff Example (`gold150.jsonl` / `classifier_dev.jsonl.gz`) |
|---:|---|---|---|
| **1** | `low` | Generic market/macro, standard offering mechanics, or boilerplate accounting/regulatory disclosures with no company-specific operational or financial harm. | **`aastha-spintex-2026#r89` (`band: 1`, `market_macro`):** *"Natural calamities could have a negative impact on the Indian economy and cause our Company's business to suffer... Prolonged spells of abnormal rainfall or other natural calamities could have a negative impact..."* |
| **2** | `medium` | Standard business/operational/sector risk (or routine arm's-length RPTs, ununionized labor, routine lease renewals) where no material adverse event or breach has occurred. | **`aastha-spintex-2026#r45` (`band: 2`, `debt_liquidity`):** *"Our lenders have created security interests over our movable and immovable properties... Although we have not experienced any material delays or defaults in repayment of our borrowings during preceding three Fiscals..."* |
| **3** | `high` | Material company-specific vulnerability or past minor/remediated compliance lapse, CARO backup/audit-trail remark, or isolated employee/third-party incident that does **not** threaten solvency, core operations, or financial integrity. | **`meesho-2025#r21` (`band: 3`, `financial`):** *"Examination report issued by our Statutory auditors discloses certain modifications... Incomplete daily backups of electronic records on India-based servers; Absence of enabled audit trail features..."* (Also `aastha-spintex-2026#r2`, `band: 3`: past non-appointment of internal auditor under Sec 138, since rectified). |
| **4** | `severe` | Severe, high-impact company-specific risk or actual material event: auditor going-concern uncertainty, substantive qualified/adverse/disclaimed audit opinion on financial statements, active/material loan default or NPA classification, major regulatory penalty/debarment/stop-operations order, wilful defaulter declaration, or large-scale financial/operational crisis. | **`vodafone-idea-2024` / `classifier_dev` (`band: 4`, `severe`):** Auditor's report containing a *Material Uncertainty Related to Going Concern* paragraph on ability to meet debt obligations, substantive *Qualified Opinion* on restated financial statements, or active loan default / regulatory debarment. |
