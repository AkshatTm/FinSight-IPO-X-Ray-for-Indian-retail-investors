# C07 — Claude Code prompts (Phase 3)

**Which prompt when**

| Situation | Prompt |
|---|---|
| Very first Phase 3 session (review → C0.1) | **K** (Opus) |
| Any part after `/clear` | **R** (§1) + the part line from §2 |
| Unattended run (Sonnet parts, no hand-work) | **N** |
| Stuck | **S** |
| Gate review (CG0–CG6) | **G** |

## K — Phase 3 kickoff (local, Opus)

```text
PHASE 3 KICKOFF. These are my instructions.

FinSight Phase 3 is in docs/phase3/ (C00–C08 + C_EXECUTION_PLAN.md). Phase 3 trains the Phase 2 models on fresh data, adds the newest IPOs with a time split, builds FinSight Bench against Claude Opus and ChatGPT Go, and deploys last. It is gate-driven with NO dates. Everything runs locally; Colab runs are started by me; Kaggle runs may be launched by you with the official CLI.

STEP 1 — `git pull`, then read fully: CLAUDE.md, PROGRESS.md, docs/phase3/C00_README.md, C01_STRATEGY.md, C02_DATA.md, C03_TRAINING.md, C04_BENCHMARK.md, C05_ROADMAP.md, C_EXECUTION_PLAN.md, C06_AKSHAT_CHECKLIST.md, C07_PROMPTS.md, C08_DEPLOY.md. Skim the B-docs they cite (B02, B03, B04, B06, B07) and check the code layout with targeted searches (src/finsight, notebooks/, scripts/, configs/). Run `uv run poe test` and report in one line.

STEP 2 — Review before building. Reply with:
(a) a 10-line summary of Phase 3 and what each gate CG0–CG6 means;
(b) every contradiction, gap or risk you find between the C-docs, against the B-docs, and against the real code (file + section), each with a proposed fix. Be critical about: the time split and leakage guard touching existing packages, the rolling reference window vs current risklevel/compare code, the Colab notebooks (checkpoint/resume, vLLM versions, model availability and licences on the Hub), the bench protocol and the bias rule, the compute budget, and laptop limits (16 GB RAM, RTX 2050 4 GB);
(c) all questions you need me to answer, in one numbered list, each with a default.
Then STOP and wait for my answers.

STEP 3 — After my answers, do part C0.1 exactly as C_EXECUTION_PLAN.md describes, including the fixes I approved (edit the C-docs in the same PR). Open the PR and STOP for my approval.

STEP 4 — After I approve and you merge, print the next parts in order (C0.2 first) with the exact prompt for each (R + part line), say which ones need my hand-work, then print the /clear message.

Standing rules: plan before >50-line changes (in the PR description), never add dates, never fake or hand-edit results, never add buy/apply/avoid wording, honesty about AI-assisted labels, tests first, meaningful commits only, rebase-merge, never read PDFs/weights/raw data, never deploy or upgrade Google Cloud or spend credits without my explicit "go".

Begin with STEP 1 and STEP 2 now.
```


## 1. R — the resume prompt (paste after every `/clear`)

```text
Resume FinSight Phase 3 LOCALLY. First `git pull`. Read CLAUDE.md, the "Resume here" note in PROGRESS.md, docs/phase3/C00_README.md §4 and the current part in docs/phase3/C05_ROADMAP.md, then only the C-doc and B-doc sections that part cites. Run the tests (`uv run poe test`) and report in one line. Do the model check (both directions). Do ONE part only: <ID, or "the next unblocked part, GPU lane first">. Plan first (≤ 15 lines) if the part is > ~50 lines. Never add dates. Never deploy, never upgrade Google Cloud, never spend credits without my explicit "go". Never read PDFs, weights or raw data. Colab jobs: write COLAB_STEPS_<job>.md and stop for me to run it. End with the PR merged, the C05 box ticked, PROGRESS.md "Resume here" updated, hand-work written to docs/AKSHAT_TODO.md, and the /clear message.
```

## 2. Part-specific additions (append to the resume prompt)

| Part | Add |
|---|---|
| C0.1 | "Commit docs/phase3/, apply the CLAUDE.md patch in C00 §5, record C-ADR-01…11 as proposed in docs/09_DECISIONS.md and docs/phase3/C_DECISIONS.md, mark absorbed B-parts in B07 as 'moved to Phase 3', create C issues with labels local/colab/kaggle/akshat." |
| C0.2 | "Build notebooks/colab/_common.py, COLAB_STEPS_template.md, scripts/log_compute.py and the rate-check notebook. Stop for me to run it on T4, L4, A100; then update C03 §4 from the observed rates." |
| C1.1 | "Build configs/ipo_universe.csv for mainboard IPOs from 2024 to the latest listing (official sources only). Print counts by year and doc type. Stop for my approval." |
| C1.2 | "scripts/fetch_offer_docs.py per C02 §3 with tests on a fake server; then fetch. Print a manual-download list for blocked sources." |
| C1.3 | "scripts/batch_parse.py per C02 §6; one document at a time, Ollama stopped; fix repeated failures with regression tests; eval_results/c/parse_batch.json." |
| C1.4 | "Splits, manifests, leakage test and the rolling reference window per C02 §4–5. Print counts and stop for my confirmation before freezing." |
| C2.1 | "Risk bank per C03 §3 C2.1 incl. B2.1a golden tests and E13/E13b; separate eval parquet for test/bench." |
| C2.2 | "Teacher bake-off per C03 §3: COLAB_STEPS_teacher_bakeoff.md, input export, blind 100-row sheet after I bring outputs back. Verify both checkpoints and licences on the Hub first." |
| C2.3 | "Full teacher per C03 §3 with the chosen model; COLAB_STEPS_teacher_full.md; filters; quality-100 sheet; stop for my rating; then go/no-go and datasheet." |
| C2.4 | "Classifier per C03 §3: TF-IDF on laptop, base 3 seeds on Kaggle via CLI, COLAB_STEPS for large 3 seeds; pick by dev; ONNX; E16; model card." |
| C2.5 | "Student per C03 §3: zero-shot bake-off, COLAB_STEPS for QLoRA 4B (and 8B only if C03 §4 reserve allows), GGUF, E18–E20, gold-50 blind sheet; stop for my ratings." |
| C2.7 | "Extractor v2 per C03 §3: weak labels over train incl. 2024+, Kaggle 3 seeds via CLI, ladder row qa_finetuned_v2, keep only if it wins on dev." |
| C3.1 | "Summary + financial extraction (B1.3 left + B1.3b) per B02/B04 on the new parsed set; E14 on gold v3 once verified." |
| C4.1 | "Build bench/v1 per C04 §2–5: manifest, frozen prompts, questions, risk lists, answer templates, gold v4 pre-fill sheet. Follow C-ADR-11. Stop for my verification; then freeze." |
| C4.2 | "Produce FinSight answers for bench/v1 by script into answers/finsight/." |
| C4.4 | "Parse pasted frontier answers, generate blind sheets, stop for my ratings, then bench/score.py → eval_results/c/bench_v1.json with paired bootstrap CIs and McNemar." |
| C4.5 | "Error analysis on bench-dev only (C04 §7); propose fixes; implement with tests; re-run FinSight; bench v2 tables; list any test-informed change." |

## N — Unattended run (local, Sonnet parts only)

```text
UNATTENDED MODE (Phase 3, local). These are my instructions; I'm away.
`git pull`, then read CLAUDE.md, PROGRESS.md ("Resume here"), docs/phase3/C05_ROADMAP.md and C_EXECUTION_PLAN.md. Work through parts marked S whose "Needs" are met and that need no hand-work from me, in roadmap order. Skip O/★ parts, Colab runs, and anything needing my approval, ratings or credentials (list them in docs/AKSHAT_TODO.md). Kaggle CLI runs are allowed (smoke first).
- No stops for plan approvals: plans go in PR descriptions; gate checklists go in docs/gates/CGx.md.
- After every merge update PROGRESS.md "Resume here" and docs/MORNING_REPORT.md (new section "Unattended run <n>", no dates).
- Never: deploy, upgrade Google Cloud, spend credits, start Colab, force-push, rewrite history, delete data/gold, edit frozen bench files, commit secrets/PDFs/weights.
- Stop a part after 3 identical failures (write BLOCKED.md, move on); pause heavy steps if free RAM stays under 1.5 GB.
Begin now.
```

## S — Stuck

```text
We're stuck on <ID>. Read BLOCKED.md. In 5 lines: what failed and why you think so. Then 2–3 alternatives with trade-offs and a recommendation, including a cut from C05 §5 if it fits. No code until I choose.
```

## G — Gate review

```text
Gate review for CG<n>. `git pull`. Check every condition for CG<n> in docs/phase3/C05_ROADMAP.md against the real repo and pipeline (tests incl. relevant local ones, eval_results/, a real run where the gate needs one). Report each as PASS / FAIL with evidence. For each FAIL, propose the smallest fix, the part that should do it, or a cut from C05 §5. Write docs/gates/CG<n>.md, update PROGRESS.md, then stop.
```

## 3. COLAB_STEPS template (C0.2 writes the real file; every Colab job copies it)

```markdown
# COLAB_STEPS — <job>

**GPU:** <A100 | L4 | T4> · **Expected:** ~<h> h, ~<units> compute units · **Smoke first:** yes

1. Upload inputs from `<laptop path>` to `MyDrive/FinSight/<job>/in/` (never commit them).
2. Open `<notebook path>` in Colab (File → Upload notebook, or from GitHub).
3. Runtime → Change runtime type → <GPU>. Connect.
4. Note compute units shown in Resources: ____ (type it into `UNITS_BEFORE`).
5. Parameters cell: `SMOKE = True`. Run all. Wait for `SMOKE OK`.
6. Set `SMOKE = False`, Run all. If Colab disconnects, reconnect and Run all again (it resumes).
7. When `<JOB> OK` prints: type `UNITS_AFTER`, run the last cell (writes run_summary.json, uploads weights to HF if any, disconnects).
8. Copy `MyDrive/FinSight/<job>/out/` to `<laptop path>` and tell Claude Code "outputs are back".
```
