# Google Cloud Run definitions (B3.3a, B-ADR-04)

Infra as code for the hosted FinSight. **Nothing here is deployed** until Akshat's explicit "go"
(B2.7 smoke deploy, B3.3b public deploy). Steps: `docs/runbooks/DEPLOY_RUNBOOK.md`.

| File | What it is | Image |
|---|---|---|
| `api-service.yaml` | Cloud Run service `finsight-api`: 2 vCPU, 4 GiB, scale 0–2, showcase bundle and models mounted read-only from GCS | `deploy/api.Dockerfile` |
| `worker-job.yaml` | Cloud Run job `finsight-worker`: one execution per document, started by the API (`jobs.launcher`) | `deploy/worker.Dockerfile` |
| `gpu-job.yaml` | Cloud Run job `finsight-gpu-worker` on one L4 (profile `cloud_gpu`): vLLM + the AWQ student | `deploy/gpu.Dockerfile` |
| `sweep-job.yaml` | Cloud Run job `finsight-sweep`: deletes uploads past 30 days, run daily by Cloud Scheduler | worker image |
| `gcs-cors.json` | Bucket CORS: browser PUT to signed URLs from the Vercel site and localhost | — |
| `gcs-lifecycle.json` | Bucket lifecycle: `docs/` objects deleted after 31 days (backstop to the sweep), stale multipart uploads aborted | — |
| `IAM.md` | Service accounts and roles | — |

Bucket layout: `docs/<doc_id>/…` (uploads and their outputs), `bundle/` (showcase artefacts from
`scripts/bundle_artifacts.py`), `models/` (GGUF chat model, GGUF student, ONNX classifier, the AWQ
student for the GPU job, the risk bank). Models are never committed; they reach the bucket by
`gcloud storage cp` from the laptop.

`${NAME}` placeholders are filled by `uv run python scripts/render_deploy.py --set IMAGE_TAG=…`
(values from `--set` or the environment; it refuses to write while any is missing).

Not yet wired: the API does not start the GPU job by itself. Until the simplify stage lands in
the pipeline, run it by hand (`gcloud run jobs execute finsight-gpu-worker --update-env-vars
DOC_ID=…`) or rely on the CPU fallback (`python -m finsight.jobs simplify`).

The Phase 1 Hugging Face Space variant (`Dockerfile` at the repo root, `deploy/space/`) is the
paid, optional fallback (ADR-022).
