# Jobs and the runner

`finsight.jobs` runs a document's [stages](pipeline.md) in order, records events, and keeps partial
results.

## How a job runs

1. `POST /api/uploads/{doc_id}/complete` (or `/reanalyse`) runs the **model preflight**
   (`jobs/preflight.py`): Ollama has `finsight-student:q4`, the ONNX classifier loads, `bge-m3` and the
   reranker are in the Hugging Face cache. A missing model refuses the job with
   `503 models_unavailable` unless the caller lists it in `analyse_without`; then the stages that need
   it (`simplify` for Ollama, `risks_scored` for the classifier) are marked skipped.
2. The API creates a `jobs` row and starts the runner on a **background thread** in the API process
   (`503 worker_unavailable` if the thread cannot start).
3. The runner (`jobs/runner.py`) runs each `Stage` in order:
    - a stage whose `output` file already exists is not run again, so a retried job continues where it
      stopped;
    - a stage whose `requires` failed is skipped and counts as failed;
    - a failing stage marks the result **partial** and later **degraded**; a failing **critical** stage
      (`validated`, `detected`, `parsed`) fails the whole job;
    - a stage past its timeout (`Stage.timeout_s` or `jobs.stage_timeouts_s`) fails the same way.
4. Each step appends events to `job_events`: `stage` (start / end / failed, with details), `ready`
   (which report part can be shown), `risk_simplified`, and `done` with the final status.
5. At the end the `docs` row gets `pipeline_version`, the model `fingerprint` and `analysis_status`
   (complete, degraded or failed) — the [cache key](pipeline.md#cache-key-and-pipeline-version).

## Events (server-sent)

`GET /api/docs/{doc_id}/events` streams the job's events from the database. The browser resumes with
`Last-Event-ID` after a dropped connection, so the Analysing page never misses a stage. The event shapes
are in the [OpenAPI reference](../reference/api.md) and [Data formats](../reference/data_formats.md).

## The simplify queue

The `simplify` stage queues the 15 most important risks (`simplify.auto_top_n`). A worker thread
rewrites one risk at a time with the student and saves each to `simplified.json` straight away.
**Explain in plain English** (`POST /api/docs/{doc_id}/risks/{rid}/simplify`) moves a risk to the front
(`Database.bump`).

## Command line

```bash
uv run python -m finsight.jobs run <doc_id> <job_id>   # run an existing job row without the API
uv run python -m finsight.jobs simplify <doc_id>       # rewrite the queued risks
uv run python -m finsight.jobs forget <doc_id>         # delete an analysis so the next upload starts fresh
uv run python -m finsight.jobs sweep                   # delete uploads past retention
```

Quotas (`jobs/quotas.py`) count uploads per user and per day in Indian Standard Time; `start.bat` raises
both limits to 1,000.
