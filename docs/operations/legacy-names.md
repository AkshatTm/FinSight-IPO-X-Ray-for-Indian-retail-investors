# Legacy names (FinSight)

Vidura was called FinSight. The code, the docs, the environment prefix (`VIDURA_`) and the
browser storage keys (`vd_`) were renamed. The names below belong to resources that exist
outside this repository, or to files other things point at, so renaming them in the text
alone would break downloads, deploys or links. They are kept on purpose. To rename one, change
the real resource first, then update every place listed here.

The old `FINSIGHT_*` environment variable names (and `FINSIGHT_API_ORIGIN` for the frontend)
still work as a permanent fallback; the `VIDURA_*` name wins. See
[Settings and environment variables](../reference/config.md).

## External resources

| Name | Where it lives | Why kept |
| --- | --- | --- |
| `AkshatTm/finsight-student` (also `-student-4b`, `-student-8b`, `finsight-student8b`) | Hugging Face private model repos (GGUF/adapters) | Downloads and `scripts/hf_upload.py` target these repo IDs |
| `AkshatTm/finsight-risk-classifier` | Hugging Face model repo | Weights are fetched by ID |
| `AkshatTm/finsight-weights-archive` | Hugging Face repo | Archive of trained weights |
| `AkshatTm/finsight-simplify`, `AkshatTm/finsight-advice` | Hugging Face repos | Fetched by ID |
| `AkshatTm/finsight-x` and the other `finsight-*` repo examples in scripts and docs | Hugging Face | Same reason; placeholders in examples follow the real naming |
| `finsight-student:q4` (and other `finsight-student*` tags) | Ollama model tag, `configs/config.yaml`, `deploy/ollama/Modelfile.student` | Models already created locally under this tag; renaming needs `ollama cp` and a config change |
| `finsight-gpu-jobs` (`AkshatTm/finsight-gpu-jobs`) | Google Cloud job/bucket resource named in the operations docs | Real cloud resource; unused before C5.1 |
| `finsight-db-url`, `finsight-api` | Google Cloud secret and service names; `finsight-api` is also the Docker image name in `Dockerfile` | Real resource names; the image tag in the build and run commands must match what is deployed |
| `finsight-ci` | Throwaway Postgres password in `.github/workflows/backend.yml` | A CI-only value, not a brand |
| `finsight-weaklabel`, `finsight-weaklabel-v3`, `finsight-teacher-risks`, `finsight-teacher-pilot`, `finsight-teacher-smoke` | Kaggle dataset slugs | Private datasets that Kaggle notebooks mount by slug |
| `finsight-extractor-*`, `finsight-clf-*`, `finsight-bilstm-*`, `finsight-muril-guard-*` | Kaggle kernel slugs | Kernel slugs used by `python -m vidura.weaklabel.kaggle` to push, poll and fetch |
| `MyDrive/FinSight`, `/content/drive/MyDrive/finsight_p4` | Google Drive folders used by the Colab notebooks | Folders already hold checkpoints |
| Supabase project and table names | Supabase | Nothing in the repo names a `finsight` project or table; the project is reached through `VIDURA_AUTH__SUPABASE_URL`. Check the dashboard for a project called FinSight |
| `https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors` | GitHub repo URL | Updated when the repo is renamed (GitHub redirects the old name) |
| `https://akshattm.github.io/FinSight-IPO-X-Ray-for-Indian-retail-investors/` | GitHub Pages | Pages does not redirect; updated with the repo rename |

## Files, folders and records

| Name | Where it lives | Why kept |
| --- | --- | --- |
| `finsight_lite` | `ml/handoff/eval/vendor/finsight_lite/` and the handoff docs | Vendored package that ARGON's Colab code imports; part of the handoff contract |
| `data/finsight.db` | Default local SQLite file, in gitignored `data/` | Renaming the file would orphan an existing local database |
| `data/platform_bench/FinSight_Platform_Bench.xlsx` | Platform Bench workbook | Frozen bench input |
| `docs/10_FINSIGHT_EXPLAINED.md` | Historical explainer | Many pages link to this file name |
| `bench/v1/` | Frozen Bench v1 files | Frozen under C-ADR-06; they keep the product wording of the time |
| `eval_results/`, `docs/archive/`, `report/`, dated PROGRESS and handoff logs, ADRs and the Phase 1 to 4 plan folders | Repo | Historical record; left as written |
| `FinSight-cc`, `FinSight-research` | Local worktree folder and a research folder, mentioned in older notes | Names of directories on the laptop |
