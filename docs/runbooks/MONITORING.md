# Monitoring and logs

**When to use:** checking that the deployed site is healthy, or finding out why an upload failed.

**Prerequisites:** viewer access to the Google Cloud project; `gcloud` on the laptop.

## Health

- `GET /api/health` returns `status` (`ok`, `warming` while the model loads, `degraded` if the chat model is unavailable), the profile and which models are loaded.
- Cloud Run → `finsight-api` → Metrics: requests, latency, instance count (at most 2) and cold starts.

## Logs

On Cloud Run every `finsight.*` log line is one JSON object (`finsight.core.logging`; the worker CLI always, the API when `K_SERVICE` is set) with `ts`, `level`, `logger`, `msg` and context fields: a failed job stage carries `doc_id`, `job_id` and `stage`, a chat stage `trace_id`. Cloud Logging parses them as structured logs.

```bash
# API errors in the last hour
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="finsight-api" AND severity>=ERROR' --freshness=1h --limit 50
# Everything one upload did (worker job)
gcloud logging read 'resource.type="cloud_run_job" AND jsonPayload.doc_id="<doc_id>"' --freshness=1d
# Recent worker runs and their status
gcloud run jobs executions list --job finsight-worker --region asia-southeast1 --limit 10
```

## One upload, step by step

1. `GET /api/docs/<doc_id>` lists every stage with its status, times and `detail`.
2. The same events are in the `job_events` table, in `seq` order.
3. A `failed` stage's `detail` names the reason; the worker log for that `job_id` has the traceback.

## Costs

- The budget alert (₹2,000 per month at 50 / 90 / 100 %) e-mails Akshat.
- Billing → Reports, filtered to Cloud Run, shows the spend per service and job.
- If spend jumps, follow the [cost incident runbook](COST_INCIDENT.md).

## What is not monitored yet

There are no uptime checks or paging alerts. The project is small enough to check by hand; add an uptime check on `/api/health` if the site is used by more people.

**Last tested:** not yet (nothing is deployed).
