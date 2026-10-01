# 05 — Data and Evaluation

This doc owns datasets, splits, labelling protocols, metric definitions and the experiment list. Every number in the report must trace back to an experiment here and a JSON file in `eval_results/`.

---

## 1. Datasets

### 1.1 Overview

| Set | Contents | Size | Used for | Never used for |
|---|---|---|---|---|
| **Training corpus** | RHP text of past Indian IPOs from the Ghosh et al. IPO datasets (CC BY-NC-SA 4.0) | target ≥ 300 mainboard RHPs (more if available) | Weak labels → fine-tuning | Evaluation |
| **Demo set** | 10 recent mainboard IPOs (2025), each with its RHP **and** final Prospectus, clean digital PDFs. **3 dev / 7 test** (ADR-026) | 10 (+2 optional) | Demo; dev IPOs for tuning rules and extractor choice, test IPOs for reported numbers | Training; tuning on the 7 test IPOs |
| **Gold v1** | Hand-labelled values for the 11 fields on the demo set, labelled in Phase 1 before any extractor runs | ~110 values | Extractor ladder, verifier tests | Training |
| **Gold v2 (expansion)** | +10 held-out IPOs, 2025–26, RHP + Prospectus each (not in training corpus) | ~20 IPOs with v1, ~220 values | Final report numbers | Training |
| **Dev questions** | ~20 hand-written questions on 3 demo IPOs | 20 | Tuning retrieval abstain threshold, prompt | Final numbers |
| **Test questions** | ~60 hand-written questions (EN + HI) on the other IPOs | 60 | Retrieval Recall@5, answer quality | Tuning |
| **Advice set** | ≥ 50 advice + ≥ 50 factual questions **written by Akshat and friends** (EN/HI/Hinglish) for guard evaluation; up to ~150 + ~150 more (may be drafted by Claude Code) for classifier training only | 100 eval + ≤ 300 train | Guard evaluation (Akshat's set only), classifier training (Claude-drafted lines only) | Evaluating a guard on lines the guard author wrote |
| **Hindi audio** | 10–20 recorded Hindi questions | 10–20 | ASR bake-off + WER/CER | — |

We **do not use** the dataset's Apply/Avoid rating labels or listing-gain targets, ever.

### 1.2 Day-1 recon [AKSHAT + CC] (Phase 0.4)

1. Download the Hugging Face IPO dataset repo into `data/raw/ipo_dataset/`.
2. CC writes `ingest/recon.py` that prints: files, row counts, column names, dtypes, null rates, and for text columns the length distribution and 3 truncated examples. **CC runs it and reads only its printed summary**, not raw files.
3. Answer these in `09_DECISIONS.md` (ADR "Training corpus source"):
   - Does it contain full RHP text, partial text, or only PDF links?
   - Mainboard vs SME counts? Years covered?
   - Is there a company name/ISIN/date usable for de-duplication against the demo set?
4. Save 5 rows (truncated) to `data/samples/ipo_dataset_rows.jsonl`.

### 1.3 Plan B if the dataset has no usable full text

1. If it has PDF links: `ingest/download_rhps.py` downloads ≤ 400 RHPs politely (1 request / 2 s, retries, resume, checksum log). Akshat runs it.
2. Run our own `parse` on them → `data/processed/corpus/<ipo_id>.json`. Scanned PDFs are skipped.
3. If neither text nor links exist: Akshat hand-downloads ~150 RHPs from SEBI/exchange pages over 2 evenings (the weak-labelling pipeline works with 150; fewer examples, same method).

### 1.4 Demo set selection criteria [AKSHAT, Phase 0.4]

- Listed 2024–2026, mainboard, names a classmate would recognise.
- Digital PDF (text selectable), not scanned.
- Mix of structures: the downloaded set is 2 pure OFS and 8 mixed as far as we know (recon confirms from the Prospectus offer tables); no pure-fresh IPO yet. Adding 2 pure-fresh IPOs later is welcome; until then pure-fresh handling is covered by fixtures only. Report the actual mix.
- At least 2 whose tables say "(₹ in million)" and 2 that use crore throughout (recon checks).
- At least one very large RHP (600+ pages) to test performance (Lenskart, 1083 pages).
- Record in `configs/demo_ipos.yaml`: `ipo_id`, company, RHP and Prospectus file, pages, sha256, cover date, `split`.

### 1.5 Split rules

- Splits are **by IPO**, never by passage.
- Demo set: 3 dev / 7 test. Rules, thresholds, prompts and the per-field extractor choice are tuned on **dev only**; the ladder, retrieval and answer numbers in the report are computed on **test**. Proposed dev IPOs: `hexaware-technologies-2025` (pure OFS), `ather-energy-2025`, `urban-company-2025` (confirm in P0.4).
- Demo set and gold v2 IPOs are removed from the training corpus by company name + year (fuzzy match, threshold logged) before weak labelling. The exclusion list is committed (`data/gold/excluded_ipos.txt`) and a test asserts no overlap.
- Weak-label train/dev = 90/10 by IPO, seed 2026.

---

## 2. Gold labelling protocol [AKSHAT]

**File:** `data/gold/gold_values.jsonl`, one line per (ipo, field):
```json
{"ipo_id": "acme-industries-2025", "field_id": "fresh_issue_size", "value_raw": "₹ 800.00 crore",
 "page": 12, "quote": "Fresh Issue of up to [●] Equity Shares aggregating up to ₹ 800.00 crore",
 "status": "present", "labelled_at": "2026-10-08", "notes": ""}
```
`status` ∈ `present | not_in_document | placeholder`. List fields store a JSON list in `value_raw`; `objects_of_offer` stores `[purpose, amount]` pairs (amounts as printed, usually ₹ million). Optional `label_source` ∈ `hand | ai_assisted_verified` (default `hand`; ADR-035). A `not_in_document` row may keep `page` and `quote` as evidence (for example a pure offer for sale).

**Rules**
1. **Blind labelling for gold v1:** label from the PDF directly, before any extractor exists or its output is seen (Phase 1, sub-phase P1.7). This keeps the ladder fair. Fields: fresh issue amount, OFS shares, OFS amount, offer price (Prospectus), price band (if stated), face value, BRLMs, registrar, promoters, objects of the offer. Record the **PDF page**.
2. Record the **first authoritative occurrence** (cover page or The Offer) and the page number.
3. Copy the value exactly as printed; normalisation is done by code.
4. **Self-consistency check:** a week later, re-label 10 random values without looking; report agreement.
5. **Gold v1 as actually built (ADR-035):** the 110 values were pre-filled by Claude (chat) from the PDFs and then verified by Akshat, so rule 1 (blind labelling) was not followed and all rows carry `label_source: ai_assisted_verified`. Reports must disclose this: extractor scores against gold v1 measure agreement with AI-read, human-checked values, and the two may share blind spots. Hand corrections made during verification: not recorded. The self-consistency check (rule 4) therefore compares a fresh hand pass against these values.
6. Gold v2 may use *assisted* labelling (CC pre-fills page hints, not values) — disclosed in the report.

Estimated effort: ~15 min per IPO for 11 fields across two documents → ~2.5–3 h for v1, ~4 h for v2.

---

## 3. Weak labelling (distant supervision)

Pipeline and rationale are in `02_ARCHITECTURE.md` and `10_FINSIGHT_EXPLAINED.md`. Evaluation protocol:

- **Seed precision first:** rules extract seed values only when unambiguous (exactly one match pattern, non-placeholder, passes consistency). Coverage is reported (share of corpus IPOs with a seed per field).
- **Propagation filters:** only passages in the field's expected sections; value must be equal under `normalize.equal`; a metric keyword within the passage.
- **Non-numeric fields:** names (BRLMs, registrar, promoters) propagate by normalized fuzzy match ("Ltd" ↔ "Limited", case and punctuation folded). A list field trains on one span covering the whole list. `objects_of_offer` is a table and uses the table extractor only, outside the QA ladder. `offer_price` is read by rules from the Prospectus cover and is also outside the ladder: RHP training texts hold `[●]` for it, so weak labelling has no positives.
- **Negatives:** 1–2 per positive, same sections, value absent.
- **Audit [AKSHAT]:** `weaklabel/audit.py` samples 50 positives stratified by field → `data/gold/weaklabel_audit.jsonl` with the passage and highlighted answer → Akshat marks `correct | wrong_span | wrong_value | ambiguous`. Report precision with a 95 % Wilson interval.
- **Audit result and disclosure (ADR-041):** 45/50 correct on **v1** labels (90 %, Wilson 78.6–95.7 %; `python -m finsight.weaklabel audit-score` → `eval_results/weaklabel_audit.json`). The audit labels were **drafted by Claude (chat) and reviewed by Akshat** (`label_source: ai_labelled_claude_chat_human_reviewed`), not labelled blind. The five misses were fixed in code and the training data regenerated as **v2** (equity-only face value; spans keep initials and closing brackets; list spans cover the whole list). v2 is not re-audited: always write "measured on v1, fixes applied in v2".

Dataset card for the generated set: counts per field, positives/negatives, IPOs, avg passage length → `eval_results/weaklabel_stats.json`.

---

## 4. Metric definitions

| Metric | Definition |
|---|---|
| **EM** | Predicted span string == gold string after whitespace/case/punctuation normalisation |
| **Token F1** | SQuAD-style token overlap F1 |
| **NVM (normalized value match)** — primary | `normalize.equal(pred, gold)` for money/count/percent; for text/list fields, case-folded set match (list F1 for lists) |
| Field coverage | Share of fields where the extractor returns a non-empty answer |
| Correct abstention | Extractor returns "no answer" when gold `status = not_in_document` |
| **Verifier P / R / F1** | Positive class = "answer contains an error". Per error type and overall |
| Recall@5, MRR | Gold passage (containing the answer) in top 5 / reciprocal rank |
| Citation compliance | Share of answer sentences with ≥ 1 valid `[n]` |
| Answer numeric accuracy | Share of numbers in answers that are correct vs gold (human-checked on the test questions) |
| ASR CER / WER | Character / word error rate on Hindi clips (CER is primary for Hindi) |
| Guard | Block rate on advice set, false-block rate on factual set |
| Latency | p50 / p95 per stage, laptop `full` profile |

Uncertainty: 3 seeds → mean ± std for trained models; bootstrap 95 % CI (1,000 resamples by IPO) for gold-set metrics. Always print `n`.

**Headline claim and settings (ADR-031).** With ~7 test IPOs a single IPO moves one field's score by 10+ points, so the headline result is overall NVM with a bootstrap CI and a paired per-IPO difference between rungs; per-field results are shown as descriptive. Every ladder is reported in two settings: **full document** and **body-only** (cover page and summary masked), because cover sentences are templated and rules read them almost perfectly; body-only tests robustness to other wordings.

---

## 5. Experiments

| ID | Question | Setup | Output file |
|---|---|---|---|
| E1 | How good are auto-labels? | 50-sample audit | `eval_results/weaklabel_audit.json` |
| E2 | Rules baseline | Rung 1 on gold | `eval_results/ladder/rules.json` |
| E3 | Does fine-tuning on weak labels help? | Rung 2 vs Rung 3 (3 seeds) on gold | `eval_results/ladder/qa_pretrained.json`, `qa_finetuned_seed*.json` |
| E4 | Ablations | (a) cover page excluded from positives vs included; (b) negative ratio 1:1 vs 1:2; (c) epochs 2 vs 3 | `eval_results/ablations/*.json` |
| E5 | Does the verifier catch errors? | 100 seeded errors + 100 correct answers (§6) | `eval_results/verifier.json` |
| E6 | Retrieval quality | BM25 vs dense vs hybrid vs hybrid+rerank on test questions | `eval_results/retrieval.json` |
| E7 | Answer quality | Citation compliance, answer numeric accuracy, abstention on unanswerable questions | `eval_results/answers.json` |
| E8 | Guard | Keyword guard vs MuRIL classifier | `eval_results/guard.json` |
| E9 | Frontier comparison | §7 | `eval_results/frontier.json` |
| E10 | Latency + memory | Benchmark script, `full` and `dev_light` | `eval_results/latency.json` |
| E11 | BiLSTM-CRF rung (P1) | BIO-tagged version of weak labels, 3 seeds | `eval_results/ladder/bilstm_crf_seed*.json` |
| E12 | ASR | Candidates on Hindi clips | `eval_results/asr.json` |

`evaluate/ladder.py` regenerates `eval_results/ladder_table.{csv,json,tex}` from the ladder files. The Model Lab and report read only these.

### 5.1 Result file schema (all experiments)
```json
{"experiment": "E3", "name": "qa_finetuned", "seed": 42, "created_at": "...",
 "git_sha": "abc1234", "data": {"gold_version": "v1", "n_ipos": 12, "n_values": 104},
 "metrics": {"nvm": 0.81, "em": 0.74, "f1": 0.86},
 "per_field": {"fresh_issue_size": {"nvm": 0.92, "n": 12}},
 "notes": ""}
```

---

## 6. Seeded-error harness (E5)

This is a **unit-level benchmark**: the errors are constructed from known rules, so high recall is expected by design. Natural-error evidence comes from running the verifier on real LLM answers (E7) and on frontier answers (E9), with a hand-checked sample reported.

Start from answers verified correct by Akshat (or constructed from gold values with a template). Corrupt one number per answer:

| Error type | Construction | Expected verdict |
|---|---|---|
| `scale_lakh_crore` | crore → lakh (value unchanged) or ×/÷100 | ❌ scale_mismatch |
| `scale_million_crore` | 10× shift with unit swap | ❌ scale_mismatch |
| `digit` | Change one digit | ❌ wrong_value |
| `swap_metric` | Put the OFS value in the fresh-issue sentence | ❌ wrong_metric |
| `invented` | Insert a plausible number absent from evidence | ⚠️ not_found (counts as detected) |
| `rounding_ok` | Round within stated precision | ✅ (must *not* be flagged) |

Balanced: 100 corrupted + 100 correct (incl. rounding_ok). Detection = verdict ∈ {❌, ⚠️} for corrupted; false alarm = ❌ or ⚠️ on correct.

---

## 7. Frontier LLM comparison (E9)

- **Models:** one Claude model and optionally one other frontier chatbot, via their consumer apps with the RHP PDF uploaded (or a small one-time API spend). Record model name, date, interface.
- **Tasks:** (a) the 9 X-Ray fields for each gold IPO, asked with a fixed prompt; (b) 20 test questions.
- **Scoring:** same NVM metric; citation = page number given and correct.
- **Upload check (Phase 1):** test one full 600-page RHP upload in each consumer app. If it is truncated or rejected, add a condition where both systems receive the same top-5 passages, and report both conditions.
- **Twist (strong report result):** run FinSight's verifier on the frontier answers (with FinSight's retrieval as evidence) and report how many of their numbers get ❌ / ⚠️, broken down by error type.
- **Honesty:** they saw the full PDF; they are much larger; they likely win on open-ended explanation — say so. Expected FinSight advantages: numeric faithfulness, page citations, consistency, cost, offline operation.
- Store raw frontier outputs in `data/gold/frontier_raw/` (committed; small text).

---

## 8. Question sets

- Written by Akshat with CC's help from templates, **after** gold labelling, spread across fields and sections, 30 % Hindi.
- Each test question stores: `ipo_id`, `question`, `language`, `answer_gold` (short), `evidence_page`, `answerable` (bool). ~15 % unanswerable to test abstention.
- File: `data/gold/questions_{dev,test}.jsonl`.

---

## 9. Ethics of data

- Public regulatory documents only; licences stated in README, report and model card.
- Voice clips: Akshat's own voice (and a consenting friend); stored locally, not committed.
- No scraping behind logins; polite rate limits.

---

## 10. References (report bibliography seed)

- Ghosh, Maji, Naskar (2025). InFiNITE: Indian Financial Narrative Inference Tasks & Evaluations. Eval4NLP 2025.
- Ghosh, Maji, Vardhan, Naskar (2024). Experimenting with Multi-modal Information to Predict Success of Indian IPOs. arXiv:2412.16174.
- Ghosh, Naskar (2025). Predicting Ratings of Indian IPOs from Red Herring Prospectus. EasyChair Preprint 15779.
- Ghosh, Maji, Naskar (2025). MiMIC: Multi-Modal Indian Earnings Calls Dataset. arXiv:2504.09257.
- Ghosh et al. (2024). IndicFinNLP: Financial NLP for Indian Languages. LREC-COLING 2024.
- Mintz, Bills, Snow, Jurafsky (2009). Distant supervision for relation extraction without labeled data. ACL.
- Rajpurkar, Jia, Liang (2018). Know What You Don't Know: Unanswerable Questions for SQuAD. ACL.
- He, Gao, Chen (2021). DeBERTaV3. arXiv:2111.09543.
- Chen et al. (2024). BGE M3-Embedding. arXiv:2402.03216.
- Robertson, Zaragoza (2009). The Probabilistic Relevance Framework: BM25 and Beyond.
- Cormack, Clarke, Buettcher (2009). Reciprocal Rank Fusion. SIGIR.
- Radford et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision (Whisper).
- Lample et al. (2016). Neural Architectures for Named Entity Recognition (BiLSTM-CRF).
- Dettmers et al. (2023). QLoRA. NeurIPS.
- Financial hallucination benchmarks: PHANTOM, FinGround, FRED, K-FinHallu (related work; verify exact citations when writing).
- Loughran, McDonald (2011). When is a liability not a liability? Journal of Finance.

Claude Code must verify every citation (authors, venue, year) before it enters the report.
