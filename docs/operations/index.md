# Run, back up, restore

Vidura runs on one laptop; nothing is hosted. This page covers day-to-day running, the maintenance
scripts, backups and restoring weights.

## Launcher

`start.bat` (menu: start, stop, restart, status) and `stop.bat`; details on
[Run Vidura](../getting-started/run.md). `start.bat status` prints which of Ollama (:11434), the API
(:8000) and the web app (:3000) are up, with their process ids.

## Logs

| Where | What |
| --- | --- |
| *Vidura API* window | the API and the job runner: one JSON line per record (`ts`, `level`, `logger`, `message`, plus `doc_id`, `job_id`, `stage` on stage events) |
| *Vidura Web* window | Next.js dev server |
| *Vidura Ollama* window | Ollama |
| `GET /api/docs/{doc_id}/events` | the stored event stream of a document's last job (also in the `job_events` table) |
| `GET /api/traces/{trace_id}` | one chat answer's trace (`data/traces.sqlite`) |
| `GET /api/admin/jobs` | failed jobs (the local user is the admin when `auth.mode` is `off`) |

Closing a window stops that part. To keep a log, run the API by hand and redirect it, for example
`VIDURA_PROFILE=local uv run poe api > api-run.log 2>&1` (`api-run.log` is gitignored).

## Maintenance scripts

| Task | Command |
| --- | --- |
| Re-analyse documents through the running app (resumable; logs timings to `data/preload_log.csv`) | `uv run python scripts/preload.py a.pdf b.pdf` · `--list pdfs.txt` · `--dir <folder>` |
| Build the upload-style reports of the 10 showcase IPOs | `uv run python scripts/build_showcase.py [--only <ipo_id>]` |
| List analyses that are degraded or have an unknown model fingerprint | `uv run python scripts/purge_degraded.py` (dry run) |
| Delete them (files, indexes, page images, rows) | `uv run python scripts/purge_degraded.py --apply` (add `--strict` for empty and old-version ones) |
| Delete one analysis | `uv run python -m vidura.jobs forget <doc_id>` |
| Delete uploads past retention | `uv run python -m vidura.jobs sweep` |

`purge_degraded.py` never touches showcase documents or anything still processing.

### Add a showcase IPO

1. Save the RHP and the final prospectus as `data/raw/rhp/<ipo_id>.pdf` and
   `data/raw/prospectus/<ipo_id>.pdf` (`<ipo_id>` = company slug and year, like `meesho-2025`).
2. Register both in `configs/demo_ipos.yaml` (`ipo_id`, `company`, `split`, and per document `doc_id`,
   `file`, `pages`, `sha256`, the cover's `dated` line); add sector and listing date to
   `configs/ipo_meta.yaml`. A `split: test` IPO is for reported numbers only.
3. Add it to `data/gold/excluded_ipos.txt` so no training data uses it.
4. Build it: `uv run python -m vidura.pipeline build --ipo <ipo_id> --stage parse`, then `sections`,
   `tables`, `rules`, `xray`, `index` (and `qa` with the extractor weights); then
   `uv run python scripts/build_showcase.py --only <ipo_id>` for its full report.

## Back up and restore

Everything that matters at run time is in three places:

| What | Path | Can it be rebuilt? |
| --- | --- | --- |
| Database | `data/finsight.db` | rows for uploads cannot; showcase rows are rebuilt by `build_showcase.py` |
| Stored analyses and PDFs | `data/store/docs/` | yes, by uploading the PDF again (264 s for the 591-page Jio RHP on the reference laptop) |
| Chat indexes and page images | `data/processed/<doc_id>/` | yes, by the `index` stage |

Back up with the app stopped (`stop.bat`), by copying the folders:

```bash
mkdir -p data/backup_$(date +%F)
cp data/finsight.db data/backup_$(date +%F)/
cp -r data/store data/backup_$(date +%F)/
```

Restore by stopping the app and copying them back. `data/backup_*` is gitignored. The final session
made one such backup before purging blank and outdated analyses: `data/backup_2026-11-03/`
(`vidura.db`, `store/`, and untracked gold v3.1 files).

## Model weights and the archive

| Weights | Where they live | Restore |
| --- | --- | --- |
| Student GGUF (used) | Hugging Face dataset `AkshatTm/finsight-gpu-jobs`, `student/out/simplifier-q4_k_m.gguf` | `hf download AkshatTm/finsight-gpu-jobs student/out/simplifier-q4_k_m.gguf --repo-type dataset --local-dir models/_dl` |
| Classifier ONNX (used), reranker ONNX int8, extractor v1 seed 2026 | the laptop's `models/` only | copy from the laptop; no published copy |
| Training-time weights not used by the app (other classifier and extractor seeds, extractor v2, fp32 reranker) | private model repo `AkshatTm/finsight-weights-archive` | `hf download AkshatTm/finsight-weights-archive --local-dir models --include "<folder>/*"` |

The archive holds `extractor/`, `extractor_v2/`, `reranker_onnx/` and `risk_classifier/` (217 files,
each checked against the local copy before deletion). What was deleted from the laptop, where each item
is now and how to restore it: [CLEANUP.md](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/docs/final/CLEANUP.md).

!!! warning "The GPU-jobs dataset is public"
    `AkshatTm/finsight-gpu-jobs` holds the student adapters and GGUFs and is a public dataset. The
    docs and NOTICE describe these weights as not released; make the dataset private if that was not
    intended.

## What is not here

No hosting, no deployment, no secrets in use: Cloud Run, Cloud Storage, Supabase and Vercel were
removed (B-ADR-16) or never switched on, and deployment was cut with Phase 4. The old runbooks for them
are in `docs/archive/`.
