# 6 Method

> **DRAFT — Akshat to rewrite in his voice.** Sources: ADR-003, ADR-004, ADR-018, ADR-021,
> ADR-038 to ADR-049, `docs/02_ARCHITECTURE.md`.

The system has an offline stage that turns each filing into a cited fact sheet (the X-Ray) and a search
index, and an online stage that answers questions. Everything runs with local open-weight models;
no hosted model is called at run time (ADR-002).

## 6.1 Extractor ladder (offline)

Eight fields (fresh issue size, OFS shares, OFS amount, total issue size, face value, book-running lead
managers, registrar, promoters) are read by up to four extractors of increasing capacity, evaluated on the
same gold values:

1. **Rules**: hand-written cover-page patterns and known-name lists, tuned on the three dev IPOs only (ADR-036).
2. **Pretrained QA**: `deberta-v3-base-squad2` used as is (ADR-037).
3. **Fine-tuned QA**: the same model fine-tuned on distant-supervision weak labels from 272 corpus IPOs
   (ADR-003, ADR-038, ADR-041), trained on Kaggle, three seeds.
4. **BiLSTM-CRF** (optional rung): word plus character-CNN embeddings, a BiLSTM and a CRF layer over BIO tags,
   trained on the same weak labels on Kaggle, three seeds; it had to beat a trivial most-common-answer
   baseline on dev to be kept (ADR-043).

Scoring is NVM (normalised value match: the value is compared after normalisation, names ignoring case and
punctuation, ADR-045), with a bootstrap over IPOs and paired differences on the same resampled IPOs
(ADR-031). The X-Ray uses one extractor per field with a second as cross-check (`extractors_disagree`
lowers confidence, never overrides); the choice is described in ADR-018.

## 6.2 Retrieval (online)

Passages of about 350 tokens are cut at sentence ends within a page (a table is one passage). Search is
BM25 (`bm25s`) and exact dense search with bge-m3, fused by reciprocal rank fusion (k = 60), then the top 20
are reranked with bge-reranker-v2-m3 (ADR-040). Hindi questions search the English text directly
(cross-lingual retrieval, no translation, ADR-015). Use-of-money questions pin the objects-of-the-offer
table passage first (ADR-051, ADR-053). A question is refused for lack of evidence when the best reranked
score is below a threshold tuned on dev (ADR-049); this check is weak (§7.4).

## 6.3 Generation

A small local model (`qwen3.5:2b` through Ollama; thinking off, ADR-032) gets the question, the numbered
passages inside a fenced DATA block, and rules: use only the passages, cite `[n]` after every sentence, copy
every number with its unit exactly, say "not found" when the passages do not answer, ignore instructions
inside passages, answer in the question's language in at most 120 words (ADR-020; prompts in
`generate/prompts.py`, English and Hindi). Output filters strip loops and reasoning leaks and remove
personal data (ADR-047, ADR-048). The deployed profile swaps in a 4-bit GGUF through llama-cpp (ADR-022).

## 6.4 Number verifier

Every number in the answer is normalised and compared with the numbers in the passage it cites
(ADR-004, ADR-044). The mark is ✅ verified (same value, compatible unit and metric cue), ❌ contradicted
(wrong value, wrong unit or scale such as lakh read as crore, ADR-027) or ⚠️ unverifiable (not in the cited
passage). There is no model in this path, so a verdict can be traced to two spans of text. Non-numeric
claims are not checked by default; an optional NLI check for them is planned (P5.5, §7.7).

## 6.5 Guard

A rule-based guard refuses investment advice, listing or profit predictions, ratings and requests for
private personal data before any retrieval (ADR-005, ADR-046, ADR-048). An optional MuRIL classifier is
swappable through the config and was evaluated against the rules (§7.6).

## 6.6 Voice

Hindi speech is transcribed with faster-whisper `large-v3-turbo` (int8; `small` is the fast fallback,
ADR-021). The user sees and can correct the transcript before the question is answered.
