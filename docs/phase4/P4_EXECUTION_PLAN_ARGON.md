# Phase 4 Execution Plan — ARGON (Models & Labels)
**Owner:** Akshat · **Agent:** ARGON (Gemini 4 Argon) · **Branch:** `p4/argon` · **Budget:** 140 Colab units (102.1 planned, 37.9 reserve)

## 1. Work Order & Schedule (AR-01 .. AR-07)
| ID | Task & Deliverables | Target | Gate Alignment |
|---|---|---|---|
| **AR-01** | Read specs, write `P4_EXECUTION_PLAN_ARGON.md`, post handoff requests in `to_cc.md` | Wed 21 Oct | **P4-G0** (Wed night) |
| **AR-02** | **L1 SOD Fixtures** (`data/gold/sod_fixtures/<ipo_id>/{pages.txt,expected.json}` + `FORMAT_CATALOGUE.md` for 10 RHPs) | Wed–Thu AM | **Unblocks CC-05** (before P4-G1) |
| **AR-03** | **L2 Event Labels** (~800 rows) + **M3 Event Classifier** notebook, 3-seed run, ONNX fp32 delivery | Thu–Fri | Unblocks CC-07/09 (**P4-G2** Sat) |
| **AR-04** | **M1 Student v2**: teacher gen notebook (G4) → LoRA SFT notebook (G4) → GGUF `q4_K_M` export (`finsight-student:v2-q4`) | Thu–Fri | **P4-G1** (Fri night teacher data) |
| **AR-05** | **L3 Gold v4** (`data/gold/v4/<ipo_id>.json` + `LABELS_CARD.md`) for all 30 Platform Bench IPOs | Fri–Sat | Unblocks CC-10 (**P4-G3** Sun) |
| **AR-06** | **L4 Top-Risk Labels** (~60 train IPOs) + **M2 Salience Ranker** & **M4 Severity v2** notebooks + ONNX deliveries | Sat 24 Oct | Unblocks CC-09 (**P4-G2/G3**) |
| **AR-07** | **M5 Eval & Blind Judge**: `metrics.json` for M1–M4, `platform_bench_judge.jsonl`, `P4_MODEL_RESULTS.md` | Sun 25 Oct | **P4-G3** (Sun night) |

---

## 2. Model Plans (M1–M4) & Colab Compute Budget
All models reuse `ml/handoff/data/splits_by_ipo.json`, strictly exclude `excluded_ipos.json` (`test_no_leakage.py`), run `DEBUG=True` tiny-slice on T4 first, checkpoint each epoch to Drive with `RESUME=True`, and use pinned deps from `ml/handoff/colab/`.

### M1 — Student v2 (`ml/deliveries/m1_student/v2/`)
- **Data:** `student_v1_train.jsonl` (10,892 rows) + **2,000 unanswerable** rows (near-miss metric, wrong FY/period, wrong entity → exact app refusal `"not found in the document"`) + **1,000 answerable numeric** rows (exact number copy + `[n]` citation). Filtered via `ml/handoff/eval/` number-normalizer: drop any teacher row with a number absent from source passages. Prompt locked to `student_prompt_template.txt`.
- **Arch & Loss:** Same 4B base as Student v1 (`phase3_models.md`), QLoRA (`r=16, alpha=32, dropout=0.05`, all linear targets), token-level cross-entropy on assistant completion only. Export: merged → `q4_K_M` GGUF (`finsight-student:v2-q4`).
- **Hyper-params & Seed:** `lr=2e-4`, cosine schedule, warmup `0.03`, eff. batch `16`, `max_seq_len=2048`, `2` epochs. Seed: `[42]` (disclosed single-seed).
- **Eval, Baseline & Target:** `ml/handoff/eval/run_bench.py` (Bench v1 Task A/B/C + gold-50). Beat v1 baseline (`Task C hallucinated=0.333`, `gold-50 faithful=0.92`, `Task C answerable` in `baselines.json`) → Target: **Task C hallucinated ≤ 0.10**, **Task C answerable ≥ 0.49**, **gold-50 faithful ≥ 0.92**, **plain-English ≥ 4.5**, **post-checks ≥ 49/50**.
- **Colab & Units:** T4 debug (`1.5 u`) + G4 Teacher Gen `m1_teacher_gen.ipynb` (~4.0h = `34.8 u`) + G4 Train/Export `m1_student_train.ipynb` & `m1_export_gguf.ipynb` (~4.0h = `34.8 u`).

### M2 — Risk Salience Ranker (`ml/deliveries/m2_salience_ranker/v1/`)
- **Data:** Train on **L4** (~60 train-split IPOs, ~16k risk-bank rows: top-7 = `1.0`, RHP summary risks = `0.6`, rest = `0.0`); dev on dev-split IPOs; test on **L3** (30 Bench IPOs, zero leakage). Input: `"{company} | {sector} | {category} | {severity} | pos:{norm_pos} [SEP] {text}"`.
- **Arch & Loss:** `microsoft/deberta-v3-base` cross-encoder → scalar score, exported to ONNX fp32 (`rank_risks`, deterministic CPU ≤ 2s / 300 risks). Loss: Pairwise Margin Ranking Loss (`margin=0.2`) + BCE (`0.5/0.5` blend) sampled within each IPO.
- **Hyper-params & Seeds:** `lr=2e-5`, batch `32` (4 IPOs × 8 risks), `4` epochs, warmup `0.1`, weight decay `0.01`, `max_len=192`. Seeds: `[13, 42, 2026]`.
- **Eval, Baseline & Target:** Test on L3 (30 Bench IPOs). Beat `five_things_selection.jsonl` baseline (`baselines.json`) on **NDCG@7** and **Recall@7**, and achieve **broker_overlap@7 ≥ best single broker's overlap with the other two**.
- **Colab & Units:** T4 debug (`1.5 u`) + G4 3-seed training `m2_salience_ranker.ipynb` (~1.2h = `10.5 u`).

### M3 — Event Classifier (`ml/deliveries/m3_event_clf/v1/`)
- **Data:** **L2** (~800 sentences across ≥60 IPOs, split by `splits_by_ipo.json`, 0 `excluded_ipos.json` in train/dev). 4 classes: `actual_event`, `hypothetical`, `negated`, `not_relevant`. Input: `"{context_before} [SEP] {sentence} [SEP] {context_after}"`.
- **Arch & Loss:** `microsoft/deberta-v3-base` 4-way classifier, ONNX fp32 (`classify_events`, CPU ≤ 50ms/item). Loss: class-weighted Cross-Entropy (`actual_event` precision-calibrated threshold $\tau$ tuned on dev).
- **Hyper-params & Seeds:** `lr=2e-5`, batch `16`, `5` epochs, warmup `0.1`, weight decay `0.01`, `max_len=256`. Seeds: `[13, 42, 2026]`.
- **Eval, Baseline & Target:** `run_classifier_eval.py` on L2 test split. Beat CC-07 rules (`eval_results/p4/cc/event_rules_preds.jsonl`) on **macro-F1**, with **`actual_event` precision ≥ 0.90**, **`actual_event` recall ≥ 0.80**, and **0 false serious findings on 30 bench IPOs**.
- **Colab & Units:** T4 debug (`1.0 u`) + G4/T4 3-seed training `m3_event_clf.ipynb` (~0.4h G4 = `3.5 u`).

### M4 — Severity v2 (`ml/deliveries/m4_severity/v2/`)
- **Data:** `classifier_train/dev/test.jsonl` + train-split verified `actual_event` rows from L2 mapped to `severe` + `gold-150` train rows.
- **Arch & Loss:** `microsoft/deberta-v3-base` 4-class (`low`, `medium`, `high`, `severe`), ONNX fp32 (`predict_severity`). Loss: Focal Loss ($\gamma=2.0$) with class weight `2.5x` on `severe` + dev threshold calibration for `P(severe)`.
- **Hyper-params & Seeds:** `lr=2e-5`, batch `16`, `4` epochs, warmup `0.1`, weight decay `0.01`, `max_len=256`. Seeds: `[13, 42, 2026]`.
- **Eval, Baseline & Target:** `run_classifier_eval.py` on `classifier_test.jsonl`. Beat Severity v1 (`severe_recall=0.56`, `macro_f1=0.892`) → Target: **severe recall ≥ 0.70** with **macro-F1 ≥ 0.882** (drop ≤ 0.01).
- **Colab & Units:** T4 debug (`1.5 u`) + G4 3-seed training `m4_severity_v2.ipynb` (~1.2h = `10.5 u`).

### Compute Summary (140 Units Cap, G4 = 8.71 u/hr)
| Job | Runtime | Est. Hours | Units |
|---|---|---|---|
| All T4 `DEBUG=True` smoke runs (M1 gen, M1 train, M2, M3, M4 + M5 judge test) | T4 | ~4.0 h | **8.0** |
| M1 Teacher Generation (`m1_teacher_gen.ipynb`) | G4 | ~4.0 h | **34.8** |
| M1 Student v2 LoRA + GGUF (`m1_student_train.ipynb`, `m1_export_gguf.ipynb`) | G4 | ~4.0 h | **34.8** |
| M2 Salience Ranker (3 seeds) + M3 Event Clf (3 seeds) + M4 Severity v2 (3 seeds) | G4 | ~2.8 h | **24.5** |
| **Total Planned** | — | — | **102.1** |
| **Unallocated Reserve** (for 1 full retry of any model missing gate target) | G4 / T4 | ~4.3 h G4 | **37.9** |

---

## 3. Label Sets (L1–L4) & Akshat Verification Plan
Every row includes `ipo_id`, `page`, `evidence_quote` (≤ 25 words), and `label_source: "ai"` (updated to `"human_verified_ai"` only on rows Akshat verifies).

1. **L1 — SOD Fixtures (`data/gold/sod_fixtures/`, AR-02):**
   - **Scope:** 10 RHPs in `data/raw/` (Jio + 9 varied across 2024–2026, size, sector, lead managers). 10 `pages.txt` + 10 `expected.json` (8 sections each) + `FORMAT_CATALOGUE.md`.
   - **Method:** PyMuPDF (`fitz`) extraction of "Summary of the Offer Document" pages (`=== page N ===` markers) + structured extraction of printed tables/units.
   - **Akshat verifies:** Full check of Jio + 2 RHPs, table-total & unit check on the remaining 7 via side-by-side `pages.txt` (**~25 mins**).
2. **L2 — Event Labels (`data/gold/event_labels/`, AR-03):**
   - **Scope:** ~800 sentences (≥150/class across `actual_event`, `hypothetical`, `negated`, `not_relevant`) from ≥60 IPOs in `splits_by_ipo.json` (0 `excluded_ipos.json` in train/dev).
   - **Method:** Label all `serious_finding_hits.jsonl` rows + targeted mining of risk-factor/litigation sentences with ±2 context sentences.
   - **Akshat verifies:** **100% of `actual_event` rows (~160 rows)** + **100 random rows** from other classes via a flat review CSV (**~30 mins**).
3. **L3 — Gold v4 (`data/gold/v4/`, AR-05):**
   - **Scope:** All 30 Platform Bench IPOs (`FinSight_Platform_Bench.xlsx` IPOs tab). 30 `<ipo_id>.json` files (facts, 3 FY + stub financials, objects, strengths ≤30w + page, top 7 risks, 13 red-flag inputs) + `LABELS_CARD.md`.
   - **Method:** PyMuPDF targeted section extraction from `data/raw/` RHPs with exact page & ≤25-word `evidence_quote`.
   - **Akshat verifies:** **100% of facts & financials** for all 30 IPOs + **20% spot-check (6 IPOs)** of strengths/top-7 risks/red-flags via a consolidated verification CSV (**~90 mins**).
4. **L4 — Top-Risk Labels (`data/gold/top_risks/`, AR-06):**
   - **Scope:** ~60 **training-split IPOs only** × 7 top risks = ~420 positive rows (paired with ~16k `risk_bank.parquet` rows).
   - **Method:** Match RHP "Summary of Risk Factors" / top bulleted risks + materiality signals to `risk_bank.parquet` `risk_id`s with 1-line rationale.
   - **Akshat verifies:** **10% spot-check (6 IPOs = 42 rows)** (**~15 mins**).

---

## 4. Needed from CC (Posted in `docs/phase4/comms/to_cc.md`)
1. **CC-01 / CC-02 Handoff Pack (`ml/handoff/READY`):** `splits_by_ipo.json`, `excluded_ipos.json`, `risk_bank.parquet`, `serious_finding_hits.jsonl`, `student_v1_train.jsonl`, `student_prompt_template.txt`, `baselines.json`, and `colab/` setup files.
2. **Canonical `ipo_id` mapping for L1 (10 SOD RHPs) & L3 (30 Bench IPOs):** Map between `data/raw/` PDF filenames and canonical `ipo_id` slugs so `data/gold/sod_fixtures/<ipo_id>/` and `data/gold/v4/<ipo_id>.json` match CC-05 and CC-10.
3. **CC-07 Rule Preds (`eval_results/p4/cc/event_rules_preds.jsonl`):** Needed on L2 test split IDs by Sat for M3 vs rules comparison.

---

## 5. Spec Improvements (`PROPOSAL` — Not Adopted Until Approved)
- **PROPOSAL-1 (M1 Zero-GPU Unanswerable Construction):** Since unanswerable targets always output the exact deterministic refusal string (`"not found in the document"`), we only need Gemma-4-31B for the 1,000 answerable numeric rows + 500 adversarial questions, and can construct the remaining 1,500 unanswerable rows by pairing real questions with mismatched/near-miss RHP passages via script — **saving ~18 Colab units (~2 G4 hours)** with higher refusal consistency.
- **PROPOSAL-2 (M2 CPU Latency ≤ 2.0s Guarantee):** `deberta-v3-base` fp32 on 300 risks × 256 tokens takes ~9s on laptop CPU. Propose exporting dynamic `int8` quantized ONNX (`quantize_dynamic`) + `max_len=128` (or a 2-stage fast linear pre-filter 300 → top 48 → DeBERTa fp32) to guarantee `<1.5s` CPU runtime.
- **PROPOSAL-3 (M4 Verified-Only Augmentation):** Inject only Akshat-verified (`human_verified_ai`) L2 `actual_event` train-split rows into M4 Severity training to prevent label noise from hurting macro-F1.

---

## 6. Key Risks & First Cuts
1. **Gemma-4-31B Teacher Gen > 4h on G4:** *Cut first:* Adopt PROPOSAL-1 (script-pair 1,500 unanswerables; run 31B teacher only on 1,000 numeric + 500 hard unanswerables).
2. **M2 CPU > 2s / 300 risks:** *Cut first:* Cap `max_len=128` (risk header + first 2 sentences) or switch backbone to `deberta-v3-small` if fp32 latency exceeds 2.0s.
3. **M4 Macro-F1 drops > 0.01:** *Cut first:* Keep v1/focal weights fixed and tune only dev probability threshold $T_{\text{severe}}$ (0 GPU units).
4. **Akshat Verification Bandwidth:** *Cut first:* Auto-generate single-file CSVs with `value | page | evidence_quote` so Akshat verifies in one pass without opening PDFs unless a quote looks suspect.
