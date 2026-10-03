# Restore the database

**When to use:** a bad migration, accidental deletion, or a Supabase project that was paused or lost.

**Prerequisites:** owner access to Supabase; `psql` and `pg_dump` (PostgreSQL 16 client) on the laptop; the database URL from Secret Manager (`gcloud secrets versions access latest --secret finsight-db-url`), used only in the terminal.

## What is in the database, and what can be rebuilt

| Table | Content | If lost |
| --- | --- | --- |
| `users` | Supabase user id and e-mail | recreated on the next sign-in |
| `docs` | one row per uploaded document | outputs stay in Cloud Storage; rows must be restored |
| `uploads` | upload counts for the daily quotas | quotas reset (harmless) |
| `jobs`, `job_events` | processing history and the SSE replay | lost history only |
| `simplify_queue` | pending plain-English rewrites | queued again by the next `python -m finsight.jobs simplify` run or an "Explain this" click |
| `traces`, `demo_cache` | Phase 1 chat traces and recorded answers | the demo cache is re-recorded with `uv run poe record-demo` |

## Steps

1. **Stop writes:** set `UPLOADS_ENABLED=false` on the API.
2. **Take a dump of what is there now**, even if it is damaged:

   ```bash
   pg_dump "$DB_URL" --format=custom --no-owner --file finsight-$(date +%Y%m%d-%H%M).dump
   ```

   Use the direct or session connection (port 5432) for `pg_dump`; the transaction pooler (6543) does not support it well.
3. **Pick the source:** the newest good dump on the laptop, or a backup in the Supabase dashboard (Database → Backups). Which backups exist depends on the Supabase plan; check the dashboard rather than assuming.
4. **Restore into an empty schema:**

   ```bash
   pg_restore --clean --if-exists --no-owner --dbname "$DB_URL" finsight-<date>.dump
   ```

5. **Bring the schema up to date:** `FINSIGHT_DB__URL="$DB_URL" uv run python -m finsight.db.migrate`.
6. **Turn uploads back on** (`UPLOADS_ENABLED=true`).

## How to verify

- `psql "$DB_URL" -c "select count(*) from docs"` matches what you expect.
- Open two showcase reports and one uploaded report on the site.
- Upload one small PDF and check it reaches `ready`.

## Rollback

Restore the dump taken in step 2.

## Common errors

- **`relation already exists`:** restore without `--clean` into a schema that still has tables; add `--clean --if-exists`.
- **Migrations fail after a restore:** the dump came from newer code. Restore, then deploy the code version that wrote it.

**Prevention:** take a `pg_dump` before every deploy that adds a migration.

**Last tested:** not yet (nothing is deployed). Test once against a throwaway Supabase project.
