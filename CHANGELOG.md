# Changelog

All notable changes to FinSight. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/). Each release is a git tag. Numbers quoted here come from [`eval_results/final/FINAL_SCORECARD.md`](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/final/FINAL_SCORECARD.md).

## [Unreleased]

Nothing yet.

## [1.1] — 2026-11-07

The final version: Phase 4's product work, the final session's fixes, English only, and the documentation rewrite. Pipeline version 4.2.

### Added

- **Summary of the Offer Document (SOD) engine** (CC-05, C-ADR-27): reads the RHP's own summary, or the chapters it summarises when there is none; `sod.json` with financial rows, ratios, strengths, promoter holding before and after, and the price band; served as `sod` in the report response. Decided red-flag checks over 289 RHPs went from 1,561 to 1,714; Jio Platforms from 1 to 7 of 13.
- **Financials tab** (CC-06): three fiscal years and the stub period, EPS, NAV, PAT margin, debt to equity, return on net worth, with a unit switch.
- **Cache v2** (CC-04): a stored analysis is valid for the PDF hash + `pipeline_version` + the model fingerprint; a model preflight before each job with "Analyse without it"; a degraded status that is never cached as complete; **Re-analyse** and **Delete** in the report and the API (`POST /api/docs/{doc_id}/reanalyse`, `DELETE /api/docs/{doc_id}`).
- **`start.bat` / `stop.bat`**: a menu launcher (start, stop, restart, status) that starts Ollama, the API and the web app in minimised windows, frees ports 8000 and 3000, and opens the app in Edge.
- `scripts/preload.py` (resumable re-analysis through the running app, with stage timings) and `scripts/purge_degraded.py`.
- The "Charcoal & Saffron" redesign: an interactive X-ray lens hero, a stats strip, and charts across the report and library.
- Phase 4 hand-off pack in `ml/handoff/` and the L2 event-label set (1,007 AI-labelled sentences; unused).
- Documentation: a rebuilt docs site (getting started, user guide, architecture, data, model cards in the Hugging Face format, evaluation and reproduction, API guide with curl, every config key, development, operations, decisions, history, glossary, FAQ), `CITATION.cff`, issue templates, `scripts/check_links.py` and a link check in CI.

### Changed

- A serious finding forces risk level **High** only when it is about the issuer; findings about a promoter, director or group company are shown but do not (C-ADR-26). Jio Platforms: High → Low; showcase IPOs forced High: 6 / 10 → 4 / 10.
- The "riskier than X % of past IPOs" percentile is hidden (`null` with a note) because it tracked document length; Low / Medium / High stays (C-ADR-28).
- Compare names the issuer row after the company instead of "The Company".
- `pipeline_version` 4.2: reports from older versions are re-analysed when opened.
- The ADR index lists the Phase 3 decisions (the generator missed `##` headings) and each decision once.
- The glossary page is English-only and adds report terms (SOD, WACA, RoNW, NAV …).

### Removed

- **Hindi and voice.** `src/finsight/voice/` (faster-whisper ASR), `POST /api/voice`, `GET /api/lab/asr`, the voice config, the `asr` dependency group and `scripts/asr_bakeoff.py`. The API is English-only: chat answers in English, the glossary and question chips are English, and a stray `language` / `lang` / `source` field is accepted and ignored (no 422). Hindi gold files and `eval_results/asr.json` stay as history.
- **Phase 4 model work** (M1–M5), Platform Bench and gold v4: no model was trained; the product keeps the Phase 3 models.
- Blank and outdated analyses, purged after a backup (`data/backup_2026-11-03/`).
- Stale pages moved to `docs/archive/` with a note: the old run guide, cloud runbooks and deploy steps, the Phase 2 tutorials and how-tos.

### Fixed

- Clicking a fact opens the right page of an uploaded prospectus.
- The preload waits for the document row to say ready after the job's `done` event.
- The launcher no longer flashes terminal windows.

## [1.0] — 2026-10-21

Phase 2 (upload any offer document) and Phase 3 (recent IPOs, trained models, FinSight Bench).

### Added

- Upload any IPO offer document (RHP, DRHP or prospectus): validation, document type, duplicate check by SHA-256, daily quotas, kill switch and retention.
- Storage and database layers (SQLite; Postgres through SQLAlchemy Core and Alembic) and a job runner with resumable server-sent events.
- The report page: risk level card, red flags (13 checks and serious findings), risks, compare; upload and "My uploads" screens.
- Risk factors: split, category classifier, seriousness band, novelty against past IPOs, hedging and numbers.
- Risk level: points from red flags and rare serious risks as a share of the points possible, always with its disclaimer; thresholds fitted on 165 train + dev IPOs (C-ADR-25).
- Compare: listed peers from the basis-for-offer-price table and a past-IPO reference.
- Recent IPOs: 289 RHPs collected, 275 parsed; a frozen strict time split with leakage tests (C-ADR-02); a risk bank of 29,677 risks from 440 IPOs.
- Teacher chosen by a blind bake-off (Gemma-4-31B-it, C-ADR-05); 12,000 train-slice risks labelled and rewritten.
- Risk classifier DeBERTa-v3-base, ONNX fp32: dev macro-F1 0.892 ± 0.006 (3 seeds), gold-150 0.899.
- Plain-English student Qwen3-4B LoRA, GGUF Q4_K_M: gold-50 faithful 0.92, plain English 4.64 / 5, post-checks 49 / 50 (one seed).
- Gold v3 / v3.1, gold-150 and gold-50; E14 0.769 and E15 0.762 after the reader fixes (C-ADR-20).
- FinSight Bench v1: 7 test IPOs, frozen inputs, tasks A–D and G (C-ADR-24).
- Reported ablations, not adopted: extractor v2, DeBERTa-v3-large, the 8B student.
- Documentation site (MkDocs Material) with generated reference pages, model cards and datasheets.

### Removed

- Google Cloud (Cloud Run, Cloud Storage, GPU job, deploy workflows, `cloud` / `cloud_gpu` profiles, vLLM backend, cost estimates and the `/admin/costs` page) (B-ADR-16). The product runs locally.

### Fixed

- Upload quotas and the admin job list compared an IST day start as if it were UTC on SQLite, so limits were wrong between 18:30 and 24:00 UTC.

## [0.4.0] — 2026-10-02

### Added

- The full user interface on the real API (gate G4): the IPO library, the workspace with the cited fact sheet and document viewer, verified chat in English and Hindi, the Model Lab and the landing page.

## [0.3.0] — 2026-10-02

### Added

- Trustworthy chat and API (Phase 1 parts 3–4, gate G3): retrieval (BM25, dense, reranking), cited answers from a local LLM, the ✅/⚠️/❌ number verifier, the advice guard and the FastAPI service with server-sent events.

## [0.2.0] — 2026-10-01

### Added

- Parsing, normalisation, the extractors (rules, pretrained QA, fine-tuned QA on weak labels, BiLSTM-CRF), weak labels and the extractor ladder (Phase 1 parts 1–2, gate G2).

[Unreleased]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/compare/v1.1...HEAD
[1.1]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/compare/v1.0...v1.1
[1.0]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/compare/v0.4.0...v1.0
[0.4.0]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/releases/tag/v0.2.0
