# Deploy runbook: Google Cloud Run (B3.3a → B2.7 / B3.3b)

**Only after Akshat's explicit "go" in chat.** Every step below can cost money once billing is on.
Prerequisites: `docs/phase2/HOSTING_SETUP_STEPS.md` Part A (Supabase, Vercel) and Part B steps 1–8
(project, billing + ₹2,000 budget alert, APIs, Artifact Registry `finsight`, bucket, service
accounts per `deploy/gcp/IAM.md`, secrets, GPU quota if the GPU job is wanted). The local tools are
`gcloud` and `uv`. Region: `asia-southeast1`.

```bash
export GCP_PROJECT=<project-id> GCP_REGION=asia-southeast1 FINSIGHT_BUCKET=<bucket>
export SUPABASE_URL=https://<ref>.supabase.co VERCEL_HOST=<site>.vercel.app
gcloud config set project "$GCP_PROJECT"
```

1. **Secrets** (values typed into the prompt, never into files or chat):
   `gcloud secrets create finsight-db-url --data-file=-` (the Supabase pooler URL, port 6543), and
   `finsight-admin-emails` (a JSON list).
2. **Bucket settings:** `gcloud storage buckets update gs://$FINSIGHT_BUCKET
   --cors-file=<rendered>/gcs-cors.json --lifecycle-file=deploy/gcp/gcs-lifecycle.json`.
3. **Artefacts and models** (from the laptop):
   - `uv run python scripts/bundle_artifacts.py --out dist/bundle`, then `gcloud storage rsync -r dist/bundle gs://$FINSIGHT_BUCKET/bundle`;
   - `gcloud storage cp models/<chat>.gguf models/simplifier/*.gguf gs://$FINSIGHT_BUCKET/models/…`, keeping the layout the profile expects (`models/simplifier/…`);
   - GPU path only: the AWQ student into `gs://$FINSIGHT_BUCKET/models/simplifier/awq/`.
4. **Images:** set the repository variables `GCP_PROJECT`, `GCP_REGION`, `GCP_WIF_PROVIDER` and
   `GCP_DEPLOY_SA` (GitHub → Settings → Variables), then run the **images** workflow by hand
   (Actions → images → Run workflow; image `cpu-both`, tag e.g. `v2026-10-12`). Add `gpu-worker`
   only for the GPU path.
5. **Render:** `uv run python scripts/render_deploy.py --set IMAGE_TAG=v2026-10-12` → `dist/deploy/`.
6. **Deploy:**
   ```bash
   gcloud run jobs replace dist/deploy/worker-job.yaml --region "$GCP_REGION"
   gcloud run jobs replace dist/deploy/sweep-job.yaml --region "$GCP_REGION"
   gcloud run services replace dist/deploy/api-service.yaml --region "$GCP_REGION"
   gcloud run services add-iam-policy-binding finsight-api --region "$GCP_REGION" \
     --member=allUsers --role=roles/run.invoker   # public API; auth is the Supabase JWT
   # optional GPU path (quota + billing):
   gcloud run jobs replace dist/deploy/gpu-job.yaml --region "$GCP_REGION"
   ```
7. **Retention schedule:** Cloud Scheduler job, daily 03:10 IST, HTTP POST to the Run Admin API
   `…/jobs/finsight-sweep:run` with OAuth as `finsight-worker@`.
8. **Vercel:** set `NEXT_PUBLIC_API_URL` to the service URL; redeploy the site.
9. **Smoke test:** `FINSIGHT_SMOKE_TOKEN=<a Supabase access token> uv run python
   scripts/cloud_smoke.py --base-url <service URL> --pdf <a small offer document> --out
   eval_results/b/smoke_deploy.json`. Record cold start and stage timings (B2.7).
10. **Write down** the image tag, revision names and smoke result in `PROGRESS.md`.

If a launch fails, the API answers `503 worker_unavailable` and marks the job failed. To retry by
hand: `gcloud run jobs execute finsight-worker --region "$GCP_REGION" --update-env-vars
DOC_ID=<doc_id>,JOB_ID=<job_id>` after creating a new job row (or ask the reader to upload again).
Rollback: `ROLLBACK.md`. Spend alarm: `COST_INCIDENT.md`.
