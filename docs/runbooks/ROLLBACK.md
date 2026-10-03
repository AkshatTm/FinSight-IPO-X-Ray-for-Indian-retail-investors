# Rollback runbook (B3.3a)

Cloud Run keeps every revision, so a rollback is a traffic switch, not a rebuild.

1. **API:** `gcloud run revisions list --service finsight-api --region asia-southeast1`, then
   `gcloud run services update-traffic finsight-api --region asia-southeast1 --to-revisions <previous>=100`.
2. **Worker / GPU / sweep jobs:** jobs have no traffic; render the previous image tag and replace:
   `uv run python scripts/render_deploy.py --set IMAGE_TAG=<previous>` then
   `gcloud run jobs replace dist/deploy/worker-job.yaml --region asia-southeast1` (same for the others).
3. **Database:** migrations are additive (Alembic). Never downgrade the production database without
   a Supabase backup; if a migration is the problem, roll the code back and leave the schema.
4. **Stop uploads while you look:** set `UPLOADS_ENABLED=false`
   (`gcloud run services update finsight-api --region asia-southeast1 --update-env-vars UPLOADS_ENABLED=false`).
   The showcase reports keep working; the upload page shows the B05 "uploads are paused" message.
5. **Site:** Vercel → Deployments → promote the previous deployment.
6. Note what happened and the revision you returned to in `PROGRESS.md`.
