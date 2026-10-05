# FinSight — Claude Code instructions (always loaded)

FinSight = IPO X-Ray for Indian retail investors. Phase 1: RHP → cited fact sheet + bilingual chat with ✅/⚠️/❌ number verification. Phase 2: upload any IPO offer document → red flags, plain-English risk report, risk level with reasons, comparisons. **Phase 3 (now):** newest-IPO data, trained Phase 2 models, FinSight Bench vs frontier models, then deploy. Gate-driven; course deadline: Sun 1 Nov 2026 (the only date; it lives only here). Open-weight models only.

## Environment rule
**Local only in code (B-ADR-16, 4 Oct 2026).** Every part runs in a local session on the Windows laptop (see Environment below). Start with `git pull`. Do not add Cloud Run, GCS, GPU-job, Docker-deploy or paid-hosting code before C5.1; Supabase sign-in/Postgres, Vercel and the HF Space are optional config only. B-ADR-16's "credit used up" premise is outdated: a Google Cloud free trial is active, used only at C5.1 after a budget alert and Akshat's explicit "go" (C-ADR-10).

## Session protocol (Phase 3)
1. Read the **"Resume here"** note at the top of `PROGRESS.md`, then `docs/phase3/C05_ROADMAP.md` (current part) and its entry in `docs/phase3/C_EXECUTION_PLAN.md`, then only the C-doc and B-doc sections that part cites. Index: `docs/phase3/C00_README.md` (Phase 2: `docs/phase2/B00_README.md`, Phase 1: `docs/00_README.md`).
2. Run the tests (`uv run poe test`) before changing anything; report in one line.
3. **Model check, both directions, before every part:** Model column in C05 / C_EXECUTION_PLAN (O = Opus, S = Sonnet; ★ and bugs that failed twice on Sonnet = Opus). If it differs from the running model, stop before any work and print exactly: "🔁 MODEL SWITCH: next is <ID> (<title>) — recommended <Opus/Sonnet>. Type /model <opus/sonnet>, then say continue." Otherwise print "✓ Model OK: <ID> on <model>".
4. **One part per session.** End with `✅ <ID> done — run /clear and paste the Phase 3 resume prompt.` (`docs/phase3/C07_PROMPTS.md` R).
5. **Loop:** `git pull` → part (fixtures, then real data; Kaggle runs by CLI; Colab runs by Akshat from `COLAB_STEPS_<job>.md`) → PR merged → next part.
6. Keep the **"Resume here"** block at the top of `PROGRESS.md` current (exact next step, open files, failing tests) after every merge.

## Hard rules
- **Plan first:** for any task > ~50 lines, a plan (≤ 15 lines) in the PR description (or wait for Akshat's approval when he asks).
- **One primary package per part;** touch other packages only for wiring, and import them only via their `__init__.py`.
- **Never read:** `data/raw/`, `data/processed/`, PDFs, audio, `models/`, weights, `node_modules/`, `.next/`, `.venv/`, notebook outputs. You may read `data/samples/`, `data/gold/` and `tests/fixtures/real/`. For schema questions, run a summary script or ask Akshat for 5 rows. To see a document, use `uv run python -m finsight.pipeline inspect` (prints ≤ 40 lines; may write ≤ 30 truncated snippets to `data/samples/`).
- **Fixture pack exception (B-ADR-15):** `tests/fixtures/real/` may hold real section text, word boxes and tables from public offer documents and short corpus excerpts, gzip JSON ≤ 5 MB per file, ≤ 20 MB total, written only by `scripts/export_fixtures.py`. Never PDFs or weights.
- **Never train models on the laptop.** Write notebooks. On **Kaggle only** (local sessions), you may upload private datasets, push and run notebooks on GPU, poll status and download outputs (`python -m finsight.weaklabel.kaggle`, ADR-042). Official `kaggle` CLI only. Colab runs are started by Akshat.
- **Never commit or print credentials** (Kaggle, Supabase service key, DB URL, HF/Vercel tokens, `.env`). `.env.example` lists names only.
- **Never deploy, create paid resources or spend credits** without Akshat's explicit "go" in chat. No hosting exists (B-ADR-16).
- **Never hand-edit model outputs or eval results.** Fix the pipeline or show ⚠️.
- **Never add investment advice or predictions;** no buy/sell/apply/avoid instructions (forbidden phrases: `configs/forbidden_phrases.yaml`, B-ADR-13). The risk level always carries its disclaimer.
- **Honesty:** disclose AI-assisted labels (`label_source`), single-seed runs and test-informed decisions.
- **Time split (C-ADR-02):** documents in the `test` or `bench` slices (`configs/splits.yaml`) never enter training data, the risk bank, thresholds or prompt tuning. `tests/test_split_leakage.py` checks the committed manifests in `data/manifests/`.
- **Bench freeze (C-ADR-06):** files listed in `frozen_files` of a `bench/<v>/manifest.yaml` with `frozen: true` are never edited; a new version gets a new folder. Answer files are not frozen inputs.
- **Colab:** write `docs/phase3/COLAB_STEPS_<job>.md` for every Colab job; Akshat runs it. Notebooks checkpoint to local disk, sync to Google Drive every N steps and resume; weights go to a private HF repo as adapters/GGUF/ONNX, never merged fp16.
- **No dates:** never add calendar dates or deadlines to plans or PROGRESS.md "next" lines (the header deadline is the one exception). Evaluation records keep timestamps.
- **Tests are the memory:** every module ships with pytest tests; property tests for `normalize`. Mark tests that need full documents, the corpus or model weights `@pytest.mark.local` (`poe test` and CI skip them).
- **Stuck rule:** if a part balloons past one session, write `BLOCKED.md` (what failed, what was tried) and stop.
- **Verify, don't assume:** check current library and hosting docs before using an API you're unsure of; record non-obvious choices as a proposed ADR (Phase 2: `B-ADR-NN` in `docs/09_DECISIONS.md` + `docs/phase2/B08_DECISIONS.md`).

## Documentation as code (B09)
Docs change in the same PR as the behaviour they describe. Numbers come from `eval_results/` via scripts, API reference from `openapi.json`, config reference from the settings — never typed by hand. Google-style docstrings on public functions; module `__init__` docstrings state the package's job. Every trained model gets a model card, every dataset a datasheet.

## Git (full rules: `docs/08_GIT_WORKFLOW.md`)
Issue → branch `<type>/b<x.y>-<slug>` → small green commits (Conventional Commits, `Refs #n`) → PR (closes issue) → CI green → rebase-merge, delete branch → tag at phase end. `gh pr create`, `gh pr merge --rebase --delete-branch`. Labels `local` / `akshat` mark where an issue runs. Never commit data (except the fixture pack), weights, PDFs, `.env`, outputs, files > 5 MB. No filler commits. Never force-push `main`.

## Environment (Windows laptop, local sessions)
Your shell is Git Bash. Use `pathlib`, LF endings, no Make. Python via `uv`; tasks via poe.
```
uv sync                      # install
uv run poe test              # fast tests (not slow, not local) | uv run poe test-all   # everything
uv run poe lint | fmt | typecheck
uv run poe api               # FastAPI on :8000
uv run python -m finsight.pipeline build --ipo <id>
cd frontend && pnpm dev      # :3000   (NEXT_PUBLIC_USE_MOCKS=1 for fixtures)
```
Laptop: 16 GB RAM (~8 GB used by other apps), RTX 2050 4 GB. Use `FINSIGHT_PROFILE=dev_light` while coding. Stop Ollama before GPU-heavy offline jobs.

**Profiles:** `dev_light`, `full` (laptop) · `deploy_cpu` (ADR-022 paid HF fallback, dormant). The `cloud` / `cloud_gpu` profiles were removed (B-ADR-16); no hosting.

## Stack
Python 3.11 · uv · ruff · mypy · pytest/hypothesis · pydantic v2 · FastAPI + sse-starlette · PyMuPDF · pdfplumber/Docling · transformers · optimum/onnxruntime · bm25s · faiss-cpu · Ollama / llama-cpp-python · faster-whisper · SQLite / Postgres (SQLAlchemy Core + Alembic) · Supabase (Auth, Postgres, Storage)
Frontend: Next.js App Router · TS strict · Tailwind · shadcn/ui · Motion · TanStack Query · Zustand · Recharts · MSW · openapi-typescript · Vitest · Playwright · supabase-js

## Module map (details: `docs/02_ARCHITECTURE.md` §5, Phase 2: `docs/phase2/B02_ARCHITECTURE.md` §4)
Code lives in `src/finsight/<package>/`, tests in `tests/<package>/`, config in `configs/`, helper scripts in `scripts/`, notebooks in `notebooks/`, the app in `frontend/`.
Phase 1: core · ingest · parse · normalize · extract · weaklabel · retrieve · generate · verify · guard · voice · chat · evaluate · api · pipeline
Phase 2 (new): storage · db · jobs · auth · summary · redflags · risks · risklevel · compare · reports

## End of every part
Tick boxes in `docs/phase3/C05_ROADMAP.md`, update `PROGRESS.md` ("Resume here" + ≤ 10 lines), append a Part C section to `docs/10_FINSIGHT_EXPLAINED.md` for any new module, write local follow-ups to `docs/AKSHAT_TODO.md`, include these in the PR.
