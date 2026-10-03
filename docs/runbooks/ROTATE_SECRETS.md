# Rotate secrets

**When to use:** a secret may have leaked (pasted into chat, a log, a commit, a screenshot), someone who had it leaves, or as routine every few months.

**Prerequisites:** owner access to the Google Cloud project and the Supabase project; `gcloud` signed in on the laptop. Values are typed into prompts only, never into files, chat or commit messages.

## What exists

| Secret | Where it lives | Used by |
| --- | --- | --- |
| Database URL (Supabase pooler, port 6543) | Secret Manager `finsight-db-url` | API, worker, GPU and sweep jobs |
| Admin e-mails (JSON list) | Secret Manager `finsight-admin-emails` | API |
| Supabase anon key | Vercel env `NEXT_PUBLIC_SUPABASE_ANON_KEY` | the website (public by design; row access is not granted through it) |
| Kaggle API token | laptop only (`~/.kaggle/kaggle.json`) | `python -m finsight.weaklabel.kaggle` |
| GitHub → Google Cloud | none: Workload Identity Federation, no keys | `images.yml` |

## Steps

1. **Database password.** Supabase → Project Settings → Database → reset the database password. Copy the new pooler connection string (transaction mode, port 6543).
2. **New secret version:**

   ```bash
   gcloud secrets versions add finsight-db-url --data-file=-   # paste, then Ctrl-D
   ```

3. **Pick it up.** The service reads `latest` when an instance starts, so roll a new revision:

   ```bash
   gcloud run services update finsight-api --region asia-southeast1 --update-labels rotated=$(date +%Y%m%d)
   ```

   Jobs read `latest` at their next execution; nothing to do.
4. **Disable the old version** once the new revision is serving:

   ```bash
   gcloud secrets versions list finsight-db-url
   gcloud secrets versions disable <old-version> --secret finsight-db-url
   ```

5. **Kaggle token:** Kaggle → Settings → API → Expire token, then Create new token; replace `~/.kaggle/kaggle.json` on the laptop.
6. **Supabase anon key** (only if the project's keys were regenerated): update it in Vercel → Project Settings → Environment Variables and redeploy.

## How to verify

- `curl -s https://<api-url>/api/health` answers `"status"` other than `"degraded"`.
- Upload one small PDF and check it reaches `ready`.
- A database login with the old password fails.

## Rollback

Re-enable the previous secret version (`gcloud secrets versions enable <old> --secret finsight-db-url`) and roll a new revision as in step 3. Only do this if the old value is known not to have leaked.

## Common errors

- **`password authentication failed`** in the API logs: the new version was added but the service still runs an old revision. Repeat step 3.
- **`prepared statement … already exists`:** the URL points at the session pooler or the direct port; use the transaction pooler on port 6543.

**Last tested:** not yet (nothing is deployed). Test once with the deploy runbook (B4.1 local follow-up).
