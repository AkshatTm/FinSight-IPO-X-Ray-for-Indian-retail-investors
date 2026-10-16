# Run FinSight on your own laptop

Upload any IPO offer document (RHP, DRHP or final prospectus, as a **text PDF**) in the browser
and get the full product: key facts with their pages, red flags, a risk level with reasons, every
risk in plain English, a comparison, and a chat that checks every number it quotes. Everything
runs on this machine. Nothing is sent anywhere, nothing is deployed.

## 1. Set up from zero (once)

Windows 11, 16 GB RAM, the RTX 2050 (4 GB) is used when it is free. You need:

| Tool | Check | Get it |
|---|---|---|
| Git, Git Bash | `git --version` | https://git-scm.com |
| uv (Python 3.11 is installed by uv) | `uv --version` | https://docs.astral.sh/uv/ |
| Node 22+ and pnpm | `node -v`, `pnpm -v` | https://nodejs.org, then `npm i -g pnpm` |
| Ollama | `ollama --version` | https://ollama.com/download |

```bash
git clone <the repo> && cd FinSight-IPO-X-Ray-for-Indian-retail-investors
uv sync                      # Python packages
```

Model files are not in git. Put them where the app looks (ask for the folder if you start on a
new machine):

* `models/student/simplifier-q4_k_m.gguf`, the plain-English student (2.4 GB). The start command
  creates the Ollama model `finsight-student:q4` from it when Ollama does not have it yet.
* `models/risk_classifier/onnx/`, the risk-category classifier.
* `data/processed/bank/risk_bank.parquet`, the past-risk bank used for "unusual" badges.
* The Hugging Face cache must hold `BAAI/bge-m3` and `BAAI/bge-reranker-v2-m3` (they are
  downloaded on first use if you are online).

## 2. Start it (one command)

```bash
uv run poe app
```

It installs the model packages if they are missing (first time: a few minutes, torch is
large), checks that Ollama runs and has `finsight-student:q4`, loads the student into memory,
starts the API on port 8000 and the frontend on port 3000, and prints the address:

```
FinSight is running.
  Open:   http://localhost:3000/upload
```

Press **Ctrl+C** to stop both. `uv run python scripts/run_app.py --no-frontend` starts the API
alone.

## 3. Use it on your own PDF

1. Open http://localhost:3000/upload and drop a PDF (up to 50 MB, 1,500 pages, text not scan).
   No sign-in is needed on this machine, and there is no daily limit.
2. The **Analysing** page lists the steps as they finish. After the key facts are ready a
   **See what's ready** button opens the report while the rest continues. A 400 to 560 page RHP
   takes about 4 to 6 minutes (see Timings).
3. Uploading the same file again opens the existing report. To analyse it again from scratch run
   `uv run python -m finsight.jobs forget <doc_id>` (the id is in the address bar), then upload.
4. Reports are kept in `data/store/docs/<doc_id>/` and `data/processed/<doc_id>/`. Your uploads
   are listed under **My uploads**.

## 4. What each panel shows

| Panel | What you see | Where it comes from |
|---|---|---|
| **Overview** | Risk level (Low, Medium, High) with the reasons and the always-visible disclaimer; five things to know | red flags + rare serious risks, placed among past IPOs |
| **Red flags** | 13 checks (debt, cash flow, who gets the money, what insiders paid, ...) each with its sentence, numbers and page. "Serious findings" (going concern, regulator orders, qualified audit, ...) set the level to High | rules on numbers read from the document |
| **Risks** | Every risk factor with its category, "unusual" badge (how many past IPOs had a similar risk), the document's wording and a plain-English version for the most important ones. Click **Explain in plain English** for any other | classifier, bge-m3 against past risks, the student model |
| **Compare** | Listed peers from the document and where this IPO sits among past IPOs | peer table + the rolling reference window |
| **Facts, pages and Ask** | Key facts with ✅/⚠️ checks, the PDF page by page with the number highlighted, and a chat in English or Hindi (voice too). Every number in an answer is checked against the pages | rules and table extraction, BM25 + reranker, the student, the number verifier |

FinSight never says whether to apply. Questions like "Should I apply?" are refused and answered
with the facts instead. Red-flag questions are answered from the Red flags tab.

## 5. Timings (this laptop)

See `docs/RUN_LOCALLY_TIMINGS.md`, written by `scripts/smoke_local.py` (the end-to-end check:
`uv run python scripts/smoke_local.py --fresh`).

## 6. Known limitations

* **Text PDFs only.** A scan has no text to read; the upload says so.
* **Blank numbers stay blank.** A Red Herring Prospectus prints `[●]` for the price and sizes
  until the final prospectus. Those facts and the checks that need them show "Not available",
  never zero. Upload the final prospectus to get them.
* Fact extraction reads about 9 of 11 headline fields on a typical RHP; Compare needs the
  price and the peer table, so it is often thin on an RHP.
* The first chat answer after a start takes 30 to 60 seconds (the reranker loads); later answers
  take 4 to 10 seconds. A rewrite takes about 10 to 20 seconds each, one at a time.
* The student is a plain-English rewriter used for chat as well; answers are short and
  cautious by design. The first 15 risks (most important first) are rewritten automatically.
* Hindi: the interface and chat answers are in Hindi; the report pages stay in English.
  Voice uses `faster-whisper-medium` on the CPU and loads when you first press the mic.
* Single user, single machine: no sign-in, no sharing, no deployment.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `Ollama is not installed` / `did not start` | Install Ollama, open the Ollama app once, run again. |
| `finsight-student:q4 is not in Ollama and models/student/... is missing` | Copy `simplifier-q4_k_m.gguf` into `models/student/` and run again. |
| Chat says *llm_unavailable* or rewrites stay "Explaining..." | Ollama stopped. Start it (`ollama serve`) and ask again; a failed rewrite is retried when you click **Explain in plain English**. |
| Out of memory, the machine crawls | Close browsers and other apps (the pipeline needs about 6 GB; the student 3 GB). Stop Ollama's other models: `ollama stop <name>`. Do not run training or benchmark jobs at the same time. |
| The analysis stops at a step with a red mark | The rest of the report still opens ("partial"). Details are in the terminal where `poe app` runs. Retrying: `python -m finsight.jobs forget <doc_id>`, upload again. |
| "This PDF looks like a scan" | The PDF has no text layer. Use the text PDF from SEBI or the exchange; OCR is not built. |
| "This doesn't look like an IPO offer document" | Only RHP, DRHP and prospectus are read. |
| The page is blank or stays on "Analysing" | Reload. Check that http://127.0.0.1:8000/api/health answers. |
| Port 8000 or 3000 is busy | `uv run python scripts/run_app.py --port 8001`, or stop the other program. |
| First start is slow | `pnpm install` and the first page compile happen once; the first question loads the reranker. |
