# C04 — FinSight Bench: FinSight vs Claude Opus vs ChatGPT Go

The bench is the evidence behind every "better than" claim (C01 §4). It replaces Phase 1's E9 plan.

## 1. Systems

| System | How it is used | Recorded |
|---|---|---|
| **FinSight** | Full upload pipeline + chat on the laptop (`full` profile), exactly as a user gets it | git sha, profile, model files |
| **Claude Opus** | Claude.ai app, Opus selected, PDF uploaded in a **new chat** per document | app, plan, exact model name shown, how the PDF was given |
| **ChatGPT Go** | ChatGPT app on the Go plan, PDF uploaded in a **new chat** per document | app, plan, exact model name shown, how the PDF was given |

No memory/personalisation features on the frontier apps during runs (Akshat turns them off or uses a fresh chat with memory disabled), no web search, no extra hints beyond the frozen prompts.

If an app refuses the full PDF (size or page limit), Akshat records the error, and Claude Code splits the PDF by **sections** with a script (no reading) so the app gets the relevant sections; the condition is reported per document.

## 2. Bench documents and freezing

- **`bench` slice (C02 §4):** default **8 IPOs** — 4 of the 7 test showcase IPOs + the 4 newest `test` IPOs. Configurable; more documents = more of Akshat's time (C06 §3).
- **`bench-dev`:** 2 dev IPOs run through the same protocol. Only these may be used for error analysis and tuning.
- `bench/v1/` holds the manifest, prompts, questions, answer keys and the scoring script. When everything is ready, the manifest gets `frozen: true` and a commit; after the first frontier run nothing under `bench/v1/` changes (C-ADR-06). A later version is `bench/v2/`.

## 3. Gold and the bias rule (C-ADR-11)

- Facts gold = gold v3 (showcase IPOs) + **gold v4** for bench IPOs not in v3: same fields, each with page + quote.
- Pre-fill may come from any source (FinSight output, Claude chat), but **every value is verified by Akshat on the PDF page** before freezing, and the sheet records which values he changed. Reason: we are scoring Claude and ChatGPT, and FinSight itself; unverified pre-fill from any of them would bias the result.
- Red-flag status gold is computed by script from verified facts.
- Q&A answer keys: written with page references, verified by Akshat.

## 4. Tasks

### Task A — Key facts (~20 per document)
Issue size, fresh issue, OFS, price band, face value, lead managers, registrar, promoters, revenue / PAT / operating cash flow (3 years), borrowings, net worth, promoter holding post-issue, pledged %, top-customer %, litigation counts.
- Frontier prompt (frozen): asks for each field with value, unit and page number, in a fixed table format.
- **Metrics:** normalized value match (Phase 1 NVM), **scale-error rate** (lakh/crore/million confusions), coverage (answered vs "not found"), citation accuracy (stated page contains the value).

### Task B — Red flags (13 checks per document)
- Frontier prompt gives the same 13 check definitions in plain language (from `configs/redflags.yaml` `rule:` texts) and asks for status + supporting number + page.
- **Metrics:** status accuracy vs status gold, macro-F1 over OK/Watch/Concern/NA, number correctness behind each status.

### Task C — Risk questions (10 per document)
- Mix: 6 answerable fact questions, 2 "trick" scale questions (asks for a figure in the wrong unit), 2 **unanswerable** questions (the document does not contain the answer).
- **Metrics:** correct / partly / wrong / abstained (rated blind), hallucinated-number rate, abstention accuracy on the unanswerable ones, citation accuracy.

### Task D — Risk rewrites (5 risks per document)
- Same 5 risks for every system; frontier prompt asks for a plain-English rewrite ≤ 60 words that keeps every number and does not change certainty.
- **Metrics:** blind human "same meaning" (yes/partly/no), number preservation (verifier, script), certainty preservation (script), FKGL drop (script), forbidden phrases.

### Task E — Consistency
- 3 bench documents, Task A repeated **3 times** per system in fresh chats.
- **Metric:** share of values identical across all 3 runs.

### Task F — Cost and time
- FinSight: measured stage timings, ₹ of electricity-free local compute = 0 / deployed cost after C08.
- Frontier: plan price per month, wall-clock per document (Akshat notes start/end).

## 5. Running it

1. Claude Code (C4.1) builds `bench/v1/`: manifest, prompts (`prompts/task_*.md`), questions, risk lists, answer-key templates, and **answer templates** per system (`answers/<system>/<ipo_id>.md` with fixed headings so pasting is mechanical).
2. Akshat verifies gold and answer keys (C06), then the manifest is frozen.
3. FinSight answers are produced by a script (C4.2).
4. Akshat runs the frontier apps (C4.3): open new chat → upload → paste task prompt A, copy reply into the template → B → C → D. One document per sitting is fine.
5. A parse script converts pasted replies into `answers/<system>/<ipo_id>.jsonl`; anything it cannot parse is flagged, not guessed.
6. Blind rating sheets (Tasks C and D) are generated with system names hidden and order shuffled; Akshat rates; the key is applied by script.
7. `bench/score.py` writes `eval_results/c/bench_v1.json` and the tables for the report and the Model Lab.

## 6. Statistics and claims

- Every metric with n and a bootstrap 95 % interval over items.
- FinSight vs each frontier system: **paired** differences (same items), bootstrap CI; McNemar test for binary correctness.
- "Better" only when the paired-difference CI excludes 0; otherwise "on par"; "worse" is reported the same way.
- Per-task and overall tables; the "Where FinSight loses" list is generated from the same file.

## 7. Improvement loop

1. Bench v1 on `bench` (test) and `bench-dev`.
2. Error analysis **only on `bench-dev` items** and on dev IPOs outside the bench; from `bench` only aggregate numbers are looked at.
3. Fix the pipeline (rules, normaliser, prompts, retrain if needed), with tests.
4. Bench v2: FinSight re-run on the same frozen `bench/v1` items; frontier answers re-collected only if time allows (the apps change over time, so the report states when each frontier answer set was collected).
5. Any change that was motivated by a `bench` (test) item is disclosed as test-informed.

## 8. Effort estimate for Akshat (time, not dates)

| Work | Approx. |
|---|---|
| Verify gold v4 facts (bench IPOs not in gold v3) | ~45 min per document |
| Verify Q&A answer keys | ~15 min per document |
| Frontier runs (2 systems) | ~30–40 min per document per system |
| Consistency repeats | ~1.5 h total |
| Blind rating (Tasks C + D) | ~2 h total |

With 8 bench IPOs, budget about 15–18 hours of Akshat's time, spread over many sittings. If that is too much, drop to 6 documents before freezing (never after).
