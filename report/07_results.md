# 7 Results

> **DRAFT — Akshat to rewrite in his voice.** Every number is read from `eval_results/`; the file is named
> at each table. All intervals are 95 %. The test set is seven IPOs (56 extractor values), so read the paired
> differences and the intervals, not the point scores. Parts marked **TBD** are filled when the run finishes.

## 7.1 Extractor ladder (E2, E3, E11) — `ladder_table.json`

Normalised value match (NVM) on the 7 test IPOs; bootstrap over IPOs. Fine-tuned and BiLSTM-CRF are means of 3
seeds. *Body-only* blanks pages 1 to 15 and scores the 35 values still stated in the pages an extractor may read.

| Rung | Full document (n = 56) | Body-only (n = 35) |
|---|---|---|
| 1 Rules | **0.857** | 0.229 |
| 2 Pretrained QA | 0.357 | 0.371 |
| 3 Fine-tuned QA | 0.738 | **0.848** |
| 4 BiLSTM-CRF | 0.488 | 0.276 |

Paired differences (same resampled IPOs): fine-tuned minus pretrained +0.381 [0.226, 0.524] full and +0.476
[0.305, 0.657] body-only, so **fine-tuning on weak labels clearly helps**. Fine-tuned minus rules is −0.119
[−0.214, −0.012] on the full document and +0.619 [0.600, 0.657] body-only: rules win on templated cover pages,
and away from the cover only the fine-tuned model works. Fine-tuned minus BiLSTM-CRF is +0.250 [0.137, 0.375]
full and +0.571 [0.495, 0.648] body-only; BiLSTM-CRF is not distinguishable from the pretrained model
(+0.131 [−0.018, 0.262] full). The PRD target of beating rules on at least 5 of 8 fields **was not met**: the
fine-tuned model is ahead on one field (promoters). The BiLSTM-CRF passed its dev gate against a most-common-answer
baseline but is far below the fine-tuned model, which is the expected ordering for a small model without
pretraining; it is reported as measured.

**Product choice.** The X-Ray reads each field with the best extractor (ADR-018): system accuracy on test is
0.875 [0.804, 0.946] for the rules-first configuration actually shipped and 0.857 [0.750, 0.946] for the
dev-only choice (`xray_accuracy.json`; difference one value of 56). The rules-first choice for two fields was
made after seeing test results (disclosure 3 in `report/README.md`).

## 7.2 Retrieval (E6) — `retrieval.json`

Test questions (56 answerable; the evidence page or the gold answer appears in the top results):

| Method | recall@1 | recall@5 | MRR |
|---|---|---|---|
| BM25 | 0.304 | 0.625 | 0.394 |
| Dense (bge-m3) | 0.268 | 0.518 | 0.347 |
| Hybrid (RRF) | 0.339 | 0.643 | 0.436 |
| Hybrid + rerank | **0.464** | 0.607 | **0.514** |

Reranking helps the top of the list (recall@1 +0.125 over hybrid) but not recall@5; the difference at recall@5 is
two of 56 questions (ADR-049). Abstaining on the retrieval score is weak: on test the tuned threshold refuses
23 of 56 answerable questions to catch 9 of 11 unanswerable ones, so the deployed threshold is looser (ADR-049).

## 7.3 Answers through the full pipeline (E7) — `e7.json`

`full` profile (qwen3.5:2b, temperature 0.2, one run), questions through the real orchestrator:

| Split | Questions | Answered | Refused | Abstained | Numbers | ✅ | ⚠️ | ❌ |
|---|---|---|---|---|---|---|---|---|
| Dev | 50 | 42 | 3 | 5 | 68 | 52 (0.76) | 8 | 8 |
| Test | 67 | 60 | 7 | 0 | 86 | 59 (0.69) | 22 | 5 |

Of the unanswerable questions, 3 of 9 (dev) and 4 of 11 (test) ended in abstention or "not found". ✅ means
the number is in the cited passage with the right unit, not that the answer is correct. Twenty answers per
split with numbers are in `e7_sample_<split>.jsonl` for the author to check by hand (not yet done). One run:
a 13-item score moves by two or three between runs (ADR-020), so do not quote these as stable rates.

## 7.4 Number verifier on seeded errors (E5) — `verifier.json`

200 items built by known rules from 45 gold values (digit errors, scale slips, wrong units, invented values,
correct controls). **Held-out** (rules frozen on the three dev IPOs, first run on all ten): detection 100/100,
exact reason 95/100, false alarms 0/100, scale-mismatch recall **35/40** [0.74, 0.95] (27 test items: 22). After
one rule fix made on seeing the five test misses: 40/40, **not held-out**. E5 is a unit benchmark with
templated answers, so high recall is expected by design; it says nothing about free text (that is E7).

## 7.5 Hindi quality — ADR-020, `data/gold/hindi_fluency_sheet_rated.csv`

Fluency 1 to 5 on 20 answers per model, scores drafted by Claude and **pending the author's confirmation**:
qwen3.5:2b mean 2.9, qwen3.5:4b 2.7 (gemma4:e2b not rated, empty outputs). Number-copy in Hindi: 8 of 13 for
the 2B model against 9 of 13 in English (a 13-item score moves by two or three between runs). Hindi answers are
labelled experimental in the product.

## 7.6 Guard (E8) — `guard.json`, `guard_compare.json`

Keyword rules on the AI-drafted set (60 advice, 60 factual): block rate 60/60 [0.94, 1.00], false-block 0/60
[0.00, 0.06] — **in-sample**, because the rules were tuned after reading that set. Unseen: 85 fresh probes, first
run: 33/36 advice blocked, 0/49 factual blocked, 11/11 privacy probes blocked, 0/10 business-contact false blocks.
MuRIL classifier (three seeds, best by validation F1, 70/15/15 split by question): on the 18 held-out
questions it blocks 9/9 advice but also blocks 4/9 factual questions, against 9/9 and 0/9 for the keyword rules;
the intervals overlap widely. The keyword guard stays the default.

## 7.7 Speech (E9) — `asr.json`

Ten Hindi clips, word and character error against references that are Claude's reading of what was said (none
reviewed by the author; `large-v3-turbo` also drafted them, so its CER is optimistic): large-v3-turbo CER 0.062,
WER 0.228; medium 0.289 and 0.352; small 0.363 and 0.557. Median seconds per clip on CPU int8: 9.8, 7.7 and 2.9.

## 7.8 Non-numeric claim check (P5.5) and latency (E10)

**NLI on non-numeric claims (P5.5, `nli.json`).** mDeBERTa-v3-xnli on 180 seeded name claims built from gold
quotes (registrar, promoters, lead managers; English and Hindi hypotheses; entailed, contradicted and
neutral): accuracy 30/54 [0.42, 0.68] on dev IPOs and 67/126 [0.45, 0.62] on test IPOs, near chance for three
classes, with neutral claims the worst (14 of 54 correct) and Hindi no worse than English. Names are a hard
case for NLI (the model treats any promoter name near a cover block as supported). Conclusion: the check is
**not good enough to show users**; `verify.nli` stays off and nothing in the API uses it.

**Latency and memory (E10, `latency.json`).** See the table below.

| Profile | LLM | Median first token | Median total | 90th percentile total | Peak GPU | Peak process RAM |
|---|---|---|---|---|---|---|
| `dev_light` | qwen3.5:0.8b | 2.7 s | 3.5 s | 5.4 s | 2.6 GB | 0.8 GB |
| `full` | qwen3.5:2b | 25.4 s | 32.0 s | 37.3 s | 3.8 GB | 3.7 GB |

First 20 answerable dev questions, one at a time, RTX 2050 (4 GB), Ollama resident. In `full` the median
answer spends 17 s in retrieval and 14 s in generation: with embedder, reranker and the 2B model all wanting
the 4 GB GPU, retrieval is far slower than the 0.7 s measured with no LLM loaded (`memory.json`); the cause was
not investigated (likely memory pressure and model swapping). The first question after start-up took 46 s. The
Cloud Run CPU deployment is not measured yet (E23). Whole-system RAM in use peaked at 15 GB of 16 GB.

## 7.9 Phase 2 experiments (E13–E24)

> The table is generated from `eval_results/` by `scripts/docs_gen.py` (`uv run poe docs-gen`); a row shows a
> file only when it exists, and no Phase 2 number is written here by hand. Results are filled in by the local
> sessions that run each experiment (B04 §3); the paragraphs that interpret them are written after.

<!-- generated:phase2 start -->

| ID | Question | Result files |
| --- | --- | --- |
| E13 | Are risks split correctly? | `b/segmentation.json` |
| E14 | Are red-flag inputs extracted correctly? | not run yet |
| E15 | Do red-flag statuses agree with hand-computed ones? | not run yet |
| E16 | How good is the category classifier? | not run yet |
| E17 | Does the seriousness rule make sense? | not run yet |
| E18 | Are rewrites faithful? | not run yet |
| E19 | Are rewrites easier to read? | not run yet |
| E20 | Do rewrites keep numbers and certainty? | not run yet |
| E21 | Does the risk level relate to real outcomes? | not run yet |
| E22 | Is "unusual" meaningful? | not run yet |
| E23 | Speed and robustness on unseen PDFs | not run yet |
| E24 | Cost | not run yet |
| E8r | Does the guard still behave after allowing risk-level questions? | not run yet |
| E7c | Chat answers on the deployed `cloud` profile (BM25, Q4) | not run yet |

<!-- generated:phase2 end -->

What each experiment must report, when it runs (B04 §3):

- **E13–E15** (segmentation, red-flag inputs, red-flag statuses): measured on the test IPOs, dev used for
  tuning only; NVM and status accuracy with intervals.
- **E16** (category classifier): the ladder TF-IDF + LR → DeBERTa base (3 seeds) → large (1 seed) → teacher
  zero-shot on gold-150; macro-F1 with per-class F1. Model chosen on dev only.
- **E17–E20** (seriousness rule, rewrites): Spearman ρ against the teacher's ratings; blind human ratings of
  "same meaning" for base, student and teacher on gold-50; readability drop; the share of rewrites rejected
  by each check.
- **E21** (risk level against outcomes): a correlation check only, reported with bootstrap intervals; it is
  not a forecast and is not shown as one.
- **E22–E24** (novelty threshold, cloud speed, cost per upload).
