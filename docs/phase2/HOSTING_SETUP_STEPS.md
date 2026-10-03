# Hosting setup steps (B0.3)

These are Akshat's hand steps, in order. The design is in B02 §10 and B-ADR-04 (Google Cloud Run + GCS, Supabase Auth + Postgres, Vercel).

**Rules:**
- Never paste a key or password into chat, a commit or an issue. Values go only into `.env` (git-ignored), Secret Manager or the Vercel dashboard.
- `.env.example` lists the variable names. `uv run python scripts/check_env.py cloud` prints only the **names** that are missing.

## Part A: now (free, no billing)

### A1. Supabase (Auth + Postgres)
1. Create a project at supabase.com (Free plan). Pick region **Mumbai (`ap-south-1`)** if offered, else Singapore. Save the database password in your password manager.
2. Auth → Providers → **Google**: enable it.
   - Create an OAuth client in Google Cloud Console → APIs & Services → Credentials. This is free; billing is not needed.
   - Add the Supabase callback URL as an authorised redirect URI.
3. Auth → URL configuration: site URL `http://localhost:3000` for now. Add the Vercel URL later.
4. Project Settings → Database → Connection string → **Transaction pooler** (port **6543**). Put it in `.env` as `FINSIGHT_DB__URL`, using the `postgresql+psycopg://` scheme. The code disables prepared statements for the pooler.
5. Project Settings → API:
   - project URL → `FINSIGHT_AUTH__SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_URL`;
   - anon key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`;
   - JWT secret (only if the project still uses HS256) → `FINSIGHT_AUTH__JWT_SECRET`.
6. Put your own e-mail address in `FINSIGHT_AUTH__ADMIN_EMAILS`.
7. Storage is **not** used: files go to GCS (B-ADR-04). The 50 MB upload limit stays in config (`uploads.max_mb`).

### A2. Vercel
1. Import the GitHub repo and set the root directory to `frontend/`.
2. Set the environment variables:
   - `NEXT_PUBLIC_API_URL`: leave empty until the API exists; the site then runs on mocks with `NEXT_PUBLIC_USE_MOCKS=1`.
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
3. Add the Vercel URL to the Supabase redirect list (A1.3).

### A3. Kaggle GPU check
1. kaggle.com → Settings: phone verified, GPU quota visible (about 30 h/week).
2. `kaggle --version` works locally, and `~/.kaggle/kaggle.json` exists (never committed).
3. Run `uv run python -m finsight.weaklabel.kaggle --help` in a local session.

### A4. Check
Run `uv run python scripts/check_env.py cloud`. Before Part B, only the `GCP_*` and `FINSIGHT_STORAGE__BUCKET` names should still be reported as missing.

## Part B: later, only after Akshat says "go" (paid account)
Nothing in Part B is done by Claude, and nothing is done before your explicit "go". It costs money once billing is on.

1. **Project:** create a GCP project, e.g. `finsight-ipo`. Note the project ID → `GCP_PROJECT`. Set `GCP_REGION=asia-southeast1`.
2. **Billing:**
   - Link a paid billing account. Free-trial credit does **not** cover GPUs.
   - Billing → Budgets & alerts → budget **₹2,000/month**, with alerts at 50 %, 90 % and 100 %, e-mailed to you.
3. **APIs:** enable `run`, `artifactregistry`, `storage`, `secretmanager`, `iamcredentials` and `cloudbuild` (optional).
4. **Artifact Registry:** create a Docker repository `finsight` in `asia-southeast1`.
5. **GCS bucket:** `finsight-docs-<suffix>` in `asia-southeast1`, uniform access, public access prevention on → `FINSIGHT_STORAGE__BUCKET`.
   - CORS: `deploy/gcp/cors.json` (B3.3a), which allows PUT/GET from the Vercel and localhost origins.
   - Lifecycle: `deploy/gcp/lifecycle.json` deletes `docs/` objects after 30 days. The showcase prefix is kept.
6. **Service accounts:**
   - `finsight-api`: Storage Object Admin on the bucket, Cloud Run Invoker/Developer to start jobs, Secret Manager accessor, and **Service Account Token Creator on itself** (V4 signed URLs need `signBlob`).
   - `finsight-worker`: Storage Object Admin on the bucket, Secret Manager accessor.
7. **Secrets:** Secret Manager entries `db-url` and `supabase-jwt-secret` (if HS256).
8. **GPU quota:**
   - IAM & Admin → Quotas → "Total Nvidia L4 GPU allocation without zonal redundancy, per project per region" for **Cloud Run jobs** in `asia-southeast1`.
   - Request 1 if it is 0. Without it, use profile `cloud` (CPU only).
9. **Deploy:** follow `docs/runbooks/DEPLOY_RUNBOOK.md` (B3.3a, B3.3b), then run `scripts/cloud_smoke.py`.

## Fallback (paid, optional)
Hugging Face Docker Space (`deploy_cpu`, ADR-022). This needs HF PRO (about $9/month), because free accounts can no longer create Docker Spaces. Use it only if GCP is not set up by the showcase date.
