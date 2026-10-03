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

### B-ADR-04 Google Cloud Run (CPU API + L4 GPU job + vLLM service), Vercel, Supabase — proposed
**Context:** "Fast and public" with student credits; Cloud Run L4 GPUs scale to zero, bill per second and need no quota request for first use.
**Decision:** All hosting on Google Cloud + Vercel + Supabase. Azure/AWS unused (backup only).
**Consequences:** Cold starts handled in the UI; budget alerts and instance caps from day 1.

### B-ADR-05 Google login for uploads; public read for reports — proposed
**Decision:** Supabase Auth with Google; 3 uploads/user/day, 30/day global; same-file dedupe; reports of public documents viewable by link.

### B-ADR-06 Open-weight models only (re-affirmed) — proposed
**Decision:** No hosted LLM APIs. Teacher, student, chat and classifiers are open-weight, self-hosted.

### B-ADR-07 Teacher → student distillation for simplification — proposed
**Decision:** A ~30B open teacher (Colab A100, inference only) produces filtered labels and rewrites for ~5,000 corpus risks; a 7–9B open student is fine-tuned with QLoRA and served with vLLM.
**Consequences:** Uses Colab compute units; licences of both models checked; trained model inherits non-commercial terms of the corpus.

### B-ADR-08 Classifier: base on Kaggle, large on Colab, pick by dev — proposed
**Decision:** DeBERTa-v3-base (3 seeds, Kaggle) and DeBERTa-v3-large (Colab); select by dev macro-F1; report both on gold-150.

### B-ADR-09 Course framing update — proposed
**Decision:** Report framing becomes "Making Indian IPO risk disclosures understandable": extraction, classification, semantic novelty, distillation-based simplification, deterministic verification. Still presented as an extension of listed Project 23 (extract + verify) plus Projects 15/18/12/8 techniques.

### B-ADR-10 Risk report English only — proposed
**Decision:** Risk report (red flags, risks, risk level, compare) in English; UI chrome and chat remain bilingual.

### Phase 1 ADRs affected
- ADR-005 → narrowed by B-ADR-03.
- ADR-022 (deployment target) → superseded by B-ADR-04.
- `12_FRONTEND_SPEC.md` §5.8 line "It won't rate or rank IPOs" → replaced per B05 §2.
- Landing "What FinSight won't do" and About "Known limits" → updated per B05.
