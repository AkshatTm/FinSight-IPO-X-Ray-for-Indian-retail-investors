# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 1 log: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** Big Phase 2, B0 (setup) → BG0 Mon 5 Oct. Plan: `docs/phase2/B07_ROADMAP.md` + `docs/phase2/B_EXECUTION_PLAN.md`. Overnight cloud run 1 in progress: see `docs/MORNING_REPORT.md`.
- **Last done:** B1.2 jobs/storage/db/events (#127): `storage` (local + GCS), `db` (SQLAlchemy Core + Alembic, SQLite/Postgres), `jobs` (stage runner, events, quotas, kill switch, retention, priority queue), `auth` (Supabase JWT), `reports`, B06 §2–3 upload/doc/event endpoints. Before that B1.1a (#138), B0.3 (#137).
- **Next ☁️ cloud parts:** B1.5 UI (#131) → B2.3a teacher (#133, O) → B2.4a (#134) → B2.5a (#135, O). After B0.4: B1.3a (#128), B1.4 (#130), B2.1a (#132).
- **Next 💻 local parts:** B0.1 workspace bug (#121), B0.4 fixture pack (#123). L1 prompts: `docs/AKSHAT_TODO.md`. 👤 Part A of `docs/phase2/HOSTING_SETUP_STEPS.md` (Supabase, Vercel, Kaggle; no GCP billing yet).
- **Open questions:** B0.1 bug details.
- **Tests:** 1239 passed, 6 skipped (`uv run poe test`, cloud session, 3 Oct).

## Log
- 3 Oct — B1.2 (#127): upload flow init → file → complete (server SHA-256), worker stages with B06 events + Last-Event-ID replay by polling, IST-day quotas 3/10 + kill switch, retention sweep, simplify priority queue, Supabase JWT auth (off locally), report.json assembly, Alembic 0001 checked on SQLite and Postgres (new CI job), showcase doc_ids in demo_ipos.yaml.
- 3 Oct — B1.1a (#125): upload validation (size → PDF → password → pages → scanned by median text density → offer-document cover with ≥ 2 offer markers), type from the largest-font cover title, `doc_id` from SHA-256, `drhp` in DocType (openapi + frontend types regenerated), shared `uploads:` block in config.yaml. Local follow-up B1.1b in AKSHAT_TODO.
- 3 Oct — B0.3 (#122): hosting is Google Cloud Run (asia-southeast1; CPU API service + CPU worker job + optional L4 GPU job; GCS; Supabase Auth + Postgres; Vercel), Azure dropped. `cloud`/`cloud_gpu` profiles, `UploadsConfig` (50 MB, 1,500 pages, 3/user/day, 10/day, `UPLOADS_ENABLED`), storage/db/auth/simplify/jobs settings, `.env.example` + `check_env.py`. No deploy, billing off.
- 3 Oct — B0.K + B0.2 (#120): kickoff review (45 fixes approved) and Akshat's hosting change: CPU-first, cloud-agnostic hosting (Azure Container Apps for Students or an HF Docker Space + Supabase + Vercel; GCP GPU optional), top-15 automatic rewrites on CPU, Kaggle-first training (Qwen ~14B AWQ teacher, ~3–4B student as GGUF Q4), normalised risk level over 2018–2023. B_EXECUTION_PLAN, B00–B11 fixes, B-ADR-01..15 proposed, CLAUDE.md Phase 2 rules, `local`/`postgres` markers, gold v3 template (270 rows), issues #120–#135 with cloud/local/akshat labels.
- Blockers: none.
