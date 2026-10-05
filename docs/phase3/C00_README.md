# C00 — Phase 3 (Big Phase 3): read me first

Phase 3 turns FinSight from "code that is written" into "models that are trained, measured, and shown to beat general chatbots where it matters". Put this folder at `docs/phase3/` in the repo.

## 1. Where the project stands at the start of Phase 3

From the repo (PROGRESS.md, B07, AKSHAT_TODO, `eval_results/`, `data/`, `models/`):

| Area | State |
|---|---|
| Phase 1 (X-Ray, chat, verifier, guard, voice, extractor ladder) | Done and trained: extractor (3 seeds), BiLSTM-CRF (3 seeds), guard classifier. Results in `eval_results/`. |
| Phase 2 code | Mostly written and tested (1,572 tests): upload pipeline, jobs, storage, risk splitting, red-flag rules, risk features, risk level, compare, report UI, teacher / classifier / student notebooks. |
| Phase 2 models | **None trained.** No teacher labels, no classifier, no student. `eval_results/b/` does not exist. |
| Phase 2 evaluations E13–E24 | **None run.** |
| Unbuilt Phase 2 code | B1.3 summary + financial extraction (the input to red flags). |
| Hand-work outstanding | gold v3 verification, segmentation spot-check, quality-100, gold-150, gold-50, novelty pairs, Phase 1 leftovers (E7 check, ASR references, Hindi review). |
| Data | Corpus = 389 IPOs, 2009–2023. Showcase = 10 IPOs from 2025. **Nothing from 2024 or 2026.** |
| Compute | Colab Pro (200 compute units, Google Drive), Kaggle (free T4, CLI on the laptop), laptop RTX 2050 4 GB / 16 GB RAM, Google Cloud free trial (~₹28,800 credit, trial account, no GPU quota until upgraded). |

## 2. What Phase 3 adds

1. **Newest IPOs.** Every mainboard offer document from 2024 to the latest listing is collected, parsed and split **by time** (C02).
2. **A stronger training stack.** A bigger teacher chosen by a blind bake-off, more and fresher teacher labels, the classifier and the simplifier trained on them, and a retrained extractor (C03).
3. **FinSight Bench.** A pre-registered benchmark on the newest IPOs that compares FinSight with **Claude Opus** and **ChatGPT Go** on facts, red flags, risk questions and risk rewrites (C04).
4. **No dates.** Phase 3 is ordered by **gates** (conditions), not calendar days. The course deadline still exists; when time gets short, the cut order in C05 §5 decides what goes.
5. **Deployment last** on the Google Cloud trial (C08), decided when we get there.

## 3. Files

| File | What it holds |
|---|---|
| C00_README.md | This index, the repo state, rules that change, CLAUDE.md patch |
| C01_STRATEGY.md | The goal ("beat frontier models"), what we may and may not claim, competitors, proposed ADRs |
| C02_DATA.md | New IPO collection, time split, leakage rules, rolling reference window |
| C03_TRAINING.md | Compute plan, Colab rules, every model to train, budgets |
| C04_BENCHMARK.md | FinSight Bench: tasks, gold, frontier protocol, scoring, claim rules |
| C05_ROADMAP.md | All parts (IDs, tracks, dependencies, model column, done-when), gates, cut order |
| C_EXECUTION_PLAN.md | Per part: issue, branch, model, files, tests, commits, hand-work, done-when |
| C06_AKSHAT_CHECKLIST.md | Everything Akshat does: before starting, during, after |
| C07_PROMPTS.md | Claude Code opening prompts per part + the Colab run template |
| C08_DEPLOY.md | Final stage: Google Cloud deployment, open decisions |

The Phase 2 B-docs stay the **specs** for the modules they describe (B02 architecture, B03 model details, B04 experiments, B05 UI, B06 API). Phase 3 changes **order, data and scale**, not the module designs, unless a C-doc says so.

## 4. Rules that change in Phase 3

- **No dates anywhere.** Parts are ordered by dependencies and gates. `PROGRESS.md` records what happened, not deadlines.
- **Colab is a first-class GPU** (not "optional"). Akshat starts every Colab run by hand from a `COLAB_STEPS_<job>.md`; Claude Code never runs Colab. Kaggle runs may still be launched by a local Claude Code session with the official CLI.
- **Time split is law.** No document from the test slice or the bench may enter any training set, risk bank, threshold or prompt tuning (C02 §4). A test asserts it.
- **The benchmark is frozen before FinSight is tuned on it.** Prompts, questions and scoring rules are committed before the first frontier run (C04 §2).
- Everything else in CLAUDE.md stays: plan first, one package per part, never read PDFs/weights/raw data, never train on the laptop, never hand-edit results, never give advice, honesty, tests are the memory.

## 5. CLAUDE.md patch (Claude Code applies this in part C0.1)

Replace the "Session protocol (Phase 2)" heading and step 1 with:

```markdown
## Session protocol (Phase 3)
1. Read the **"Resume here"** note at the top of `PROGRESS.md`, then `docs/phase3/C05_ROADMAP.md` (current part) and only the C-doc and B-doc sections that part cites. Index: `docs/phase3/C00_README.md`.
```

Add under "Hard rules":

```markdown
- **Time split (C-ADR-02):** documents in the `test` or `bench` slices (`configs/splits.yaml`) never enter training data, the risk bank, thresholds or prompt tuning. `tests/test_split_leakage.py` enforces it.
- **Bench freeze (C-ADR-06):** files under `bench/` marked `frozen: true` are never edited after the first frontier run; a new version gets a new folder.
- **Colab:** write `docs/phase3/COLAB_STEPS_<job>.md` for every Colab job; Akshat runs it. Notebooks checkpoint to Google Drive and resume.
- **No dates:** never add calendar dates or deadlines to plans or PROGRESS.md "next" lines.
```

Replace the feature-freeze line in the header with: "Phase 3 (now): newest-IPO data, trained Phase 2 models, FinSight Bench vs frontier models, then deploy. Gate-driven, no dates."

## 6. How a Phase 3 working day looks (no dates, just the rhythm)

- **One GPU job running** (Colab or Kaggle) whenever one is unblocked. GPU time is the long pole; never leave it idle when a job is ready.
- **One Claude Code local session** on the next unblocked code part, `/clear` between parts.
- **Akshat's hand-work** in the gaps: ratings and gold checks are on the critical path just like the GPUs (C06).
