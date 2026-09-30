# 01 — Product Requirements Document (PRD)

**Product:** FinSight — IPO X-Ray for Indian retail investors
**Owner:** Akshat Tomar · **Build:** solo + Claude Code · **Deadline:** Sun 1 Nov 2026 (CSE472 submission: report + implementation + GitHub + live demo/viva)
**Status:** Approved for build · Version 3.0 (29 Sep 2026)

---

## 1. Summary

Retail investors in India apply to IPOs without reading the Red Herring Prospectus (RHP), a 400–700 page legal document. Those who try to use a general chatbot get confident answers that confuse lakh and crore, mix up the fresh issue with the offer for sale, and cannot show where a number came from.

FinSight opens an IPO and instantly shows a **fact sheet (the X-Ray)** where every figure is page-cited and clickable. A chat panel answers questions in English or Hindi (typed or spoken). Every number in every answer is checked by a deterministic, Indian-format-aware verifier and marked ✅ / ⚠️ / ❌, with an evidence drawer showing exactly why.

**Our technical contribution (not an API wrapper):**
1. A DeBERTa extractive-QA model **fine-tuned on automatically generated labels** (distant supervision) — zero manual training labels.
2. A **deterministic numeric verifier** that understands ₹, lakh/crore/million, Indian digit grouping and scale errors.
3. **Local, open-weight models only.** No paid LLM APIs at runtime.

**Hard rule:** FinSight never gives buy/sell/apply advice, never rates IPOs, never predicts listing gains (SEBI; §9).

---

## 2. Problem

| Pain | Evidence we'll show in the report/demo |
|---|---|
| RHPs are too long for retail investors | Page counts of the demo RHPs (we measure them) |
| General chatbots mis-scale Indian numbers | Frontier-LLM comparison (§8, E9 in `05_DATA_AND_EVALUATION.md`): we run our verifier on their answers and count ❌ |
| Answers aren't traceable | Chatbots give no page reference; FinSight gives page + highlighted box for every figure |
| Hindi-first users are underserved | Hindi voice question → Hindi answer with citations |

---

## 3. Users

| Persona | Description | What they need | Primary screen |
|---|---|---|---|
| **Priya, first-time IPO applicant** (primary) | 26, salaried, applies via a broker app, comfortable in Hindi, has never opened an RHP | "How much is new money vs promoters selling? What's the price band? What will they do with the money?" — in plain words, trustworthy | Workspace (X-Ray + chat) |
| **Rahul, finance/commerce student** (secondary) | Learning to read offer documents | Jump from a fact to the exact page; understand terms | Workspace + glossary |
| **Examiner / viva panel** (evaluation) | Grades CSE472 | Evidence of deep learning, fine-tuning, evaluation rigour, honest results | Model Lab, Inspector, How-it-works |
| **Recruiter / interviewer** (portfolio) | Skims GitHub for 2 minutes | A working demo, clean README, measured results | README, landing page, deployed link |

---

## 4. Goals and non-goals

**Goals**
- G-1 Every figure shown is traceable to a page and a highlighted region.
- G-2 Every number in a chat answer is verified or honestly flagged.
- G-3 Our fine-tuned extractor measurably beats the rules baseline and the pretrained model on at least half the fields (target, not promise; report honestly either way).
- G-4 Runs fully offline on Akshat's laptop (16 GB RAM, RTX 2050 4 GB) after setup.
- G-5 A deployed public version exists by the deadline (may be "lite": smaller LLM, slower chat).

**Non-goals**
- Investment advice, ratings, price/listing-gain prediction, grey market premium.
- OCR of scanned PDFs (detected and skipped with a warning).
- DRHPs (they contain `[●]` placeholders) — RHPs only in v1.
- Non-Indian markets.
- User accounts, payments, storing user data.

---

## 5. Feature scope and priorities

IDs are referenced from `07_ROADMAP.md` and PR titles.

### P0 — must ship (the pitch; never cut)
| ID | Feature | Notes |
|---|---|---|
| FR-01 | **IPO Library** of 12 curated demo IPOs | Cards with key facts, search |
| FR-02 | **X-Ray fact sheet** — 9 fields + 2 derived | Fields in §5.4 |
| FR-03 | **Click-to-source**: any figure → viewer jumps to page, exact words highlighted | < 300 ms |
| FR-04 | **Chat with citations** `[1]…[5]`, hover preview, click → page | Streaming (SSE) |
| FR-05 | **Numeric verifier** with ✅ ⚠️ ❌ badges + **evidence drawer** | Scale mismatch is always ❌ |
| FR-06 | **Abstain** when retrieval is weak ("not found in the prospectus") | Never guess |
| FR-07 | **Advice guard** (EN / HI / Hinglish) — polite refusal + facts | SEBI note |
| FR-08 | **Extractor ladder**: rules vs pretrained QA vs fine-tuned QA, with real numbers | Model Lab page |
| FR-09 | **Demo mode** + presenter hotkeys (replays *real recorded* outputs) | For viva reliability |

### P1 — should ship
| ID | Feature |
|---|---|
| FR-10 | Hindi voice input (ASR) + Hindi answers |
| FR-11 | Pipeline Inspector (stages, timings, retrieval scores, prompt, checks) |
| FR-12 | Unit toggle (crore / million / lakh / full ₹) re-renders every figure |
| FR-13 | Extractor-compare toggle on X-Ray cards (3 extractors side by side vs gold) |
| FR-14 | Consistency checks on X-Ray (total = fresh + OFS; price band sanity) |
| FR-15 | BiLSTM-CRF extractor rung (syllabus depth) |
| FR-16 | Frontier-LLM comparison + verifier run on frontier answers |
| FR-17 | NLI check for non-numeric claims (inference-only model) |
| FR-18 | Trained advice-intent classifier (replaces keyword guard; becomes a ladder entry) |
| FR-19 | **Glossary tooltips** (EN/HI) for terms like OFS, fresh issue, anchor investor, face value — static, reviewed text, no model | new in v3 |
| FR-20 | Public deployment (frontend + CPU backend, "lite" chat) |
| FR-21 | How-it-works page with interactive architecture diagram |

### P2 — only if everything above is green
| ID | Feature |
|---|---|
| FR-30 | Compare two IPOs side by side (reuses X-Ray JSON) |
| FR-31 | Numeral playground ◇ and extractor playground ◇ (token start/end score bars) |
| FR-32 | Command palette ◇ |
| FR-33 | v1.1 fields: promoter holding pre/post, litigation counts, top-customer concentration |
| FR-34 | QLoRA fine-tune of the generator (paid Colab) |
| FR-35 | Cross-IPO facts ("OFS share above the median of 2023–26 mainboard IPOs") — facts only |
| FR-36 | Upload your own RHP (background job, progress UI) |
| FR-37 | Publish the fine-tuned extractor on Hugging Face Hub with a model card (same NC-SA terms as training data) |

### 5.4 X-Ray fields (v1)
| Field id | Type | Example |
|---|---|---|
| `total_issue_size` | money | ₹1,250.00 crore |
| `fresh_issue_size` | money | ₹800.00 crore |
| `ofs_size` | money or share count | ₹450.00 crore / 1,23,45,678 shares |
| `price_band` | money range | ₹440 – ₹463 per share |
| `face_value` | money | ₹2 per share |
| `book_running_lead_managers` | list[text] | … |
| `registrar` | text | … |
| `promoters` | list[text] | … |
| `objects_of_offer` | table rows (purpose, amount) | … |
| derived `fresh_share_pct`, `ofs_share_pct` | percent | computed, no model |

---

## 6. User stories and acceptance criteria

**US-1 X-Ray (FR-02, FR-03)**
*As Priya, I want the key facts of an IPO on one screen so I don't read 500 pages.*
- Given a curated IPO, when I open its workspace, the X-Ray renders in < 1 s (precomputed).
- Each card shows value, page chip, and a verification badge.
- When I click a card, the document viewer shows that page with the source words highlighted within 300 ms.
- If extractors disagree or the value is missing, the card shows ⚠️ with the reason — never a made-up value.

**US-2 Trustworthy chat (FR-04, FR-05)**
*As Priya, I want to ask questions and know whether each number is correct.*
- Answers stream; every sentence carries at least one `[n]` citation.
- After streaming, each number in the answer is underlined and gets ✅ / ⚠️ / ❌ one by one.
- Clicking a badge opens the evidence drawer: answer value vs document value (both normalized), matched passage, plain-language reason, "Show in document".

**US-3 The catch (FR-05)**
*As an examiner, I want to see the system catch a unit error.*
- Given the question "Is the fresh issue ₹X lakh?" where the RHP says ₹X crore, the verdict is ❌ with reason "Scale mismatch — differs by exactly 100× (lakh vs crore)".

**US-4 Honest abstention (FR-06)**
- When no passage passes the rerank threshold, no text is generated; an abstain card shows the closest passage.

**US-5 Advice guard (FR-07)**
- "Should I apply?", "kya ye IPO lena chahiye?", "इस IPO में निवेश करूँ?" → refusal + SEBI note + key X-Ray facts. No LLM call is made.

**US-6 Hindi voice (FR-10)**
- Press mic, speak a Hindi question, see the transcript (editable), receive a Hindi answer with citations; numbers still verified.

**US-7 Model Lab (FR-08)**
- The ladder table shows EM, token F1 and normalized-value accuracy per extractor (mean ± std over 3 seeds where trained), read from `eval_results/`, with sample size shown.

---

## 7. Non-functional requirements

| Area | Requirement (laptop, "full" profile) |
|---|---|
| X-Ray load | < 1 s (served from precomputed JSON) |
| Click-to-highlight | < 300 ms (active IPO's page images prefetched) |
| Chat | Time to first token ≤ 4 s; full answer ≤ 15 s with the chosen small LLM; verification ≤ 300 ms |
| Voice | Transcript of a 5 s Hindi clip ≤ 6 s |
| Memory | Backend process ≤ ~5.5 GB RAM, LLM ≤ ~3.6 GB VRAM (see `02_ARCHITECTURE.md` §12). A `dev_light` profile must run while Claude Code, VS Code and a browser are open |
| Offline | After setup, no internet needed at runtime |
| Reliability | No stack traces reach the UI; every failure has a friendly message and a degraded mode |
| Accessibility | Badges = icon + word + colour; keyboard navigable; `prefers-reduced-motion` respected; 1366×768 projector + phone layouts |
| Reproducibility | Every table/figure in the report regenerated by a script from `eval_results/`; fixed seeds |
| Honesty | Outputs are never hand-edited; demo mode replays recorded real outputs only |

---

## 8. Success metrics (targets; the report states actuals, hit or miss)

| Metric | Target | Where measured |
|---|---|---|
| Weak-label precision (50-sample audit) | ≥ 85 % | E1 |
| Fine-tuned vs pretrained QA, normalized-value accuracy | Fine-tuned better on ≥ 5 of 8 extractive fields | E3 |
| Verifier recall on scale-mismatch seeded errors | ≥ 95 % | E5 |
| Verifier F1 over all seeded error types | ≥ 0.85 | E5 |
| Retrieval Recall@5 on hand-written questions | ≥ 0.80 | E6 |
| Advice guard: block rate on advice set / false-block rate on factual set | ≥ 95 % / ≤ 5 % | E8 |
| Frontier comparison | FinSight ≥ frontier on numeric accuracy + citation; report where frontier wins | E9 |
| Laptop latency | Meets §7 | E10 |

---

## 9. Ethics, legal, compliance

- **No investment advice.** SEBI requires registration for research analysts and investment advisers; "educational" disclaimers do not make unregistered advice acceptable. FinSight explains what the document says and refuses advice questions.
- **Licences.** The IPO dataset(s) we train on are CC BY-NC-SA 4.0 (non-commercial, share-alike). Fine for coursework and a portfolio; stated in README, report and any released model card.
- **Data.** Public regulatory disclosures only. No user data stored; voice audio is processed and discarded.
- **Honesty.** Small sample sizes stated; losses reported; no edited outputs.

---

## 10. Milestones (details in `07_ROADMAP.md`)

| Milestone | Date | Outcome |
|---|---|---|
| G0 Foundation | Wed 30 Sep | Repo + CI green, environment works, data inspected |
| G1 Documents understood | Tue 6 Oct | 12 demo RHPs parsed, sections found, numeral normalizer done |
| G2 Our model | Wed 14 Oct | X-Rays for all demo IPOs, extractor ladder with real numbers |
| G3 Trustworthy chat | Tue 20 Oct | Chat + verifier + guard + voice end to end (CLI + API) |
| G4 Full product locally | Fri 23 Oct | UI on real API, Playwright demo test green |
| G5 Feature freeze | Mon 26 Oct | Deployed; depth items done or cut |
| Submission | Sun 1 Nov | Report, slides, video, README, tagged v1.0.0 |

---

## 11. Out of scope (explicitly)

Ratings, predictions, portfolio tracking, broker integration, OCR, DRHP support, SME IPOs in the demo set (they may still appear in training data), mobile apps, user accounts.

## 12. Open questions / risks owned by Akshat

1. **Teacher approval** of an off-list topic — pitch in Appendix A. Fallback: frame as an extension of listed Project 23.
2. **Training-data contents** — confirm on Day 1 what the Hugging Face IPO dataset actually contains (full RHP text? PDF links?). Plan B in `05_DATA_AND_EVALUATION.md` §1.3.
3. **Laptop headroom** — measured in Phase 0; may force the 2B LLM.

---

## Appendix A — Pitch to the teacher

FinSight is built from the same techniques as the listed projects, applied to one real problem:

| Listed project | What FinSight uses from it |
|---|---|
| 23 InfoXtract (extraction + verification) | Field extraction + verification against source — FinSight's core |
| 15 AskGov (fine-tune BERT for extractive QA) | Our fine-tuned DeBERTa extractive-QA model |
| 18 ReportHub (PDF ingestion + section tagging) | RHP parsing and section detection |
| 12 NyayaNER / 5 AnnadataAI (BiLSTM-CRF NER) | BiLSTM-CRF extractor rung |
| 8 PromptCraft (hallucination flagging) | Numeric verifier with ✅ ⚠️ ❌ |

*"Ma'am, I'd like to take Project 23's idea — extract and verify information — and apply it to IPO prospectuses that retail investors can't read. It combines techniques from Projects 15, 18 and 12 with a baseline → deep learning comparison and won't duplicate anyone's topic. If you prefer, I'll frame it strictly as an extension of Project 23."*
