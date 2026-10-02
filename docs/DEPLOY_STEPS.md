# Deploy steps (P6.1 and P6.2), click by click

Everything here is prepared but **not done**: no account was created and nothing was uploaded.
Plan: the API runs on a free CPU Hugging Face Space (Docker), the website on Vercel. The
website calls `/api/*` on its own origin and Next.js forwards it to the Space (`rewrites` in
`frontend/next.config.ts`), so the API needs no CORS setup.

What the public demo does: the scripted questions replay recorded real answers (demo cache). A
question outside that set goes to a small model on a shared CPU, which is slow (tens of seconds);
the site says so. That is the ADR-022 trade-off.

## 0. Before you start (laptop, about 10 minutes)

1. `uv run python scripts/bundle_artifacts.py --out dist/space`
   Writes the built outputs of the ten demo IPOs, the demo cache, `eval_results/` and `configs/`
   to `dist/space/` with a `MANIFEST.json`. It never copies PDFs. It prints the size. If the size
   is more than you want to upload, add `--no-pages` (the page images are the biggest part; the
   document viewer then shows no pages).
2. Look at `dist/space/MANIFEST.json`: no path starting `data/raw`.
3. Optional local check (needs Docker Desktop and about 3 GB of free RAM; stop Ollama first):
   ```
   docker build -t finsight-api .
   docker run --rm -p 7860:7860 -v "%cd%/dist/space:/app/bundle:ro" finsight-api
   ```
   Open http://localhost:7860/api/health. The first start downloads the 1.3 GB model.

## 1. Hugging Face Space (API)

1. Go to huggingface.co, sign in, click your avatar, **New Space**.
2. Name: `finsight-api`. SDK: **Docker** (Blank). Hardware: **CPU basic (free)**. Visibility:
   Public. Click **Create Space**.
3. On the Space page open **Files**, then **Add file**, **Upload files**. Upload, keeping the
   folder structure:
   - `Dockerfile`, `pyproject.toml`, `uv.lock`, `README.md` (use `deploy/space/README.md`; it
     has the Space settings at the top, so upload that file as `README.md`), `LICENSE`
   - the `src/` folder
   - `deploy/space/entrypoint.sh` as `deploy/space/entrypoint.sh`
   - the **contents** of `dist/space/` into a folder named `bundle/` in the Space
   Large page-image folders can be uploaded from the command line instead (`hf upload` from
   the Hub CLI) if the web form times out.
4. **Settings**, **Variables and secrets**: add the names in `deploy/space/space.env.example`
   (`FINSIGHT_PROFILE=deploy_cpu` and the model repo and file). `HF_TOKEN` is only needed if a
   download is refused; add it as a **secret**, never as a variable.
5. The Space builds on its own (open the **Logs** tab). Wait for "Running". The first start
   downloads the model, about two minutes.
6. Test: open `https://<your-user>-finsight-api.hf.space/api/health` in a browser. Expect
   `"status": "ok"` or `"degraded"` (degraded means the LLM is not loaded yet).
7. Write the direct URL down (the "Embed this Space" menu shows it): it looks like
   `https://<your-user>-finsight-api.hf.space`.

## 2. Vercel (website)

1. Go to vercel.com, sign in with GitHub, **Add New**, **Project**.
2. Import the FinSight repository. Set **Root Directory** to `frontend`. Framework: Next.js (the
   `vercel.json` in `frontend/` already sets install and build commands).
3. **Environment Variables**: add `FINSIGHT_API_ORIGIN` = the Space URL from step 1.7 (no trailing
   slash). Do not set `NEXT_PUBLIC_USE_MOCKS`.
4. Click **Deploy**. When it finishes, open the URL and check: the IPO list loads, an X-Ray page
   shows numbers, the Model Lab shows the ladder.
5. Ask one scripted question in the chat (a suggested question): it should replay at once.

## 3. After it works

- Put the two URLs in the README and in the report (section "Reproducibility").
- Tag `v1.0.0-rc.1` after the README has the links (P6.3).
- If the site shows "API unavailable": open the Space URL first (free Spaces sleep after
  inactivity and wake in about a minute), then reload.

## Known risks to know about (not blockers)

- **Streaming through a Vercel rewrite.** A slow live answer may be cut by Vercel's proxy
  time limit. The scripted questions are fast and unaffected. If live answers are cut, the fix is
  to let the browser call the Space directly, which needs a CORS rule in `src/finsight/api/app.py`
  (tell the assistant; it is a ten-line change).
- **The deployed model is a 4-bit file** (`Qwen3.5-2B-Q4_K_M.gguf`) of the model measured with
  Ollama on the laptop. Its answers were **not** re-measured; the verifier marks numbers either
  way. Run the E7 questions against it once before quoting any answer-quality number for the
  deployed system.
- **No reranker on the Space** (`FINSIGHT_RETRIEVE__RERANK=false` in the Dockerfile): retrieval
  is BM25 only there (recall@5 0.61 on dev, ADR-049). The laptop profile is better.
- **Voice is off** on the Space (`asr: off`).
- The Space has about 16 GB RAM on the free tier; the image needs roughly 3 GB with the model.
