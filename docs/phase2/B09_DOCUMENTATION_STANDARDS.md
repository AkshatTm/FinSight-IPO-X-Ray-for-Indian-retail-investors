# B09 — Documentation Standards (industry grade)

**Goal:** someone new (an examiner, a recruiter, a future contributor, or Akshat in six months) can understand, run, deploy, evaluate and extend FinSight from the docs alone.

## 1. Principles
1. **Docs as code:** docs live in the repo, change in the same PR as the behaviour they describe, and are checked in CI.
2. **Diátaxis structure:** separate **tutorials** (learn), **how-to guides** (do a task), **reference** (look things up), **explanation** (understand why).
3. **Single source of truth:** numbers come from `eval_results/` via scripts; API reference from `openapi.json`; config reference from the pydantic settings; never copied by hand.
4. **Plain English**, short sentences, every acronym defined on first use, screenshots where they help.
5. **Honest:** limitations, known issues and AI-assisted parts are documented, not hidden.

## 2. Docs site
- **MkDocs Material** + `mkdocstrings[python]` (API docs from docstrings) + a Redoc page rendering `openapi.json`; published to **GitHub Pages** by a GitHub Action on every push to `main`.
- `mkdocs build --strict` in CI (fails on broken links/warnings); `markdownlint` and a link checker on `docs/**`.
- Navigation:

```
Home (what FinSight is, 1-min tour, live link)
Tutorials
  ├─ Run FinSight locally in 10 minutes
  └─ Analyse your first IPO document
How-to guides
  ├─ Add a showcase IPO
  ├─ Add a red-flag check
  ├─ Add a new X-Ray field
  ├─ Retrain the risk classifier (Kaggle / Colab)
  ├─ Retrain the simplifier (Colab)
  ├─ Deploy to Google Cloud (runbook link)
  └─ Record the demo cache
Reference
  ├─ API (Redoc from openapi.json)
  ├─ Python packages (mkdocstrings)
  ├─ Configuration and environment variables
  ├─ Red-flag rules (generated from configs/redflags.yaml)
  ├─ Risk level (generated from configs/risklevel.yaml)
  ├─ Data formats (gold files, eval_results schema, report.json)
  └─ CLI commands (pipeline, poe tasks)
Explanation
  ├─ Architecture (C4 diagrams)
  ├─ How the pipeline works (Phase 1 + Phase 2)
  ├─ Models: why each one, how trained, how evaluated
  ├─ Evaluation and results (generated tables)
  ├─ Design decisions (ADR index)
  ├─ Limitations and ethics (SEBI, licences, privacy)
  └─ FinSight explained (learning doc + viva questions)
Operations
  ├─ Deploy runbook
  ├─ Rollback runbook
  ├─ Incident: costs spiking / GPU stuck
  ├─ Rotate secrets
  └─ Monitoring and logs
Project
  ├─ Roadmap and changelog
  ├─ Contributing
  ├─ Security policy
  └─ Privacy
```

## 3. Required files (repo root and `docs/`)

| File | Content | Standard |
|---|---|---|
| `README.md` | Pitch (1 line), badges (CI, docs, licence, Python, Node), demo GIF, live link, features, screenshots, architecture diagram, **results table generated from eval_results**, quickstart (≤ 5 commands), docs link, tech stack, limitations, licence, author, "What I learned" | ≤ 2 screens to the quickstart |
| `CHANGELOG.md` | Every release v0.1.0 → v2.0.0 | Keep a Changelog + SemVer |
| `CONTRIBUTING.md` | Setup, branch/commit/PR rules (from `08_GIT_WORKFLOW.md`), tests, docs-as-code rule | — |
| `SECURITY.md` | How to report issues, supported versions, what's in scope, secrets handling | GitHub security policy format |
| `PRIVACY.md` | What's stored (email, uploads ≤ 30 days), what's never stored, redaction of personal details, deletion requests | Plain English |
| `LICENSE` + `NOTICE` | MIT for code; CC BY-NC-SA notes for data/models | — |
| `CODE_OF_CONDUCT.md` | Contributor Covenant (short) | optional but standard |
| `docs/architecture/` | C4 level 1–3 diagrams (mermaid): context, containers, components; sequence diagrams for upload and chat | Up to date with B02 |
| `docs/reference/config.md` | Every config key and env var with type, default, profile values | Generated from settings |
| `docs/model_cards/*.md` | One per trained model (template §4) | Hugging Face model card sections |
| `docs/datasheets/*.md` | One per dataset (corpus, weak labels, teacher outputs, gold sets) (template §5) | "Datasheets for Datasets" |
| `docs/runbooks/*.md` | Deploy, rollback, cost incident, rotate secrets, restore DB (template §6) | Step lists with exact commands |
| `docs/evaluation.md` | All experiments E1–E24: question, method, n, results table, caveats | Generated tables + written caveats |
| `docs/adr/` | Index of all ADRs (Phase 1 + B) | Generated index |
| `docs/troubleshooting.md` | Top 15 problems (RAM, Ollama, CUDA, Kaggle, Colab, Cloud Run cold starts, Supabase auth) with fixes | — |
| `docs/glossary.md` | Finance + ML terms | From 12 §14 + ML terms |

## 4. Model card template
```
# <Model name>
- Version / date / git sha · Base model + licence · Owner
## Intended use / out of scope (not investment advice; no predictions)
## Training data (link to datasheet), size, splits, exclusions
## Training procedure (hardware, hyperparameters, seeds, compute used)
## Evaluation (metrics, n, mean ± std / CIs, test set, comparison table)
## Limitations and known failure cases (with 3 real examples)
## Ethical considerations (bias, misuse, privacy)
## How to use (code snippet) · How to reproduce (notebook link)
```

## 5. Datasheet template
Motivation · composition (counts, fields, examples) · collection process · labelling (who, AI-assisted?, instructions) · preprocessing · uses / non-uses · distribution and licence · maintenance.

## 6. Runbook template
```
# <Task>
When to use · Prerequisites (access, tools) · Steps (numbered, exact commands, expected output) ·
How to verify · Rollback · Common errors and fixes · Last tested (date, by)
```

## 7. Code documentation
- Google-style docstrings on every public function/class (args, returns, raises, example where useful).
- `interrogate` docstring coverage ≥ 80 % on `src/finsight` (CI warning below, failing below 70 %).
- Module `__init__` docstrings describe the package's responsibility and public API.
- Frontend: TSDoc on exported components/hooks; a `frontend/README.md` (structure, scripts, env, mocks, testing).

## 8. Diagrams
Mermaid in Markdown (renders on GitHub and MkDocs). Required: C4 context, containers, components (backend), upload sequence, chat sequence, data flow for training (corpus → teacher → filters → student). Keep diagrams next to the text that explains them.

## 9. CI checks for docs
`mkdocs build --strict`, `markdownlint-cli2`, `lychee` (links), `interrogate`, `openapi.json` up to date (regenerate + diff), generated tables up to date (`poe docs-gen` + diff).

## 10. Definition of done for documentation (checked at BG3 and v2.0.0)
- [ ] Docs site builds and is live on GitHub Pages
- [ ] Every new package has reference docs and a how-to where relevant
- [ ] Every model has a model card; every dataset a datasheet
- [ ] Deploy + rollback runbooks tested once end to end
- [ ] README quickstart tested from a clean clone on Windows
- [ ] Results tables generated, not hand-typed
- [ ] Limitations, AI-assisted labelling and licences documented
