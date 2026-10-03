# B08 — Decisions for Big Phase 2 (B-ADRs)

Status meanings as in `09_DECISIONS.md`. Claude Code adds these to `docs/09_DECISIONS.md` (prefixed **B-ADR**) in B0.2 as **proposed**; Akshat marks them accepted.

### B-ADR-01 Reframe: from fact lookup to risk understanding — proposed (4 Oct 2026)
**Context:** Facts like issue size can be found with Ctrl+F; the hard part for beginners is understanding risks hidden in legal language.
**Decision:** Phase 2 adds upload-any-document, red flags, plain-English risk report, risk level and comparisons. Phase 1 features stay.
**Consequences:** New models and cloud deployment; Phase 1 evaluation remains valid for the facts/chat parts.

### B-ADR-02 Risk level (Low/Medium/High) with reasons — proposed
**Context:** Users want guidance; buy/avoid advice requires SEBI registration and can't be predicted reliably.
**Decision:** Show a transparent, corpus-relative risk level with reasons and a fixed disclaimer. Never buy/apply/avoid wording. Thresholds from percentiles of past IPOs, not from outcomes.
**Consequences:** Advice-adjacent; mitigated by transparency, wording rules and validation (E21). Can be put behind a click if required.

### B-ADR-03 Outcome data used only for validation (narrows Phase 1 ADR-005) — proposed
**Decision:** Listing outcomes and broker opinions in the dataset may be used **only to evaluate** the risk level (E21), never to train or tune a predictor, never shown in the product except the Model Lab result.

### B-ADR-04 Hosting: Google Cloud Run (CPU API + CPU job + optional L4 GPU job) + Supabase + GCS + Vercel — proposed (revised twice, 3 Oct 2026)
**Context:** Google Cloud offers GPUs on Cloud Run (L4, scale to zero, per-second billing), which the simplifier and dense indexing benefit from. Billing needs a paid account (₹1,000 prepayment; free-trial accounts get no GPUs), which Akshat will set up later. An interim Azure-for-Students plan was dropped the same day.
**Decision:**
- Google Cloud in asia-southeast1: a Cloud Run CPU API service; a Cloud Run CPU worker job for every stage; an optional Cloud Run L4 GPU job (vLLM offline + bge-m3) for simplify + index (`cloud_gpu`); GCS for files with signed URLs; Artifact Registry; Secret Manager.
- Supabase for Auth (Google) and Postgres (pooler); Vercel for the site.
- Code stays CPU-first: without the GPU job, the CPU job rewrites the top 15 risks with the student GGUF Q4 and the rest on click.
- Nothing is deployed, enabled or paid for without Akshat's explicit "go".
- Supersedes ADR-022 as the primary deployment; ADR-022's HF Docker Space stays as a **paid, optional** showcase-only fallback (HF PRO).
**Consequences:** One cloud vendor, GPU when billing allows; until then all deployment work is code, scripts and runbooks; budget alert ₹2,000/month and instance caps from the first deploy.

### B-ADR-05 Google login for uploads; public read for reports — proposed
**Decision:** Supabase Auth with Google; 3 uploads/user/day, 10/day global, `UPLOADS_ENABLED` kill switch; same-file dedupe by a server-recomputed SHA-256; reports of public documents viewable by link; non-showcase docs deleted after 30 days.

### B-ADR-06 Open-weight models only (re-affirmed) — proposed
**Decision:** No hosted LLM APIs. Teacher, student, chat and classifiers are open-weight, self-hosted.

### B-ADR-07 Teacher → student distillation for simplification — proposed
**Decision:** A Qwen-family (Apache-2.0) teacher in AWQ 4-bit (~14B on Kaggle T4 with vLLM; ~32B if Colab Pro is bought), inference only, produces filtered labels and rewrites for ~5,000 corpus risks after a 500-item pilot. A Qwen ~3–4B student is fine-tuned with QLoRA on a Kaggle T4 and served as GGUF Q4 on CPU via llama.cpp; an ~8B variant only if a GPU host appears.
**Consequences:** Free Kaggle GPU (≈ 10–11 h of the weekly quota); licences checked; the trained model inherits the corpus's non-commercial terms.

### B-ADR-08 Classifier: base on Kaggle, large on Colab, pick by dev — proposed
**Decision:** DeBERTa-v3-base (3 seeds, Kaggle) and DeBERTa-v3-large (1 seed, Kaggle; Colab optional; first to cut); select by dev macro-F1; report both on gold-150; serve as ONNX int8 on CPU.

### B-ADR-09 Course framing update — proposed
**Decision:** Report framing becomes "Making Indian IPO risk disclosures understandable": extraction, classification, semantic novelty, distillation-based simplification, deterministic verification. Still presented as an extension of listed Project 23 (extract + verify) plus Projects 15/18/12/8 techniques.

### B-ADR-10 Risk report English only — proposed
**Decision:** Risk report (red flags, risks, risk level, compare) in English; UI chrome and chat remain bilingual.

### B-ADR-11 Risk level: normalised points over a 2018–2023 reference population — proposed (3 Oct 2026)
**Context:** The corpus is page text only and mostly 2009–2017. Several red-flag inputs (WACA, post-issue promoter holding, pledges, the ICDR summary tables) exist only in newer documents, so older IPOs would score low because of NA checks and every new upload would look High.
**Decision:** score = points ÷ maximum points over the checks available for that document (+ up to 4 risk points); thresholds are the thirds of the 2018–2023 corpus distribution; `corpus_n` comes from `configs/risklevel.yaml` and is shown in the UI. Novelty also uses the 2018–2023 bank. A `behind_click` flag can hide the level behind a click.
**Consequences:** A smaller reference set (~200); fairer comparison; E21 measured on the same population.

### B-ADR-12 Kaggle-first training — proposed (3 Oct 2026)
**Decision:** Teacher, classifiers and student all train or run on Kaggle (T4 / T4×2), launched by local sessions through the Kaggle CLI (ADR-042). Colab is optional: if bought, the teacher may move to ~32B and Akshat runs `COLAB_STEPS_*.md`.
**Consequences:** No Colab dependency on the critical path; fp16 on T4 (no bf16).

### B-ADR-13 Forbidden phrases, not forbidden words — proposed (3 Oct 2026)
**Context:** A word list (buy, sell, apply, invest, safe) would flag our own copy ("selling shareholders", "It won't tell you whether to apply or buy") and normal risk text ("investors", "safety").
**Decision:** `configs/forbidden_phrases.yaml` holds instruction-style patterns plus an allow-list; one filter in `guard` is used for UI copy tests, rewrite post-checks and teacher filtering.

### B-ADR-14 doc_id beside ipo_id; showcase primary doc = RHP — proposed (3 Oct 2026)
**Decision:** `doc_id = sha256[:16]` for every document; showcase docs are mapped in `configs/demo_ipos.yaml`; a showcase report's primary doc is the RHP and its `companion_doc_id` is the Prospectus, which supplies prices; `/ipos/[id]` redirects to `/reports/[doc_id]`. Core `DocType` gains `drhp`; `unknown` is only a detection result.

### B-ADR-15 Committed real-section fixture pack — proposed (3 Oct 2026)
**Context:** Cloud sessions have only the repo; Phase 1 rules forbid committing data.
**Decision:** `tests/fixtures/real/` may hold real section text, word boxes and tables from public offer documents and short corpus excerpts (gzip JSON, ≤ 5 MB per file, ≤ 20 MB total), written only by `scripts/export_fixtures.py`, with sources and licences in its README. No PDFs, no weights, no personal data beyond what the public filings print (privacy redaction applies to anything displayed).

### Phase 1 ADRs affected
- ADR-005 → narrowed by B-ADR-03.
- ADR-022 (deployment target) → superseded by B-ADR-04 as the primary deployment; kept as the showcase-only fallback (cut 6).
- ADR-029 (dependency groups) → extended in B1.2/B2.4a (`sqlalchemy`, `alembic`, `psycopg`, an S3 client; `ml-cpu` for scikit-learn/ONNX).
- `12_FRONTEND_SPEC.md` §5.8 line "It won't rate or rank IPOs" → replaced per B05 §2.
- Landing "What FinSight won't do" and About "Known limits" → updated per B05.
