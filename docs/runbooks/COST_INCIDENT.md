# Cost incident runbook (B3.3a)

Triggered by the ₹2,000/month budget alert (50 %, 90 %, 100 %) or an unexpected bill line.

1. **Stop new work at once:** `UPLOADS_ENABLED=false` on the API (ROLLBACK.md step 4). Showcase pages
   stay up; nothing new starts a job.
2. **Find the spender:** Billing → Reports, group by SKU. Usual suspects:
   - Cloud Run **GPU** (L4) seconds: a GPU job stuck or retried. List running executions:
     `gcloud run jobs executions list --job finsight-gpu-worker --region asia-southeast1`;
     cancel with `gcloud run jobs executions cancel <execution> --region asia-southeast1`.
   - Cloud Run **CPU** instance time on the API: min instances should be 0
     (`autoscaling.knative.dev/minScale: "0"`) and max 2; check the live revision.
   - **Egress / storage:** a large `bundle/` or page images served too often; check GCS metrics.
   - **Artifact Registry storage:** old images; delete tags older than the last two.
3. **Hard stop if needed:** delete the GPU job (`gcloud run jobs delete finsight-gpu-worker`), scale the
   API to zero with max 1, or as a last resort unlink billing from the project (everything stops).
4. **Abuse?** Check the uploads quota table (3 per user per day, 10 per day overall) and the API logs
   for one user or IP; block the user in Supabase.
5. Write up cause, cost and fix in `PROGRESS.md`, and lower limits in `configs/config.yaml` if needed.
