# Phase 4 Execution Plan — ARGON (Models & Labels)
**Owner:** Akshat · **Agent:** ARGON (Gemini 4 Argon) · **Branch:** `p4/argon` · **Budget:** 140 Colab units (84.6 planned, 55.4 reserve)

## 1. Work Order & Schedule (AR-01 .. AR-07)
| ID | Task & Deliverables | Target | Gate Alignment |
|---|---|---|---|
| **AR-01** | Read specs, write & revise `P4_EXECUTION_PLAN_ARGON.md`, post handoff/SOD requests in `to_cc.md` | Wed 21 Oct | **P4-G0** (Wed night) |
| **AR-02** | **L1 SOD Fixtures**: post 10 `ipo_id`s (`jio-platforms-2026` + 9 train/dev) in `to_cc.md` → wait for CC word-box export → write `expected.json` + `FORMAT_CATALOGUE.md` (no `pages.txt`) | Wed–Thu AM | **Unblocks CC-05** (before P4-G1) |
| **AR-03** | **L2 Event Labels** (~800 rows) + **M3 Event Classifier** notebook, 3-seed run, ONNX fp32 delivery | Wed–Fri | Unblocks CC-07/09 (**P4-G2** Sat) |
| **AR-04** | **M1 Student v2**: chat SFT teacher gen + scripted near-miss unanswerables → mixed chat+rewrite LoRA SFT → GGUF `q4_K_M` (`finsight-student:v2-q4`) | Thu–Fri | **P4-G1** (Fri night teacher data) |
| **AR-05** | **L3 Gold v4** (`data/gold/v4/<ipo_id>.json` + `LABELS_CARD.md`) for all 30 Platform Bench IPOs | Fri–Sat | Unblocks CC-10 (**P4-G3** Sun) |
| **AR-06** | **L4 Top-Risk Labels** (~60 train IPOs) + **M2 Salience Ranker** & **M4 Severity v2** notebooks + ONNX deliveries | Sat 24 Oct | Unblocks CC-09 (**P4-G2/G3**) |
| **AR-07** | **M5 Eval & Blind Judge**: `metrics.json` for M1–M4, `platform_bench_judge.jsonl`, `P4_MODEL_RESULTS.md` | Sun 25 Oct | **P4-G3** (Sun night) |

---

## 2. Exclusion & Data Hygiene Rules (Hard Constraint)
- **Canonical IDs:** Lowercase hyphen slugs `<company-words>-<year>` everywhere (e.g., `jio-platforms-2026`, `ather-energy-2025`). Never underscores.
- **Zero Leakage (`ml/handoff/data/excluded_ipos.json`):** Contains **128 excluded IPOs** (all 110 test-slice IPOs + 14 SME/unusable + demo/showcase + Bench v1 + Platform Bench including `jio-platforms-2026`). **Nothing** from `excluded_ipos.json` may enter any train or dev set across M1, M2, M3, M4, L2, or L4. Enforced by `tests/ml/test_no_leakage.py`.
- **Single Disclosed Exception:** `jio-platforms-2026` in L1 SOD fixtures (parser diagnosis only; flagged test-informed in `FORMAT_CATALOGUE.md`). The other 9 SOD fixtures come strictly from `train`/`dev` in `splits_by_ipo.json`.
- **Colab Handoff Pull:** Notebooks read `HF_TOKEN` from Colab secrets, pull large files (`risk_bank.parquet`, `classifier_train.jsonl.gz`, `student_v1_train.jsonl.gz`) from `AkshatTm/finsight-gpu-jobs` (`phase4/handoff/data/`) via `ml/handoff/colab/setup_cell.py`, and verify all SHA256 checksums against `ml/handoff/data/MANIFEST.json`.

---

## 3. Model Plans (M1–M4) & Colab Compute Budget

### M1 — Student v2 (`ml/deliveries/m1_student/v2/`)
- **Problem & Two Frozen Templates:** Existing `student_v1_train.jsonl.gz` (10,362 train / 529 dev) contains **risk-rewrite pairs only** (`student_prompt_template.txt`); **zero chat SFT data exists today**. Chat (`student_chat_template.txt` + `_hi.txt`) is M1's primary target (`0.333` hallucinated numbers on unanswerable in Bench v1 Task C).
- **New Chat SFT Data Plan (~3,000 train / ~200 dev rows from train/dev IPO passages only):**
  1. **Answerable questions (~1,000 rows, Gemma-4-31B-it on G4):** Multi-passage retrieved chunks (`[1] (RHP page p) ...`) formatted with `student_chat_template.txt` (including ~15% Hindi using `student_chat_template_hi.txt`). Answers in 1–3 short sentences (≤120 words), **every number and unit copied verbatim** (`₹ 4,720.00 million`), `[n]` citation after every sentence, and full item+amount enumeration when listing objects/proceeds. Filtered by `ml/handoff/eval/numkeep.py` (drops any row whose output contains a number absent from its passages).
  2. **Unanswerable questions (~2,000 rows, P-1 approved mix — reported in `MODEL_CARD.md`):**
     - **~500 teacher-generated hard unanswerables (Gemma-4-31B-it):** Adversarial questions over passages that mention related entities/metrics but lack the asked figure/fact.
     - **~1,500 scripted same-section hard near-misses (0 GPU):** Pair real/templated questions with **same-section passages from the same RHP** that contain adjacent metrics, wrong FY/stub period, or wrong subsidiary/entity.
     - **Exact Abstain Target:** Every EN unanswerable targets the exact string `"I could not find this in the document."` (and HI targets `"मुझे यह जानकारी दस्तावेज़ में नहीं मिली।"`).
  3. **Task Mix (No Rewrite Regression):** Combine all `10,362` `student_v1_train` rewrite rows + `~3,000` new chat rows (oversampled `2x` → `~6,000` effective chat rows vs `10,362` rewrite rows, ~37% chat / 63% rewrite) so chat abstention/numeric copying is learned strongly while `gold-50` rewrite gates do not regress.
- **Arch, Hyper-params & Export:** `Qwen/Qwen3-4B-Instruct-2507`, LoRA `r=16, alpha=32`, bf16, `lr=2e-4`, cosine schedule, `max_seq_len=2048`, `2` epochs, assistant-only loss. Merged → `q4_K_M` GGUF (`finsight-student:v2-q4`). Seed: `[42]` (single-seed disclosed).
- **Targets:** Bench v1 Task C hallucinated ≤ `0.10` (vs `0.333`), Task C correct-answerable ≥ `0.49` (vs `0.49`), gold-50 faithful ≥ `0.92`, plain-English ≥ `4.5` (vs `4.64`), post-checks ≥ `49/50`.
- **Honest Compute Re-estimate:**
  - With P-1 (`1,500` teacher calls: `1,000` answerable + `500` hard unanswerable, plus ~15% `numkeep.py` rejection buffer ≈ `1,750` prompts on Gemma-4-31B-it 4-bit on G4 at ~4.5s/prompt): **~2.2 h G4 = `19.2` units**.
  - Student v2 QLoRA training (`~16.4k` mixed rows × 2 epochs on Qwen3-4B on G4, knowing v1's 10.4k rows took 1h10m) + GGUF `q4_K_M` export & dev sanity check: **~2.3 h G4 = `20.0` units**.
  - **Total M1 G4 = `39.2` units** (well under the 70-unit ceiling; saves ~30 units vs naive 3,000-row teacher gen). *Trade-off rule if M1 ever threatened >70 units:* cap teacher-generated answerables at 800 rows and train rewrite rows for 1 epoch + chat rows for 2 epochs rather than touching M2–M4 budgets.

### M2 — Risk Salience Ranker (`ml/deliveries/m2_salience_ranker/v1/`)
- **Data:** Train on **L4** (~60 train-split IPOs paired with `risk_bank.parquet`; `section` is empty in `risk_bank.parquet`, so position is approximated by normalized `page` offset within the RHP's risk pages). Test on **L3** (30 Bench IPOs, zero leakage).
- **Arch & Latency (P-2 Modified):** `microsoft/deberta-v3-base` cross-encoder (`"{company} | {sector} | {category} | band:{severity_band} | page_rel:{rel_page} [SEP] {title}: {text}"`), Pairwise Margin Ranking + BCE loss, seeds `[13, 42, 2026]`.
  - `rank_risks` runs once per analysis → CPU latency limit is **≤ 15 s per 300 risks**.
  - **First choice:** ONNX **fp32 with `max_len=160`**.
  - **Fallback:** Use dynamic `int8` quantization **only if** fp32 exceeds 15 s on CPU **and** `int8` is within `0.005` NDCG@7 of fp32 on dev/test.
- **Eval & Separate Verified Reporting:** Report NDCG@7, Recall@7, and broker_overlap@7 against `five_things_selection.jsonl.gz` on (a) all 30 L3 Bench IPOs and **(b) separately on the 10-IPO subset where Akshat verified 100% of the L3 top-7 lists**.
- **Colab & Units:** T4 debug (`1.5 u`) + G4 3-seed run `m2_salience_ranker.ipynb` (~1.2 h = `10.5 u`).

### M3 — Event Classifier (`ml/deliveries/m3_event_clf/v1/`)
- **Data:** **L2** (`data/gold/event_labels/`), split by `splits_by_ipo.json` (zero `excluded_ipos.json` in train/dev). `check_id` ∈ `{going_concern, default_or_recall, regulator_order, fraud, qualified_audit}`. 4 labels: `actual_event`, `hypothetical`, `negated`, `not_relevant`.
- **Arch & Loss:** `microsoft/deberta-v3-base` (`"{check_id} | {context_before} [SEP] {sentence} [SEP] {context_after}"`), `max_len=256`, class-weighted CE + dev threshold tuning for `actual_event` precision ≥ 0.90. Seeds: `[13, 42, 2026]`. ONNX fp32 (`classify_events`, CPU ≤ 50 ms/item).
- **Eval & Target:** `run_classifier_eval.py` vs CC-07 rules (`eval_results/p4/cc/event_rules_preds.jsonl`). Target: beat rules on macro-F1, **`actual_event` precision ≥ 0.90**, **`actual_event` recall ≥ 0.80**, and **0 false serious findings on 30 bench IPOs**.
- **Colab & Units:** T4 debug (`1.0 u`) + G4 3-seed run `m3_event_clf.ipynb` (~0.4 h = `3.5 u`).

### M4 — Severity v2 (`ml/deliveries/m4_severity/v2/`)
- **Interface & Problem:** Seriousness **band head (bands 1–4, 4 = severe)** of the risk classifier (`predict_severity(texts) -> [{"band": 1..4, "label": "low"|"medium"|"high"|"severe", "probs": {"1": float, ...}}]`, ONNX fp32). Baseline `severe_recall_mean = 0.5575` (precision `0.5645`, band macro-F1 `0.7617`, band MAE `0.1862`) on **only 58 severe dev rows** (`classifier_dev.jsonl.gz`, n=1,060).
- **Guardrail & CI Reporting:**
  1. **Noisy Dev Support CI:** Because `n_severe_dev = 58` (1 row ≈ 1.72% recall), report **95% bootstrap / Wilson confidence intervals** alongside the 3-seed mean ± std for `severe_recall`, `severe_precision`, and `band_macro_f1` in `metrics.json` and `MODEL_CARD.md`. Also report severe recall on `gold-150` (`classifier_test.jsonl.gz`, eval-only).
  2. **Category Guardrail:** 10-way category `dev_macro_f1_mean = 0.8923` is a **no-regression guardrail** (drop must be `≤ 0.01`, i.e., `≥ 0.8823`). Since category and band heads are trained separately (`phase3_models.md`), M4 replaces only the band head (keeping the shipped category head untouched → `0.000` category drop) or verifies `≥ 0.8823` if shared.
  3. **Strict L2 Augmentation Rule (P-3):** An L2 `actual_event` train-split row enters M4 training **only if Akshat verified it (`label_source: "human_verified_ai"`) AND assigned it a severity band (1–4)**. Unverified or un-banded L2 rows are never added.
- **Arch & Loss:** `microsoft/deberta-v3-base` 4-band classifier (`max_len=384` matching v1, Focal + class-weighted CE + ordinal MAE penalty + dev threshold calibration on `P(band=4)`). Seeds: `[13, 42, 2026]`.
- **Target:** `severe_recall_mean ≥ 0.70` (with 95% CI reported), category macro-F1 guardrail held (`≥ 0.8823`).
- **Colab & Units:** T4 debug (`1.5 u`) + G4 3-seed run `m4_severity_v2.ipynb` (~1.2 h = `10.5 u`).

### Compute Summary (140 Units Cap, G4 = 8.71 u/hr)
| Job | Runtime | Est. Hours | Units |
|---|---|---|---|
| All T4 `DEBUG=True` smoke runs (M1 gen, M1 train, M2, M3, M4 + M5 judge test) | T4 | ~4.0 h | **8.0** |
| M1 Teacher Generation (`m1_teacher_gen.ipynb`, 1,000 answerable + 500 hard unanswerable) | G4 | ~2.2 h | **19.2** |
| M1 Student v2 LoRA + GGUF (`m1_student_train.ipynb`, `m1_export_gguf.ipynb`) | G4 | ~2.3 h | **20.0** |
| M2 Salience Ranker (3 seeds, `10.5u`) + M3 Event Clf (3 seeds, `3.5u`) + M4 Severity v2 (3 seeds, `10.5u`) | G4 | ~2.8 h | **24.5** |
| M5 Platform Bench Blind Risk Judge (if run via local/Colab LLM) | G4 / T4 | ~1.5 h | **12.9** |
| **Total Planned** | — | — | **84.6** |
| **Unallocated Reserve** (for retries / hyper-param iteration) | G4 / T4 | ~6.4 h G4 | **55.4** |

---

## 4. Label Sets (L1–L4) & Akshat Verification Plan

1. **L1 — SOD Fixtures (`data/gold/sod_fixtures/`, AR-02):**
   - **New Flow:** (1) ARGON posts 10 canonical `ipo_id`s in `docs/phase4/comms/to_cc.md` (`## REQUEST sod_fixture_ids`): `jio-platforms-2026` (the 1 disclosed exception) + **9 varied RHPs from `train`/`dev` only** (varied across issue size, sector, year 2024–2026, and lead managers; 0 from `excluded_ipos.json`) and **STOPS** AR-02. (2) CC exports word positions (`words + boxes + tables`) to `tests/fixtures/real/` and replies in `to_argon.md`. (3) ARGON reads the RHP PDFs (`data/raw/offer_docs/<ipo_id>.pdf` + Jio PDF) and writes **`data/gold/sod_fixtures/<ipo_id>/expected.json` + `FORMAT_CATALOGUE.md` only** (ARGON does **not** write `pages.txt`).
   - **Akshat verifies:** Jio + 2 RHPs in full, table totals & units on the remaining 7 (**~25 mins**).
2. **L2 — Event Labels (`data/gold/event_labels/`, AR-03 — starts immediately):**
   - **Source & Audit of Blocked Sentences:** `ml/handoff/data/serious_finding_hits.jsonl.gz` has **2,801 sentences** across 275 docs (`314` `fired`, `2,469` `blocked_soft`, `18` `blocked_no_debt`). Filter out any `excluded_ipos.json` from train/dev splits (test-slice hits stay strictly in `test` for evaluation only).
   - **Mining Strategy for Rare `actual_event` Class:**
     1. Label all non-excluded `fired` sentences (`314` total across splits).
     2. **Audit `blocked_soft` (`2,469` sentences):** Because the regex filter blocks any sentence containing words like `not`, `may`, `could`, `if`, or `in the event`, it also **blocks real historical events** that contain a hedge/negation clause later in the sentence (e.g., *"In FY24, lender X recalled our ₹50M facility, and we may face similar actions..."* or *"SEBI issued an order dated ... which has not yet been stayed"*). Systematically scan `blocked_soft` for past-tense/dated event verbs, regulator/court order dates, audit qualifications, and default notices to rescue true `actual_event` rows, while sampling rich `hypothetical` and `negated` examples.
     3. **Mine Risk Factors & Litigation (`risk_bank.parquet` + `data/raw/offer_docs/`):** Mine additional train/dev risk-factor and litigation sentences with concrete dates, order numbers, penalty amounts, show-cause/recall notices, and auditor emphasis-of-matter/qualifications to push `actual_event` toward ≥150.
     4. **Honesty Rule:** Never pad `actual_event` with borderline or synthetic rows. If genuine `actual_event` stays under 150 after auditing all `fired` + `blocked_soft` + `risk_bank.parquet`, **report the exact natural count honestly in `LABELS_CARD.md` and `to_cc.md`**.
   - **Akshat verifies:** **100% of `actual_event` rows** (plus assigns a 1–4 severity band on verified train-split `actual_event` rows so they can feed M4) + **100 random rows** from the other 3 classes (**~35 mins**).
3. **L3 — Gold v4 (`data/gold/v4/`, AR-05):**
   - **Scope:** 30 Platform Bench IPOs (`<ipo_id>.json` + `LABELS_CARD.md`: facts, 3 FY + stub financials, objects, strengths ≤30w + page, top 7 risks matched to `risk_id` or text+page, 13 red-flag inputs).
   - **Akshat verifies (~3.0 hours budgeted):** **100% of facts & financials across all 30 IPOs**, **100% of the top-7 risk lists on 10 IPOs** (used as M2's human-verified evaluation subset), and spot-checks on the remaining 20 IPOs.
4. **L4 — Top-Risk Labels (`data/gold/top_risks/`, AR-06):**
   - **Scope:** ~60 **train-split IPOs only** (0 excluded IPOs) × 7 top risks = ~420 positive rows matched to `risk_bank.parquet` `risk_id`s with 1-line reason + `LABELS_CARD.md`.
   - **Akshat verifies:** 10% spot-check (6 IPOs = 42 rows, **~15 mins**).

---

## 5. Approved Proposals & Guardrails Summary
- **P-1 (Approved):** ~1,500 scripted unanswerables must be **same-section hard near-misses** (wrong metric/period/entity from the same section); keep **~500 teacher-generated hard unanswerables**; report the exact mix in `MODEL_CARD.md`.
- **P-2 (Modified & Approved):** `rank_risks` CPU budget is **≤ 15 s per 300 risks** (runs once per analysis). Try **ONNX fp32 with `max_len=160` first**; use `int8` only if needed and within `0.005` NDCG@7.
- **P-3 (Approved):** Use an L2 row in M4 **only if Akshat verified it (`human_verified_ai`) AND assigned a band (1–4)**.
