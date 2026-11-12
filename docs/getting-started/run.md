# Run Vidura (start.bat)

## The launcher

Double-click **`start.bat`** in the repository folder. It shows a menu:

```text
 ===============  Vidura  ===============
   Ollama   :11434  UP    PID 1234
   API      :8000   down
   Web app  :3000   down

   [1] Start everything
   [2] Stop everything
   [3] Restart
   [4] Status
   [Q] Quit
```

Or run one action from a terminal: `start.bat start`, `start.bat stop`, `start.bat restart`,
`start.bat status`. **`stop.bat`** is the same as option 2.

### What "Start" does

1. Checks that `uv`, `pnpm` and `ollama` are installed.
2. Starts Ollama on port 11434 in a minimised window titled *Vidura Ollama*, unless it already runs.
3. Warns if Ollama has no `finsight-student:q4` (run `uv run python scripts/run_app.py --no-frontend`
   once to create it from the GGUF), otherwise loads it for 30 minutes so the first answer is quick.
4. Stops whatever listens on ports 8000 and 3000, so Vidura always gets them.
5. Runs `uv sync --inexact --group ml --group onnx` (fast when nothing changed).
6. Starts the API (`uvicorn vidura.api.app:app --port 8000`) in a minimised window *Vidura API*.
7. Runs `pnpm install` once if `frontend/node_modules` is missing, then starts the web app
   (`pnpm dev --port 3000`) in a minimised window *Vidura Web*.
8. Waits for `http://127.0.0.1:8000/api/health` (up to 120 s) and the web app (up to 180 s), then opens
   <http://localhost:3000> in Microsoft Edge (`set "BROWSER=msedge"` at the top of `start.bat`; set it
   to `default` for the system browser).

The windows inherit these settings from `start.bat`:

| Variable | Value | Effect |
| --- | --- | --- |
| `VIDURA_PROFILE` | `local` | the student model through Ollama, BM25 + reranker |
| `VIDURA_UPLOADS__PER_USER_PER_DAY`, `VIDURA_UPLOADS__GLOBAL_PER_DAY` | `1000` | no practical daily limit on your own machine |
| `VIDURA_UPLOADS__RETENTION_DAYS` | `3650` | uploads are kept for ten years |
| `VIDURA_API_ORIGIN` | `http://127.0.0.1:8000` | where the web app sends `/api/*` |
| `NEXT_PUBLIC_USE_MOCKS` | `0` | the real API, not the mocks |
| `PYTHONUTF8` | `1` | UTF-8 console output on Windows |

### What "Stop" does

It stops only Vidura: the processes listening on 8000, 3000 and 11434, the three windows by their
titles, and Ollama. It never kills every `node.exe` or `python.exe`.

## Manual start (any OS)

Two terminals from the repository root:

```bash
# 1: the API on :8000 with the laptop profile
VIDURA_PROFILE=local uv run poe api
# 2: the web app on :3000
cd frontend && pnpm dev
```

Ollama must be running (`ollama serve`). `uv run poe app` (`scripts/run_app.py`) is an older one-command
start that also creates the Ollama model; `start.bat` replaced it on Windows.

## Without a backend (mocks)

```bash
cd frontend && NEXT_PUBLIC_USE_MOCKS=1 pnpm dev
```

Every API call is answered by the mocks in `frontend/mocks/` (synthetic "Acme" data). Useful for
frontend work; nothing is analysed.

## Check that it runs

```bash
curl -s http://127.0.0.1:8000/api/health
```

returns JSON with `status` (`ok`, `warming` while models load, or `degraded`), the profile, demo mode and the state of each model. The
coloured dot at the top right of the web app shows the same.

## Hardware notes

| | Reference laptop |
| --- | --- |
| RAM | 16 GB (about 8 GB used by other apps) |
| GPU | RTX 2050, 4 GB: reranker and embeddings; the student runs in Ollama |
| One 591-page RHP | 264 s from upload to "done", one run ([timings](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/final/FINAL_SCORECARD.md#laptop-timings-rtx-2050-4-gb-16-gb-ram-profile-local)) |
| One plain-English rewrite on CPU only | 12.3 s on average over 60 dev risks ([model card](../model_cards/risk_simplifier.md#evaluation)) |

Close other heavy apps before analysing a large document. Training never runs on the laptop
([training lanes](../operations/training-lanes.md)).
