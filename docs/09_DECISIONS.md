# 09 — Decision Log (ADRs)

Each decision: context → decision → consequences. Status: `accepted` (Akshat approved), `proposed` (Claude Code added, awaiting approval), `superseded by ADR-x`. Append new ADRs at the end using the template. These entries double as viva answers to "why did you choose X?".

---

### ADR-001 India-only scope — accepted (Sep 2026)
**Context:** v1 planned US (SEC) + India. **Decision:** India only, RHPs of mainboard IPOs. **Consequences:** a sharper story (retail IPO investors, lakh/crore), one document type to parse well, a clear gap vs prior English/Korean financial-hallucination work.

### ADR-002 No hosted LLM APIs at runtime — accepted
**Context:** API wrappers are common and hard to defend as "our model". **Decision:** open-weight models only, run locally (Ollama) and on CPU when deployed. **Consequences:** smaller LLMs → we compensate with retrieval quality, strict prompts and the deterministic verifier. Frontier models appear only as a comparison baseline (E9).

### ADR-003 Distant supervision for the extractor — accepted
**Context:** no labelled RHP QA dataset exists; manual labelling thousands of examples is impossible solo. **Decision:** seed values from high-precision cover-page rules, propagate to other passages by normalized value match, train DeBERTa extractive QA (SQuAD 2.0 format). **Consequences:** label noise → measured by a 50-sample audit; the model can generalize to phrasings the rules miss.

### ADR-004 Deterministic numeric verifier — accepted
**Context:** NLI/LLM-judge faithfulness metrics are known to struggle on bare numbers. **Decision:** parse and compare numbers in code with explicit reason codes; scale mismatch is always ❌. **Consequences:** explainable, testable, near-100 % on scale errors; qualitative claims need a separate NLI check (P1).

### ADR-005 Never use rating labels; never advise — accepted
**Context:** the IPO dataset includes Apply/Avoid ratings; SEBI requires registration for advice. **Decision:** ignore rating labels entirely; advice guard refuses. **Consequences:** clean ethics section; no "prediction" feature.

### ADR-006 Timeline: single deadline 1 Nov, no 12 Oct demo — accepted (29 Sep 2026)
**Context:** the v2 plan was built around a 12 Oct presentation; that presentation is no longer required. **Decision:** one timeline to Sun 1 Nov with freeze on Mon 26 Oct; depth items (gold v2, BiLSTM-CRF, frontier comparison) move into the main plan. **Consequences:** stronger evaluation; gates G0–G5 in `07_ROADMAP.md`.

### ADR-007 Local first, deploy after stable — accepted
**Decision:** full product on the laptop by G4; a "lite" public deployment (Vercel + Hugging Face Space CPU) by G5. **Consequences:** `deploy_cpu` profile with smaller LLM; precomputed artifacts make most pages instant.

### ADR-008 Laptop constraints drive model sizes — accepted
**Context:** 16 GB RAM (~8 GB used by Windows + tools), RTX 2050 with 4 GB VRAM. **Decision:** LLM 2–4 B at 4-bit on GPU (bake-off decides), encoders as ONNX int8 on CPU online, lazy ASR, `dev_light` profile for daily coding, offline pipeline runs with Ollama stopped. **Consequences:** real measurements recorded in Phase 3.1 (new ADR).

### ADR-009 SQLite + FAISS + files, no database server — accepted
**Decision:** ≤ 50 IPOs fit easily; zero ops. Postgres/pgvector only if deployment needs it.

### ADR-010 Page images + word boxes instead of a PDF viewer — accepted
**Decision:** render pages to WebP and overlay boxes. **Consequences:** exact highlights, fast, identical behaviour on phones; no text selection in the viewer (acceptable).

### ADR-011 Windows-native tooling: uv + poethepoet + ruff — accepted
**Decision:** no Make, no WSL; ruff replaces black/isort/flake8. **Consequences:** same commands in Git Bash, PowerShell and CI.

### ADR-012 Rebase-merge PRs — accepted
**Decision:** keep every commit on `main` (see `08_GIT_WORKFLOW.md` §1). **Consequences:** history must stay clean → amend/rebase locally before pushing.

### ADR-013 Paid Colab is optional — accepted
**Context:** all P0/P1 training fits Kaggle's free GPUs; student AI Pro includes Colab units but only on paid plans. **Decision:** buy only if QLoRA (FR-34) is committed by ~20 Oct. **Consequences:** expected spend ₹0.

### ADR-014 Visual concept "tick and tie" — accepted
**Decision:** auditor's verification marks as the brand; stamp-ink blue accent; IBM Plex Sans + Plex Sans Devanagari. **Consequences:** a design rooted in the subject rather than a generic dark dashboard; see `03_UI_UX_DESIGN.md`.

### ADR-015 Cross-lingual retrieval, not translation — accepted
**Decision:** bge-m3 embeds Hindi questions and English passages into one space; the LLM answers in Hindi while copying numbers exactly. **Consequences:** no translation model; numbers in Hindi answers are verified the same way.

### ADR-023 Two documents per IPO: RHP and final Prospectus — proposed (30 Sep 2026)
**Context:** the downloaded RHPs leave the offer price, total issue size and the OFS rupee amount as `[●]`; the final Prospectus (filed after pricing) fills them in. Both exist for all 10 demo IPOs.
**Options:** (A) RHP only, show `[●]` as ⚠️ everywhere; (B) RHP + Prospectus parsed by the same pipeline; (C) also require the price-band advertisement.
**Decision:** B. Fields become `fresh_issue_size`, `ofs_shares` (count), `ofs_amount`, `offer_price`, `price_band` (optional; RHP or price-band ad if easy to find) and `total_issue_size`. Every value cites its document and PDF page; a `[●]` in the RHP is a normal ⚠️ and the Prospectus value is shown beside it as `companion`.
**Consequences:** `doc_type` on parsed docs, passages and candidates; two sets of page images; gold v1 records the document. `offer_price` is rules-only on the Prospectus cover and outside the QA ladder (no positives in RHP-derived training text). The Prospectus is the more authoritative source for final prices; chat retrieval indexes both, and answers say which document a figure came from.

### ADR-024 Contract-first API skeleton — proposed (30 Sep 2026)
**Context:** the frontend starts in Phase 1 but the real API arrives in Phase 4, and OpenAPI does not describe SSE event payloads by default.
**Decision:** P0.3 ships a FastAPI skeleton where every route in `06` returns 501 with its response model, and each SSE event is a pydantic model registered in OpenAPI. `poe gen-openapi` writes a committed `openapi.json` and the frontend generates types from it from F1 onward.
**Consequences:** shapes are agreed before either side is built; contract tests exist from the start; changing a shape means changing `06`, the model and `openapi.json` in one PR.

### ADR-025 Page numbering: PDF page primary, printed page secondary — proposed (30 Sep 2026)
**Context:** RHPs print their own page numbers, which differ from the PDF page index; an examiner opening the PDF would see a mismatch.
**Decision:** all page numbers in the API, viewer chips and citations are PDF pages (1-indexed). The printed page number is stored alongside and shown in the popover.
**Consequences:** `Page.printed_page` is read from the footer where present (nullable); "p. 12" in the UI always means the 12th PDF page.

### ADR-026 Dev/test split of the demo set; gold v1 labelled in Phase 1 — proposed (30 Sep 2026)
**Context:** writing rules and picking extractors on the same IPOs used for the reported ladder would leak test information; the original plan labelled gold after the X-Ray already existed.
**Decision:** 3 dev / 7 test IPOs. Rules, thresholds, prompts and per-field extractor choice are tuned on dev only; reported numbers use test. Gold v1 is labelled blind in Phase 1 (P1.7), before any extractor exists. Proposed dev set: `hexaware-technologies-2025` (pure OFS), `ather-energy-2025`, `urban-company-2025`; confirmed in P0.4.
**Consequences:** fewer test IPOs (7), so results are reported with bootstrap intervals and per-field numbers are descriptive (ADR-031). Gold v2 (10 more held-out IPOs) increases the test size later.

### ADR-027 Scale-mismatch requires a scale signal — proposed (30 Sep 2026)
**Context:** the rule "a 10/100/1000× difference is always a scale mismatch" also fires on genuinely different values, e.g. face value ₹10 vs ₹1.
**Decision:** `scale_mismatch` only when the ratio is 10ᵏ (k = 1–3) **and** (the scale words differ **or** the printed digits are identical). Any other 10ᵏ gap is `wrong_value`. Scale mismatch is always ❌.
**Consequences:** fewer mislabelled reasons in the evidence drawer; a unit test per case; the seeded-error harness includes a "10× wrong value" negative.

### ADR-028 Numeral policy for Hindi — proposed (30 Sep 2026)
**Context:** Hindi answers may write scale words as लाख/करोड़/हज़ार/अरब and currency as रुपये; documents could contain Devanagari digits.
**Decision:** the normalizer parses Hindi scale words, रुपये and Devanagari digits. Generated answers always use Western digits (0–9) and may use Hindi scale words. Devanagari digits are never output.
**Consequences:** ≥ 12 Hindi cases in the P1.4 table; Hindi answers are verified through the same path as English.

### ADR-029 Dependency groups; no torch in the API image or CI — proposed (30 Sep 2026)
**Context:** the online path uses ONNX int8 encoders, Ollama and CTranslate2, none of which need PyTorch; torch costs ~1 GB RAM and a large CI download.
**Decision:** uv dependency groups `api`, `ml` (torch, transformers, offline and Kaggle), `asr`, `dev`. CI installs `api` + `dev` only; the CUDA wheel is pinned under `ml`.
**Consequences:** faster CI, smaller deploy image, lower RAM; tests needing torch are marked `slow`.

### ADR-030 One primary package per sub-phase; capped `inspect` command — proposed (30 Sep 2026)
**Context:** the roadmap's sub-phases wire several packages (e.g. P2.2 touches extract, verify and pipeline), and Claude Code may not read PDFs or raw data yet must debug parsing.
**Decision:** rule reworded to one primary package per sub-phase with wiring elsewhere through `__init__.py`. `finsight.pipeline inspect` prints ≤ 40 lines and may write ≤ 30 truncated snippets to `data/samples/`.
**Consequences:** `CLAUDE.md` updated; debugging works from summaries, not source documents.

### ADR-031 Headline claim and ladder settings — proposed (30 Sep 2026)
**Context:** with 7 test IPOs one IPO moves a field's score by 10+ points; cover-page sentences are templated so rules read them almost perfectly.
**Decision:** the headline result is overall NVM with a bootstrap CI (by IPO) and a paired per-IPO comparison between rungs; per-field results are descriptive. Every ladder is reported for the **full document** and **body-only** (cover masked).
**Consequences:** the PRD target "better on ≥ 5 of 8 fields" is treated as a descriptive goal; the report states which claims the sample supports.

### ADR-032 LLM memory and thinking policy — proposed (30 Sep 2026)
**Context:** first measurement on the laptop: with the model unloaded RAM was 10.2 of 15.4 GB; with `qwen3.5:2b` loaded 12.0 GB (Ollama ≈ 1.8 GB). Ollama reported 3.0 GB at context 4096, split 37 % CPU / 63 % GPU, so part of the model ran on the CPU. Thinking mode was on by default and made answers very slow.
**Decision:** thinking is always disabled (`think: false`, tested). `dev_light` uses `qwen3.5:0.8b`. For `full`, the LLM must fit fully on the GPU: prefer a text-only GGUF and the smallest context that holds 5 passages, chosen from measurements in P3.1/P3.2.
**Consequences:** the 2B/4B choice waits for the bake-off; the 02 section 12 budget uses measured numbers; the live demo closes other apps.

---

## Pending ADRs (to be written during the build)

| # | Topic | Phase |
|---|---|---|
| ADR-016 | Training corpus source (dataset contents, Plan A/B) | P0.4 |
| ADR-017 | Table extractor: pdfplumber vs Docling | P1.3 |
| ADR-018 | Extractor chosen per field (from ladder results) | P2.6 |
| ADR-019 | Measured memory/latency; device assignments | P3.1 |
| ADR-020 | LLM choice (bake-off) | P3.2 |
| ADR-021 | ASR choice (bake-off) | P3.5 |
| ADR-022 | Deployment target details | P6.1 |

## Template

```markdown
### ADR-0NN <title> — proposed (<date>)
**Context:** <what forced a decision; numbers if any>
**Options:** <A, B, C with one-line trade-offs>
**Decision:** <what we chose>
**Consequences:** <what changes, what we give up, how we'd revisit>
```
