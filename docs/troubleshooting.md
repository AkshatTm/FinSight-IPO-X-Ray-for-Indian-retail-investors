# Troubleshooting

The fifteen problems most likely to stop you, with the fix. Each one names what you see first.

## Laptop

### 1. The laptop runs out of memory or freezes

**You see:** the API or a pipeline build slows to a crawl; Windows starts paging.
**Fix:** use `FINSIGHT_PROFILE=dev_light` while coding (the 0.8B chat model, no dense index, no reranker, no speech model). Close other heavy apps before `full`. Never run two model jobs at once, and stop Ollama (`ollama stop <model>`) before a GPU-heavy offline job.

### 2. Chat says the model is unavailable

**You see:** a chat error or an empty answer; the API log mentions Ollama.
**Fix:** start Ollama (`ollama serve`) and pull the profile's model: `ollama pull qwen3.5:0.8b` for `dev_light`, `qwen3.5:2b` for `full`. Check with `ollama list`.

### 3. CUDA out of memory, or PyTorch does not see the GPU

**You see:** `CUDA out of memory` or `torch.cuda.is_available()` is `False`.
**Fix:** the RTX 2050 has 4 GB, enough for inference only. Install the GPU build with `uv sync --group ml`, stop Ollama first, and keep batch size 1 for offline scoring. Training never runs on the laptop: it runs on Kaggle.

### 4. A test or command suddenly cannot import a package

**You see:** `ModuleNotFoundError` for `onnxruntime`, `mkdocs` or similar after a `uv sync`.
**Fix:** `uv sync` keeps only the groups you name. Sync every group you need in one command, for example `uv sync --group docs --group onnx`.

### 5. A freshness test fails after a code change

**You see:** `test_committed_pages_are_current`, the notebook test or the OpenAPI check fails in CI.
**Fix:** regenerate, never hand-edit: `uv run poe docs-gen`, `uv run poe gen-openapi` then `cd frontend && pnpm gen:api`, and the notebook makers in `scripts/make_*_notebook.py`. Commit the results with the change.

### 6. The website shows nothing or errors on every page

**You see:** failed requests to `/api/...` in the browser console.
**Fix:** start the API (`uv run poe api`, port 8000) or run the site on mocks with `NEXT_PUBLIC_USE_MOCKS=1 pnpm dev`. If the API runs elsewhere, set `FINSIGHT_API_ORIGIN`.

## Uploads

### 7. An upload is refused

**You see:** a message with a code. `too_large` (over 50 MB) or `too_many_pages` (over 1,500): the file is too big. `scanned`: the PDF has no text layer. `password`: it is protected. `not_offer_document`: it is not an RHP, DRHP or Prospectus. `quota_exceeded` / `global_quota_exceeded`: today's limits (3 per person, 10 in total, reset at midnight IST). `uploads_disabled`: the kill switch `UPLOADS_ENABLED=false` is set.
**Fix:** these are by design; the limits live under `uploads` in `configs/config.yaml`.

### 8. An upload stays on "Processing" or fails at a stage

**You see:** the progress screen stops, or a `done` event with a failed stage.
**Fix:** read the job's events (`GET /api/docs/{doc_id}/events`) and the worker log, filtered by `doc_id` and `job_id` (see [Monitoring](runbooks/MONITORING.md)). A failed stage shows ⚠️ on its part of the report; the other stages still finish. `worker_unavailable` (503) means Cloud Run refused to start the job: check the job exists and its service account.

### 9. `hash_mismatch` after uploading

**You see:** 422 when the upload completes.
**Fix:** the file in storage differs from the hash the browser sent, usually an interrupted upload. Upload again. If it repeats on Cloud Storage, check the bucket's CORS settings allow `PUT` from the site.

## Kaggle and Colab

### 10. Kaggle notebook has no GPU or cannot reach the internet

**You see:** `torch.cuda.is_available()` is `False`, or downloads fail in the notebook.
**Fix:** phone-verify the Kaggle account, then turn on GPU and Internet in the notebook settings. The weekly GPU quota (about 30 hours) resets on Saturday; run the `SMOKE = True` version first so a broken run costs minutes, not hours.

### 11. `kaggle` CLI says 401 or 403

**You see:** `401 Unauthorized` on `kaggle kernels push` or `datasets create`.
**Fix:** the token belongs in `~/.kaggle/kaggle.json` (never in the repository or a chat). Download a fresh one from Kaggle settings if it was regenerated, and accept the competition or model terms in the browser when the error names one.

### 12. Colab disconnects mid-run

**You see:** the runtime resets and the outputs are gone.
**Fix:** follow the Colab steps ([teacher](phase2/COLAB_STEPS_teacher.md), [student](phase2/COLAB_STEPS_student.md)): with Drive mounted and `OUT_DIR` on Drive, checkpoints survive a disconnect and a rerun resumes from them. Keep the tab open; Colab stops idle sessions.

## Hosting

### 13. The first request after a quiet period is slow

**You see:** the site waits several seconds, then works.
**Fix:** expected. The API scales to zero (`minScale: "0"`) so nothing costs money while idle; the first request starts a container. For a demo, open the site a minute early. Raising the minimum to 1 costs money and needs Akshat's "go".

### 14. Google sign-in fails or loops

**You see:** the sign-in popup returns to the site signed out, or Supabase shows `redirect_uri_mismatch`.
**Fix:** in Supabase, add the site URL (and `http://localhost:3000` for development) to the allowed redirect URLs; in Google Cloud, the OAuth client's redirect URI must be the Supabase callback URL. Check `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` on Vercel. Without them the site runs with auth off and one local user.

### 15. The database is unreachable after a quiet week

**You see:** API errors mentioning the database; the Supabase dashboard says the project is paused.
**Fix:** free Supabase projects pause after a week without activity. Restore the project from the dashboard (data is kept), wait for it to start, then retry. See [Restore the database](runbooks/RESTORE_DB.md) if data is missing.
