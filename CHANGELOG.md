# Changelog

All notable changes to FinSight. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/). Each release is a git tag; the phase gates (`docs/gates/`) record the evidence behind it.

## [Unreleased] — Phase 2

### Removed

- Google Cloud (Cloud Run, Cloud Storage, GPU job, deploy workflows, `cloud` / `cloud_gpu` profiles, vLLM backend, cost estimates and the `/admin/costs` page) after the credit ran out (B-ADR-16). The product runs locally.

### Fixed

- Upload quotas and the admin job list compared an IST day start as if it were UTC on SQLite, so limits were wrong between 18:30 and 24:00 UTC.

### Added

- Upload any IPO offer document (RHP, DRHP or Prospectus): validation, document type, duplicate check by SHA-256, daily quotas, kill switch and 30-day retention.
- Storage (local and Cloud Storage), database (SQLite and Postgres via SQLAlchemy Core and Alembic) and a job runner with resumable server-sent events.
- Upload, processing and "My uploads" screens; the report page with the risk level card, red flags, risks and compare tabs (on synthetic mocks until real fixtures exist).
- Risk factors: novelty against past IPOs, hedging and hard-fact checks, numbers, and a risks API.
- Risk level: points from red flags and rare serious risks, normalised over the checks that ran, placed among past IPOs, always with its disclaimer.
- Compare: peers from the basis-for-offer-price table and percentiles among past IPOs.
- Teacher, category classifier and simplifier code with Kaggle notebooks (training runs in local sessions).
- Google Cloud infrastructure as code (Cloud Run API, CPU worker job, optional L4 GPU job, Cloud Build); nothing deployed.
- Documentation site (MkDocs Material) with generated reference pages, evaluation page, model cards, datasheets, runbooks, tutorials and how-to guides.

### Changed

- Hosting moved to Google Cloud Run + Supabase + Cloud Storage + Vercel (B-ADR-04).
- The frontend's API origin is `FINSIGHT_API_ORIGIN` everywhere.
- Logs are JSON on Cloud Run, with `doc_id`, `job_id` and `stage` on stage failures.
- Docstring coverage is 84 %; CI fails below 70 % and on a docs build warning.

## [0.4.0] — 2026-10-02

### Added

- The full user interface on the real API (gate G4): the IPO library, the workspace with the cited fact sheet and document viewer, verified chat in English and Hindi, the Model Lab and the landing page.

## [0.3.0] — 2026-10-02

### Added

- Trustworthy chat and API (Phase 1 parts 3–4, gate G3): retrieval (BM25, dense, reranking), cited answers from a local LLM, the ✅/⚠️/❌ number verifier, the advice guard and the FastAPI service with server-sent events.

## Earlier

Phase 1 parts before v0.3.0 (parsing, normalisation, extractors, weak labels, the extractor ladder) are recorded in `docs/PROGRESS_PHASE1.md` and the gate files.

[Unreleased]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/releases/tag/v0.3.0
