# 04 — Tech Stack, Environment and Resources

**Version policy:** this doc names tools and model IDs; exact versions are pinned in `uv.lock` and `pnpm-lock.yaml`, not here. Before adopting any library, Claude Code checks its current docs/changelog (things move fast) and records non-obvious choices in `09_DECISIONS.md`.

---

## 1. Hardware profile (Akshat's laptop)

| Resource | Value | Consequence |
|---|---|---|
| OS | Windows | Claude Code runs natively; its shell tool uses Git Bash. Use `pathlib`, LF line endings, no Make |
| RAM | 16 GB, ~8 GB already used by Windows + Claude Code + VS Code + browser | Backend budget ≤ ~5.5 GB. `dev_light` profile for everyday coding |
| GPU | NVIDIA RTX 2050, **4 GB VRAM** (laptop, Ampere) | One heavy model on the GPU at a time. LLM ≤ ~2–3.3 GB weights. Offline pipeline runs with Ollama stopped |
| Training | None locally beyond tiny smoke tests | All fine-tuning on Kaggle (free) |

Day-1 check [AKSHAT]: `nvidia-smi` works and shows the RTX 2050; Task Manager → note idle RAM with your normal apps open.

---

## 2. Windows development setup [AKSHAT, ~45 min, Phase 0.1]

1. **Git for Windows** (includes Git Bash). Then:
   ```bash
   git config --global user.name "Akshat Tomar"
   git config --global user.email "<the email on your GitHub account>"   # required for contributions to count
   git config --global core.autocrlf false
   git config --global init.defaultBranch main
   ```
   Enable long paths (admin PowerShell): `git config --system core.longpaths true`.
2. **GitHub CLI** `gh`, then `gh auth login` (HTTPS, browser). Claude Code uses `gh` for issues, PRs and merges.
3. **uv** (Python package/env manager — fast, Windows-friendly). `uv python install 3.11`.
4. **Node.js 22 LTS** + `corepack enable` → `pnpm`.
5. **Ollama for Windows**; confirm GPU use: `ollama run qwen3.5:2b "hello"` then `ollama ps` shows GPU %.
6. **NVIDIA driver** up to date (for Ollama and PyTorch CUDA wheels).
7. VS Code (optional) with Python, Ruff, Tailwind extensions.
8. Claude Code installed and logged in; start it from the repo root.

Project creation: make an empty folder `finsight`, copy `CLAUDE.md`, `PROGRESS.md` and `docs/` in, `git init`, create the GitHub repo (`gh repo create FinSight-IPO-X-Ray-for-Indian-retail-investors --public --source . --remote origin`), push. Then paste the kickoff prompt.

---

## 3. Backend stack

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.11 | Stable wheels for every ML lib on Windows |
| Env + deps | **uv** (`pyproject.toml` + `uv.lock`), dependency groups `api` (runtime server, no torch), `ml` (torch, transformers; offline and Kaggle), `asr`, `dev` | Fast, reproducible; CI and the deployed image never install torch (ADR-029) |
| Task runner | **poethepoet** (`uv run poe <task>`) | Works on Windows without Make |
| Lint + format | **ruff** (`ruff check`, `ruff format`) | One tool replaces flake8 + black + isort |
| Types | mypy on `core`, `normalize`, `verify` | The correctness-critical packages |
| Tests | pytest, hypothesis, pytest-cov | Property tests for the normalizer |
| Models/validation | pydantic v2, pydantic-settings | Every boundary typed |
| API | FastAPI + uvicorn + `sse-starlette` | SSE streaming for chat |
| PDF text/words/images | **PyMuPDF** | Fast, word bboxes, page rendering |
| Tables | pdfplumber (default) · Docling (bake-off on 3 table pages; heavier) | Only key sections need tables |
| ML runtime | PyTorch (CUDA wheel for the RTX 2050), transformers, `optimum[onnxruntime]` | ONNX int8 for CPU encoders |
| Sparse retrieval | `bm25s` | Fast BM25 |
| Dense index | `faiss-cpu` | Small per-IPO indexes |
| LLM serving | **Ollama** (local), `llama-cpp-python` (deploy) | Same GGUF files both ways |
| ASR | `faster-whisper` (CTranslate2), optional AI4Bharat Hindi model | Bake-off decides |
| Storage | SQLite (stdlib `sqlite3`), JSON/JSONL files | Zero-ops |
| Logging | stdlib `logging` + JSON formatter | Simple |
| Notebook hygiene | `nbstripout` pre-commit hook | Clean diffs |

### Poe tasks (defined in `pyproject.toml`)
`test` (fast tests) · `test-all` (incl. slow) · `lint` · `fmt` · `typecheck` · `api` (uvicorn reload) · `build-ipo --ipo <id>` · `build-all` · `ladder` (regenerate results table) · `gen-openapi` (write `openapi.json` for the frontend).

---

## 4. Models

| Purpose | Model (Hugging Face / Ollama id) | Size | Runs where | Licence (check card) |
|---|---|---|---|---|
| Pretrained extractive QA (Rung 2) | `deepset/deberta-v3-base-squad2` | ~184 M params | Laptop GPU fp16 / Kaggle | CC BY 4.0 |
| **Fine-tuned extractor (Rung 3, ours)** | trained from the above on weak labels | same | Laptop GPU | inherits NC-SA terms of training data |
| BiLSTM-CRF (Rung 4, P1) | our own, `pytorch-crf` | ~5 M | Kaggle / laptop | ours |
| Dense retrieval | `BAAI/bge-m3` (multilingual, Hindi query ↔ English passage) | ~568 M | Offline: GPU fp16. Online: CPU ONNX int8 | MIT |
| Reranker | `BAAI/bge-reranker-v2-m3` | ~568 M | CPU int8 or GPU fp16 | Apache 2.0 |
| Local LLM candidates | `qwen3.5:2b`, `qwen3.5:4b` (Ollama), Gemma 4 E2B (GGUF) | 2–4 B, 4-bit | GPU (4B may partially offload) | Apache 2.0 |
| ASR candidates | faster-whisper `small`, `large-v3-turbo` (int8); an AI4Bharat Hindi ASR model | 0.25–0.8 GB | CPU int8 | MIT / check card |
| NLI for text claims (P1) | MiniCheck or Vectara HHEM open model | ~0.4–0.8 B | CPU | check card |
| Advice classifier (P1) | `google/muril-base-cased` fine-tuned | ~236 M | Kaggle train, CPU infer | Apache 2.0 |

**LLM notes.** Small Qwen 3.5 and Gemma 4 models have a "thinking" mode; always **disable it** for our grounded answers (it adds latency and tokens). Some Ollama templates inject thinking by default — verify with a latency check in the bake-off. Prefer text-only GGUFs (vision projector files are not needed).

**LLM bake-off (Phase 3.2) [CC→AKSHAT]:** 10 English + 5 Hindi questions on 2 IPOs, each candidate scored on: citation compliance (every sentence cited), numbers copied exactly, Hindi fluency (Akshat judges 1–5), time to first token, total time, VRAM. Pick the smallest model that passes. Record in `09_DECISIONS.md`.

**ASR bake-off (Phase 3.5):** 10 recorded Hindi questions (Akshat's voice + one other speaker if possible), character error rate + latency on CPU. Pick the best CER under 6 s for a 5 s clip.

---

## 5. Frontend stack

| Concern | Choice |
|---|---|
| Framework | Next.js (latest stable, App Router), React, TypeScript strict |
| Styling | Tailwind CSS + shadcn/ui (tokens from `03_UI_UX_DESIGN.md` §2) |
| Fonts | IBM Plex Sans, IBM Plex Sans Devanagari, IBM Plex Mono via `next/font/google` |
| Motion | Motion (formerly framer-motion) |
| Server state | TanStack Query |
| UI state | Zustand |
| Charts | Recharts |
| API types | `openapi-typescript` from backend `openapi.json` |
| Mocks | MSW + JSON fixtures |
| Tests | Vitest (units), Playwright (demo flow) |
| Palette ◇ | `cmdk` |

---

## 6. Compute plan

| Job | Where | Cost |
|---|---|---|
| Parse, extract (rules + QA inference), embed 12–30 IPOs | Laptop (GPU, Ollama stopped) | ₹0 |
| Fine-tune DeBERTa extractor, 3 seeds | **Kaggle** free GPU (T4/P100; weekly quota ~30 h) | ₹0 |
| BiLSTM-CRF, advice classifier | Kaggle | ₹0 |
| Frontier LLM comparison | Claude.ai / ChatGPT manually with the PDF uploaded (conditions reported) | ₹0 (existing subscriptions) or a tiny one-time API spend |
| QLoRA generator fine-tune (P2, optional) | Colab paid (see §6.1) or a rented 24 GB GPU | ₹0–1,000 |

Rules: debug every notebook on a tiny slice first; checkpoint every epoch with a resume flag (Kaggle sessions die); stop paid instances immediately; never start a paid run until the notebook completed end to end for free.

### 6.1 Paid Colab — review and recommendation

As of September 2026: Google's student offer in India gives **Google AI Plus free for 12 months** and **Google AI Pro at a large student discount**, redeemable until **31 Dec 2026**; AI Pro includes **200 Colab compute units per month**. Google has also just bundled premium Colab benefits into paid Google AI plans, but **those Colab perks apply only to paid plans, not free trials**. Standalone Colab Pro remains available, and compute units can also be bought pay-as-you-go.

**Recommendation:** you do **not** need paid Colab for anything P0 or P1 — DeBERTa, BiLSTM-CRF and MuRIL all train on Kaggle's free GPUs. Buy only if you commit to FR-34 (QLoRA generator) by ~20 Oct. If you do: check the exact student price on your Gemini-for-Students page, prefer an **L4** runtime over A100 for a 2–4 B QLoRA (enough memory, far fewer units per hour), and set a calendar reminder to cancel auto-renewal.

---

## 7. Budget

| Item | Expected |
|---|---|
| Everything P0 + P1 | ₹0 |
| Optional QLoRA compute | ₹0–1,000 |
| Emergency GPU rental (e.g. Jarvislabs) | ≤ ₹500, only if Kaggle quota runs out |
| Domain name (optional, for the deployed demo) | ₹0 (use `*.vercel.app`) |
| **Cap** | **₹2,000** |

---

## 8. Accounts checklist [AKSHAT]

- [ ] GitHub (email matches git config), `gh` authenticated
- [ ] Hugging Face (token with read access; write access later for the dataset/Space/model card)
- [ ] Kaggle (phone-verified for GPU), API token in `~/.kaggle/` only if using the CLI
- [ ] Vercel (Hobby) — Phase 6
- [ ] Hugging Face Space (Docker, free CPU) — Phase 6
- [ ] Optional: Google AI Pro student plan (only per §6.1)

Secrets live in `.env` (never committed) and in the platform's secret settings. `.env.example` lists names only.

---

## 9. Data and reference resources

| Resource | Use | Link / how |
|---|---|---|
| Indian IPO datasets (Ghosh et al.), CC BY-NC-SA 4.0 | Training corpus (text or PDF links) | `huggingface.co/datasets/sohomghosh/Indian_IPO_datasets` — confirm contents on Day 1; the BIR/InFiNITE release may be a separate repo |
| RHP PDFs for demo + gold | Demo and evaluation (never training) | SEBI website → Filings → Public Issues → Red Herring Documents; also NSE/BSE issue pages and company investor pages |
| SEBI ICDR Regulations (Schedule VI) | Why RHP section titles repeat | SEBI website → Legal → Regulations |
| Hugging Face course, question-answering chapter | Learning extractive QA fine-tuning | huggingface.co/learn |
| Papers | Related work | See `05_DATA_AND_EVALUATION.md` §10 |

---

## 10. Things we don't use (and why)

- Hosted LLM APIs at runtime — product principle (local, open-weight).
- LangChain/LlamaIndex — thin custom code is easier to explain in the viva and to trace.
- PDF.js viewer — page images + word boxes are simpler, faster, and make highlighting exact.
- Postgres/pgvector locally — SQLite + FAISS is enough for ≤ 50 IPOs.
- WSL2 — adds RAM pressure; everything here works natively on Windows.
