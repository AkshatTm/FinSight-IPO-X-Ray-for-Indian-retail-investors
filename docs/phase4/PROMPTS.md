# Phase 4 — All session prompts

How to use: one task per session. CC: `/clear` between sessions. ARGON: new Antigravity conversation per task.
Every prompt assumes the agent already follows its rules file (CLAUDE.md + addendum / AGENTS.md).
Kickstarters are in `KICKSTART_CC.md` and `KICKSTART_ARGON.md` — run those first.

Order of operations (Wed night): CC kickstart → approve → CC-01 (creates branches) → ARGON kickstart → approve →
CC-02 and AR-02 run in parallel.

---

## Standard session opener (prepend to every prompt below)

**CC:**
```
Session start. Read P4_PLAN.md, P4_EXECUTION_PLAN_CC.md, PROGRESS_CC.md, comms/to_cc.md. Run the fast test suite.
Then do the task below. Plan first (≤15 lines) if it's >50 lines of change; wait for my OK.
End: commit, push p4/cc, update PROGRESS_CC.md, tell me what to verify.
```
**ARGON:**
```
Session start. git fetch && git merge origin/main. Read AGENTS.md, P4_EXECUTION_PLAN_ARGON.md, PROGRESS_ARGON.md,
comms/to_argon.md. Then do the task below. End: commit, push p4/argon, update PROGRESS_ARGON.md, tell me exactly
what to run on Colab (notebook, runtime, expected units, where outputs go) or what to verify.
```

---

## CC prompts

**CC-01 — V1.0 freeze**
```
Task CC-01 (P4_PRODUCT_SPECS.md). Fix the 3 failing tests, clean the working tree (gold files, logs, BLOCKED.md),
make main contain the V1.0 state, tag v1.0, create and push p4/cc and p4/argon from the tag, append the
CLAUDE.md addendum, gitignore data/platform_bench/* except README.md and the template. Show me git status and
the tag before pushing the tag.
```

**CC-02 — Handoff pack**
```
Task CC-02. Build ml/handoff/ exactly per P4_HANDOFF_CONTRACT.md §A using real exports from this repo.
Run current models through run_bench.py and run_classifier_eval.py and write baselines.json. Add
tests/ml/test_no_leakage.py. Touch READY last and post "## READY handoff pack" in comms/to_argon.md with
any gaps.
```

**CC-03 — Platform Bench ingest + scorer**
```
Task CC-03. Akshat's sheet is data/platform_bench/FinSight_Platform_Bench.xlsx (template structure: README tab
explains). Build ingest → normalized JSONL, validation report, bench IPO ids into excluded_ipos.json (+ re-export
to the handoff pack, post an FYI to ARGON), and the deterministic scorer per P4_PRODUCT_SPECS.md CC-03.
Scorer must run even when gold v4 is partial (report n per metric).
```

**CC-04 — Cache v2**
```
Task CC-04. Preflight, versioned cache key, complete/degraded/failed status, delete + re-analyse (API + UI), and a
purge script for degraded/unknown analyses. Add tests for: models down → refuse; pipeline_version bump → stale;
delete removes all artifacts.
```

**CC-05 — SOD engine (use Opus)**
```
Task CC-05. Read data/gold/sod_fixtures/FORMAT_CATALOGUE.md and the fixtures' expected.json (not PDFs). Build the
Summary-of-Offer engine → SODResult per P4_PRODUCT_SPECS.md CC-05. Every fixture is a test. Report the pass table
per IPO per field. Gate P4-G1: ≥8/10 on financials, litigation counts, promoter holding.
```

**CC-06 — Financials, strengths, promoter holding**
```
Task CC-06. Build financials (SOD first, restated tables fallback, derived ratios in code), Our Strengths
extraction, promoter holding pre/post. Expose via API. Tests on fixtures and on 3 parsed RHPs from data/samples.
```

**CC-07 — Red flags v2 + Risk level v2 (use Opus)**
```
Task CC-07. Rewire the 13 checks on SOD/financials, add the negation/hypothetical rule filter, add the new insight
checks, and implement risk level v2 per P4_PRODUCT_SPECS.md CC-07. Export rule predictions on ARGON's event-label
test set to eval_results/p4/cc/event_rules_preds.jsonl. Write an ADR. Show me Jio before/after: checks found,
serious findings with their sentences, risk level and percentile.
```

**CC-08 — Frontend**
```
Task CC-08. Frontend per P4_PRODUCT_SPECS.md CC-08: Risks tab rebuild, Financials tab, Strengths + promoter holding
on Overview, red-flag UI v2, Compare fixes, cache UI. Regenerate API types and mocks, update Playwright. Screenshot
Jio's 4 tabs for me at 1366×768 and on a phone viewport.
```

**CC-09 — Integrate a delivery** (run once per delivery)
```
Task CC-09 for <model_id> <version>. Read its entry in comms/to_cc.md, MODEL_CARD.md and metrics.json. Akshat has
placed weights at models/<model_id>/<version>/. If verdict is BEATS, integrate behind a config switch with the old
path as fallback, add an integration test, bump pipeline_version, confirm the numbers locally. Post
"## INTEGRATED" in comms/to_argon.md either way.
```

**CC-merge — evening integration** (daily)
```
Merge per P4_GIT_WORKFLOW.md: origin/p4/argon → p4/cc → main, tests green at each step, push main, post
"## MERGED" in comms/to_argon.md. Report any conflict instead of resolving it in ARGON's paths.
```

**CC-10 — Re-run + scorecard**
```
Task CC-10. Re-analyse the 30 bench IPOs with the final config (check preflight first). Run the Platform Bench
scorer, merge ARGON's judge output, write eval_results/p4/P4_SCORECARD.md with the platform-error list and the
Jio before/after. Tell me honestly where we lose.
```

---

## ARGON prompts

**AR-02 — SOD fixtures (first)**
```
Task AR-02 / L1 in P4_MODEL_SPECS.md. Pick 10 RHPs: Jio (the single disclosed exception) + 9 varied ones from the
train/dev slices only (splits_by_ipo.json; never test-slice/bench/demo). Post them in comms/to_cc.md as
"## REQUEST sod_fixture_ids" and wait for my OK and CC's word-box export (tests/fixtures/real/). Then write
expected.json per IPO (pages.txt optional) and FORMAT_CATALOGUE.md (note the Jio exception). Commit per IPO. When done, post
"## DELIVERY sod_fixtures v1" in comms/to_cc.md and give me a verification checklist (which values to check on
which pages, ~5 min per IPO).
```

**AR-03 — Event labels + M3**
```
Task AR-03 / L2 + M3. If ml/handoff/data/serious_finding_hits.jsonl exists, label it and mine extra
hypothetical/negated/actual sentences to reach ~800 rows across ≥60 training-split IPOs plus a held-out test set
from test-split IPOs. Write LABELS_CARD.md and a verification CSV for me (random 100 + all actual_event).
Then write ml/notebooks/m3_event_clf.ipynb (DEBUG mode, 3 seeds, ONNX export, metrics.json).
```

**AR-04 — M1 teacher data + student v2**
```
Task AR-04 / M1. Write m1_teacher_gen.ipynb (G4, Gemma-4-31B-it, unanswerable + numeric examples +
number-keeping filter), m1_student_train.ipynb and m1_export_gguf.ipynb per P4_MODEL_SPECS.md. Use
student_chat_template.txt (primary) and student_prompt_template.txt (rewrite, must not regress) unchanged. Give me the run order with expected units for each; DEBUG on T4 first.
After I paste results, analyse them and decide: deliver, iterate (say what changes), or stop.
```

**AR-05 — Gold v4 (30 bench IPOs)**
```
Task AR-05 / L3. IPO list: IPOs tab of data/platform_bench/FinSight_Platform_Bench.xlsx (read only). For each IPO,
from its RHP only, write data/gold/v4/<ipo_id>.json. Do 5, post them for my verification, then continue in
batches of 5. LABELS_CARD.md at the end.
```

**AR-06 — M2 ranker + M4 severity**
```
Task AR-06. Build L4 top-risk labels on training-split IPOs, then m2_salience_ranker.ipynb and
m4_severity_v2.ipynb per P4_MODEL_SPECS.md. Baselines from baselines.json. Expected units per run up front.
```

**AR-07 — M5 evaluation + Platform Bench judge**
```
Task AR-07 / M5. For every model delivered this week: final metrics.json with verdict. Then run the blind Platform
Bench risk judge (rubric in P4_MODEL_SPECS.md M5) on all bench IPOs where both FinSight output and broker rows
exist. Write eval_results/p4/argon/P4_MODEL_RESULTS.md and platform_bench_judge.jsonl, plus a 20% sample list for
my spot-check.
```

**AR-iterate — after a Colab run** (reuse any time)
```
Results from <notebook> are in <path> (or pasted below). Compare with the target and baseline. Diagnose. Decide:
DELIVER / ITERATE (exact changes + expected units) / STOP (report as LOSES). Don't spend reserve units without
asking me.
```

---

## Akshat's own checklist per day
- Morning: read both PROGRESS files and both comms files (5 min).
- Run whatever ARGON asked on Colab; paste results back.
- Verify labels ARGON lists (it estimates time per batch).
- Fill Platform Bench rows (~10 min per IPO).
- Evening: run CC-merge. Tell ARGON to merge main next session.
