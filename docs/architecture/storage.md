# Storage and database

Everything Vidura stores is on the laptop, under `data/` (ignored by git).

## Files

| Path | What | Written by |
| --- | --- | --- |
| `data/store/docs/<doc_id>/source.pdf` | The uploaded PDF | upload (`POST /api/uploads/{doc_id}/file`) |
| `data/store/docs/<doc_id>/*.json` | One file per stage: `doc.json`, `parsed.json`, `sections.json`, `xray.json`, `summary.json`, `redflags.json`, `compare.json`, `sod.json`, `risks.json`, `risks_scored.json`, `risklevel.json`, `simplified.json`, `index.json` | the [pipeline stages](pipeline.md) |
| `data/store/docs/<doc_id>/report.json` | The assembled report overview | `vidura.reports` on request |
| `data/processed/<doc_id>/` | Copies of `parsed.json` / `sections.json`, page images and the BM25 index used by chat | `index` stage |
| `data/processed/<ipo_id>/` | Showcase IPOs built by the offline pipeline | `python -m vidura.pipeline build` |
| `data/processed/bank/` | The risk bank (past risks with `bge-m3` vectors) | `scripts/build_risk_bank.py` |
| `data/finsight.db` | SQLite database (below) | API and job runner |
| `data/traces.sqlite` | Chat traces (`GET /api/traces/{trace_id}`) | chat |
| `data/cache/weight_hashes.json` | Hashes of model files for the cache fingerprint | `vidura.jobs.cache` |
| `data/preload_log.csv` | One row per document preloaded, with stage timings | `scripts/preload.py` |

The storage layer (`vidura.storage`) puts every key under one protocol (`put_bytes`, `get_bytes`,
`exists`, `delete_prefix`), so the files above are addressed as `docs/<doc_id>/<name>`. Only the local
backend exists since B-ADR-16 removed Cloud Storage.

## Database

SQLAlchemy Core tables in `src/vidura/db/tables.py`. On the laptop (`db.backend: sqlite`) missing
tables are created on first use and missing columns are added with `ALTER TABLE`
(`Database.create_all`). Postgres would use the Alembic migrations in `src/vidura/db/migrations/`
(`uv run python -m vidura.db.migrate`); CI runs the Postgres tests (`pytest -m postgres`) against a
service container.

| Table | Rows | Key columns |
| --- | --- | --- |
| `users` | One per user (one local user on the laptop) | `id`, `email`, `created_at` |
| `docs` | One per document | `doc_id`, `sha256`, `doc_type`, `company`, `pages`, `uploaded_by`, `is_showcase`, `companion_of`, `status` (uploading / processing / ready / partial / failed), `rejection`, `pipeline_version`, `fingerprint`, `analysis_status` (complete / degraded / failed), `degraded_reasons`, `skipped_models` |
| `jobs` | One per analysis run | `job_id`, `doc_id`, `stage`, `status`, `progress`, `error`, timestamps |
| `job_events` | The event stream of each job (resumable SSE) | `job_id`, `seq`, `event`, `data`, `ts` |
| `uploads` | One per upload, for the daily quotas | `user_id`, `doc_id`, `ts` |
| `simplify_queue` | Risks waiting for a plain-English rewrite | `doc_id`, `rid`, `priority`, `status` |
| `traces` | Chat traces | `trace_id`, `doc_id`, `payload` |
| `demo_cache` | Recorded chat streams for demo mode | `key`, `payload` |

### Migrations

| Revision | Change |
| --- | --- |
| `0001_initial` | All tables above |
| `0002_cache_v2` | `docs.pipeline_version`, `fingerprint`, `analysis_status`, `degraded_reasons`, `skipped_models` (CC-04) |

## Deleting

- One document: **Delete** in the report, `DELETE /api/docs/{doc_id}`, or
  `uv run python -m vidura.jobs forget <doc_id>`. It removes the stored files, the page images, the
  search index and the rows.
- Uploads past `uploads.retention_days`: `uv run python -m vidura.jobs sweep`.
- Degraded or unknown-fingerprint analyses: `scripts/purge_degraded.py` ([Operations](../operations/index.md)).

Backups and restores are on [Operations](../operations/index.md#back-up-and-restore).
