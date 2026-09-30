# FinSight — Claude Code instructions (always loaded)

FinSight = IPO X-Ray for Indian retail investors: RHP → cited fact sheet + bilingual chat with ✅/⚠️/❌ number verification. Local open-weight models only. Deadline Sun 1 Nov 2026.

## Session protocol
1. Read `PROGRESS.md`, then `docs/07_ROADMAP.md` (find the current sub-phase) and its entry in `docs/EXECUTION_PLAN.md`, then only the doc sections that sub-phase needs. Full doc index: `docs/00_README.md`.
2. Run the tests (`uv run poe test`) before changing anything when resuming.
3. Work on **one sub-phase per session**. At the end, print: `✅ <ID> done — run /clear and paste the resume prompt.`

## Hard rules
- **Plan first:** for any task > ~50 lines, show a plan (≤ 15 lines) and wait for Akshat's approval.
- **One primary package per sub-phase;** touch other packages only for wiring, and import them only via their `__init__.py`.
- **Never read:** `data/raw/`, `data/processed/`, PDFs, audio, `models/`, weights, `node_modules/`, `.next/`, `.venv/`, notebook outputs. You may read `data/samples/` and `data/gold/`. For schema questions, run a summary script or ask Akshat for 5 rows. To see a document, use `uv run python -m finsight.pipeline inspect` (prints ≤ 40 lines; may write ≤ 30 truncated snippets to `data/samples/`).
- **Never train models.** Write notebooks; Akshat runs them on Kaggle.
- **Never hand-edit model outputs or eval results.** Fix the pipeline or show ⚠️.
- **Never add investment advice, ratings or predictions.**
- **Tests are the memory:** every module ships with pytest tests; property tests for `normalize`.
- **Stuck rule:** if a sub-phase balloons past one session, write `BLOCKED.md` (what failed, what was tried) and stop.
- **Verify, don't assume:** check current library docs before using an API you're unsure of; record non-obvious choices as a proposed ADR in `docs/09_DECISIONS.md`.

## Git (full rules: `docs/08_GIT_WORKFLOW.md`)
Issue → branch `<type>/<subphase>-<slug>` → small green commits (Conventional Commits, `Refs #n`) → `gh pr create` (closes issue) → CI green → `gh pr merge --rebase --delete-branch` → tag at phase end. Never commit data, weights, PDFs, `.env`, outputs, files > 5 MB. No filler commits. Never force-push `main`.

## Environment (Windows)
Your shell is Git Bash. Use `pathlib`, LF endings, no Make. Python via `uv`; tasks via poe.
```
uv sync                      # install
uv run poe test              # fast tests      | uv run poe test-all   # incl. slow (real models)
uv run poe lint | fmt | typecheck
uv run poe api               # FastAPI on :8000
uv run python -m finsight.pipeline build --ipo <id>
cd frontend && pnpm dev      # :3000   (NEXT_PUBLIC_USE_MOCKS=1 for fixtures)
```
Laptop: 16 GB RAM (~8 GB used by other apps), RTX 2050 4 GB. Use `FINSIGHT_PROFILE=dev_light` while coding. Stop Ollama before GPU-heavy offline jobs.

## Stack
Python 3.11 · uv · ruff · mypy · pytest/hypothesis · pydantic v2 · FastAPI + sse-starlette · PyMuPDF · pdfplumber/Docling · transformers · optimum/onnxruntime · bm25s · faiss-cpu · Ollama / llama-cpp-python · faster-whisper · SQLite
Frontend: Next.js App Router · TS strict · Tailwind · shadcn/ui · Motion · TanStack Query · Zustand · Recharts · MSW · openapi-typescript · Vitest · Playwright

## Module map (details: `docs/02_ARCHITECTURE.md` §5)
Code lives in `src/finsight/<package>/`, tests in `tests/<package>/`, config in `configs/`, helper scripts in `scripts/`, notebooks in `notebooks/`, the app in `frontend/`.
core · ingest · parse · normalize · extract · weaklabel · retrieve · generate · verify · guard · voice · chat · evaluate · api · pipeline

## End of every sub-phase
Tick boxes in `docs/07_ROADMAP.md`, update `PROGRESS.md` (≤ 10 lines), append a Part C section to `docs/10_FINSIGHT_EXPLAINED.md` for any new module, include these in the PR.
