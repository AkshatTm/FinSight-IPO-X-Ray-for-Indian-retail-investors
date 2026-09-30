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
