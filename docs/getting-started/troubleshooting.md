# Troubleshooting

Each entry starts with what you see.

## Starting

### Ollama is not running, or chat says the model is unavailable

**You see:** the health dot is not green, `GET /api/health` says `degraded`, the upload page offers
**Analyse without** *the plain-English writer*, or chat answers with `llm_unavailable`.
**Fix:** start Vidura with `start.bat` (it starts Ollama), or run `ollama serve`. Check that the model
exists with `ollama list`; if `finsight-student:q4` is missing, put the GGUF in `models/student/` and run
`uv run python scripts/run_app.py --no-frontend` once to create it ([Install](install.md#3-model-files)).

### Port 8000 or 3000 is busy

**You see:** "port … is still in use" in the launcher, or the API window says the address is in use.
**Fix:** `start.bat` stops whatever listens on 8000 and 3000 before it starts. If a process does not
stop within 20 s, the launcher prints its PID: close that program (`taskkill /PID <pid> /T /F`) and
choose **Restart**. The docs site (`uv run poe docs`) also uses port 8000; stop one of them.

### "uv / pnpm / Ollama is not installed"

**Fix:** install it from the link the launcher prints ([Install](install.md#1-tools)), open a new
terminal so `PATH` is updated, and start again.

### A test or the API cannot import `fitz` or `onnxruntime`

**You see:** `ModuleNotFoundError` after a `uv sync`.
**Fix:** `uv sync` without `--inexact` removes the groups you did not name. Run
`uv sync --inexact --group ml --group onnx` (add `--group docs` for this site).

### The first start is slow

**Fix:** expected once. `pnpm install`, the first Next.js compile and the first `uv sync` of the `ml`
group (CUDA PyTorch) take minutes. Later starts take seconds plus the model load.

## While analysing

### Cold start: the first answer or the first analysis is slow

**You see:** the first chat answer after a start takes much longer than the next ones.
**Fix:** expected. The reranker and the embeddings load on first use and are released again after;
`start.bat` preloads only the student. Ask a second question to see the normal speed.

### The upload is refused

**You see:** a message with a code. `too_large` (over 50 MB) or `too_many_pages` (over 1,500);
`scanned` (no text layer); `password` (protected PDF); `not_offer_document` (not an RHP, DRHP or
prospectus). `quota_exceeded` and `uploads_disabled` should not appear with `start.bat`, which raises
the daily limits to 1,000.
**Fix:** use the text PDF from SEBI or the exchange. Limits are under `uploads` in
[configs/config.yaml](../reference/configs.md#configyaml).

### The report says some parts are incomplete (degraded)

**You see:** a banner "Some parts of this report are incomplete" with the reasons ("analysed without
the risk classifier", "the risks_scored step did not finish").
**Fix:** start the missing model (usually Ollama) and click **Re-analyse**. A degraded report is never
cached as complete, so it is also re-run when opened after the model is back.

### "This report was made with an older version of Vidura"

**Fix:** nothing to do: the report is analysed again because its `pipeline_version` differs from 4.2
([cache key](../architecture/pipeline.md#cache-key-and-pipeline-version)).

### The analysis stops at a stage

**You see:** a red mark on one stage on the Analysing page.
**Fix:** the other stages still finish and the report opens with the parts that exist. The reason is in
the *Vidura API* window (it logs `doc_id`, `job_id` and `stage`) and in the job's events
(`GET /api/docs/{doc_id}/events`). Fix the cause and click **Re-analyse**, or delete and upload again.

### The machine runs out of memory

**Fix:** close browsers and other apps; do not run benchmark or training jobs at the same time. Stop
other Ollama models with `ollama stop <name>`. For coding without the models, use
`VIDURA_PROFILE=dev_light`.

### The page stays on "Analysing" or is blank

**Fix:** reload. Check that <http://127.0.0.1:8000/api/health> answers; if not, look at the
*Vidura API* window for the error and restart from the launcher.

## Training lanes

### Kaggle CLI says 401 or 403, or the notebook has no GPU

**Fix:** the token belongs in `~/.kaggle/kaggle.json`, never in the repository. Phone-verify the account
for GPU access and accept the model's terms in the browser when the error names them.

### Colab disconnects mid-run

**Fix:** the Colab notebooks checkpoint to Google Drive and resume; rerun the same cell. See
[Training lanes](../operations/training-lanes.md).
