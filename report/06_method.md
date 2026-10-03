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

## 6.7 Phase 2: from an uploaded document to a report

> Sources: `docs/phase2/B02_ARCHITECTURE.md` §3–8, `docs/phase2/B03_MODELS_AND_TRAINING.md`, B-ADR-04,
> B-ADR-11, B-ADR-13. Parts marked *(planned)* are designed and specified but not built yet.

**Pipeline.** An upload is checked (text-layer PDF, at most 50 MB and 1,500 pages, not password-protected,
duplicate by SHA-256), its type is detected from the first pages (RHP, DRHP or Prospectus), and a job runs
the stages in order: parse, sections, facts, financials, red flags, risk segmentation, risk features, risk
level, simplification, index, compare. Each stage writes its own file and an event; the browser follows the
events over server-sent events and can resume after a dropped connection. A failed stage marks its part of
the report ⚠️ and the others still finish.

**Red flags** *(planned, B1.4)*. Thirteen transparent checks (RF01–RF13 in B01: losses, operating cash flow,
debt, offer-for-sale share, the price sellers paid, promoter stake, vague use of money, court cases,
related-party dealings, customer concentration, price against peers, auditor remarks, pledged shares), each
OK, Watch or Concern from fixed thresholds, or Not available when an input is missing. A missing input is
never treated as a clean record.

**Risk segmentation** *(planned, B2.1)*. Inside the Risk Factors section, a new risk starts at a bold heading
at the left margin followed by normal text (from the PDF's font information); corpus texts without fonts
use numbered headings and sentence shape.

**Risk features.**
- *Category*: a DeBERTa-v3 classifier fine-tuned on the teacher's labels (base, 3 seeds; large, 1 seed),
  gated against a TF-IDF + logistic-regression baseline, served as ONNX int8 on CPU.
- *Novelty*: the share of distinct past companies (2018–2023) with a risk above cosine similarity τ
  (0.80, a placeholder until the spot check of E22); low novelty = unusual. Up to three similar past risks
  are shown.
- *Hedging*: hedge words counted with a lexicon; a risk that hedges heavily but states a past fact with a
  number gets the note "written cautiously, but it describes something that has already happened".
- *Seriousness*: a rule, not a model: the category's base weight, +1 for a hard fact, +1 for a material
  number, −1 for boilerplate. Importance for sorting = seriousness weight × (1 − novelty). The teacher's
  seriousness ratings are used only to check this rule (E17).

**Plain-English rewrites.** A teacher (Qwen3-14B-AWQ) writes rewrites for corpus risks; filtered pairs train
a QLoRA student (Qwen3-4B-Instruct-2507, LoRA r = 16) exported as GGUF Q4 for CPU (and run with vLLM on the
optional GPU job). Every rewrite of a user's document passes four checks before it is shown: every number
matches a number in the original, no forbidden phrase, at most 70 words, and no change in certainty (a
"may" must not become definite). A rewrite that fails is not shown; the original is. The top 15 risks by
importance are rewritten automatically and the rest when the reader asks.

**Risk level.** Points: Concern = 2, Watch = 1 per red flag, plus 1 per rare serious risk (high seriousness
and novelty below 0.10, at most 4). The score is the points divided by the most points the available checks
could give, so documents with fewer disclosures are not scored as safer (B-ADR-11). Low, medium and high are
thirds of the scores of past IPOs (2018–2023); the thresholds are placeholders until that run. The level is
always shown with its reasons, the percentile and a fixed disclaimer, and it is described as a summary of
disclosed risk, never as a rating or advice (B-ADR-13).

**Compare.** Peers come from the document's own Basis for Offer Price table (P/E, EPS, RoNW, NAV per share),
with the issuer's P/E computed from the offer price when the RHP leaves it blank. Four numbers (issue size,
offer-for-sale share, the price gap to what sellers paid, P/E) are placed among past IPOs as percentiles. No
judgement is attached.

**Serving.** Everything runs on the laptop: the API and the upload pipeline in one process, models through Ollama or llama.cpp, SQLite and local files; Supabase sign-in is optional. Google Cloud was removed when the credit ran out (B-ADR-16); nothing is hosted.
