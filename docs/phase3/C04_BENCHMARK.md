# C04 — FinSight Bench: FinSight vs Claude Opus vs ChatGPT Go

The bench is the evidence behind every "better than" claim (C01 §4). It replaces Phase 1's E9 plan.

## 1. Systems

| System | How it is used | Recorded |
| --- | --- | --- |
| **FinSight** | Full upload pipeline + chat on the laptop (`full` profile), exactly as a user gets it | git sha, profile, model files |
| **Claude Opus** | Claude.ai app on a paid plan, Opus selected, PDF uploaded in a **new chat** per document | app, plan, exact model string shown, input condition (§1 ladder), timestamp |
| **ChatGPT Go** | ChatGPT app on the Go plan, PDF uploaded in a **new chat** per document | app, plan, exact model string shown (the app routes between models), input condition, timestamp |

No memory/personalisation features on the frontier apps during runs (Akshat turns them off or uses a fresh chat with memory disabled), no web search, no extra hints beyond the frozen prompts.

**Input ladder (pre-registered in the manifest).** RHPs are 500–1,000+ pages (roughly 300–800k tokens), so an app may reject, truncate or search the file.

1. **Full PDF** in one upload.
2. If an app rejects it (size, page or token limit), **fixed page ranges taken from that RHP's own table of contents** for the sections each task needs. Akshat verifies the ranges before the freeze (they are in `bench/v1/page_ranges.yaml`). A script cuts the PDF by those page numbers without reading it. FinSight's parser is **not** used, so its errors cannot hurt the frontier apps.
3. When either app needs step 2 for a document, **both apps get the same step-2 input** for that document, so the comparison stays like for like.

The condition actually used is recorded per document and system, and reported.

## 2. Bench documents and freezing

- **`bench` slice (C02 §4):** **6 IPOs**: 2 of the 7 test showcase IPOs + the **4 newest 2026** `test` IPOs. The newest IPOs are preferred because frontier models may have seen news about 2025 IPOs (contamination, which helps them on facts). This is disclosed with the results.
- **`bench-dev`:** 2 dev IPOs run through the same protocol. Only these may be used for error analysis and tuning. Their frontier runs are only needed for C4.5, which is below the cut line (C05 §6).
- `bench/v1/` holds the manifest, prompts, questions, answer keys, page ranges and the scoring script. The manifest lists `frozen_files` (every input file, with its sha256) and pins `redflags_version` (§4 Task B). When everything is ready, the manifest gets `frozen: true` and a commit. After that the files in `frozen_files` never change (C-ADR-06); a test compares them with the recorded hashes. `answers/` and rating sheets are outputs, not frozen inputs, so filling them does not trip the guard. A later version is `bench/v2/`.

## 3. Gold and the bias rule (C-ADR-11)

- Facts gold = gold v3 (showcase IPOs) + **gold v4** for the 4 bench IPOs not in v3. Gold v4 fields = **Task A fields ∪ every input of the 13 red-flag checks**, each with page + quote (the status gold needs all red-flag inputs, not only Task A's ~20 fields).
- **Pre-fill is mixed and the source is hidden:** some values come from FinSight output, some from a Claude chat, and the sheet does not say which. **Every value is verified by Akshat on the PDF page** before freezing. The sheet records per field whether he changed it, and the source key is applied by script afterwards to report change rates per source. Reason: we are scoring Claude and ChatGPT, and FinSight itself; verification removes errors, and hiding the source limits anchoring on any one system.
- Red-flag status gold is computed by script from verified facts.
- Q&A answer keys: written with page references, verified by Akshat.

## 4. Tasks

### Task A — Key facts (~20 per document)

Issue size, fresh issue, OFS, price band, face value, lead managers, registrar, promoters, revenue / PAT / operating cash flow (3 years), borrowings, net worth, promoter holding post-issue, pledged %, top-customer %, litigation counts.

- Frontier prompt (frozen): asks for each field with value, unit and page number, in a fixed table format.
- **Field map:** `bench/v1/field_map.yaml` maps each Task A field to where FinSight produces it (`configs/fields.yaml` X-Ray field or a `summary.json` path from C3.1). A field FinSight cannot produce scores as "not found" for FinSight; no field is dropped to help FinSight.
- **Metrics:** normalized value match (Phase 1 NVM), **scale-error rate** (lakh/crore/million confusions), coverage (answered vs "not found"), citation accuracy (stated page contains the value).

### Task B — Red flags (13 checks per document)

- Frontier prompt gives the same 13 check definitions in plain language (from `configs/redflags.yaml` `rule:` texts) and asks for status + supporting number + page.
- **Pinned rules:** the manifest pins `redflags_version`. The status gold and FinSight's statuses are both computed with that version, even if C3.2 later tunes thresholds on dev.
- **Disclosure:** Task B is structurally easier for FinSight. Its statuses come from the same rule engine as the gold, so only its extraction errors count, while the frontier apps must also apply the rules. The report says so.
- **Metrics:** status accuracy vs status gold, macro-F1 over OK/Watch/Concern/NA, number correctness behind each status.

### Task C — Risk questions (10 per document)

- Mix: 5 answerable fact questions, 2 "trick" scale questions (asks for a figure in the wrong unit), **3 unanswerable** questions (the document does not contain the answer; 3 rather than 2 so abstention has n = 18 on 6 documents).
- **Metrics:** correct / partly / wrong / abstained (rated blind), hallucinated-number rate, abstention accuracy on the unanswerable ones, citation accuracy.

### Task D — Risk rewrites (5 risks per document)

- Same 5 risks for every system; frontier prompt asks for a plain-English rewrite ≤ 60 words that keeps every number and does not change certainty.
- **Metrics:** blind human "same meaning" (yes/partly/no), number preservation (verifier, script), certainty preservation (script), FKGL drop (script), forbidden phrases.

### Task E — Consistency (cut)

- **Cut** (C05 §5 cut 5). FinSight is deterministic, so it would be 100 % consistent by construction; the report states that as a property, not as a win.

### Task F — Cost and time

- FinSight: measured stage timings; "no per-document fee, runs locally" (deployed cost after C08 if deployed).
- Frontier: plan price per month, wall-clock per document (Akshat notes start/end).

## 5. Running it

1. Claude Code (C4.1) builds `bench/v1/`: manifest, prompts (`prompts/task_*.md`), questions, risk lists, field map, page-range template, answer-key templates, and **answer templates** per system (`answers/<system>/<ipo_id>.md` with fixed headings so pasting is mechanical).
2. Akshat verifies gold, answer keys and TOC page ranges (C06), then the manifest is frozen.
3. FinSight answers are produced by a script (C4.2).
4. Akshat runs the frontier apps (C4.3) with memory and web search off: open new chat → upload (input ladder, §1) → paste task prompt A, copy reply into the template → B → C → D. Record the plan, model string and timestamp. One document per sitting is fine.
5. A parse script converts pasted replies into `answers/<system>/<ipo_id>.jsonl`; anything it cannot parse is flagged, not guessed.
6. Blind rating sheets (Tasks C and D) are generated with system names hidden and order shuffled. Answers are **normalised to one template** (markdown stripped, citations removed from the rated text and scored separately by script, same layout), because formatting would reveal the system. **20 % of items are repeated** in the sheet to measure intra-rater consistency. Akshat is the **single rater** and built FinSight; this is disclosed. An optional second rater (a classmate) may rate 20 % of Tasks C/D. The key is applied by script.
7. `bench/score.py` writes `eval_results/c/bench_v1.json` and the tables for the report and the Model Lab.

## 6. Statistics and claims

- Every metric with n (documents and items) and a **document-cluster bootstrap** 95 % interval (resample documents, keep their items together; items within a document are correlated, so an item-level bootstrap would overstate certainty with 6 documents).
- FinSight vs each frontier system: **paired** differences (same items), cluster-bootstrap CI; McNemar test for binary correctness as a secondary check.
- "Better" only when the paired-difference CI excludes 0; otherwise "on par"; "worse" is reported the same way.
- Per-task and overall tables; the "Where FinSight loses" list is generated from the same file.

## 7. Improvement loop

1. Bench v1 on `bench` (test) and `bench-dev`.
2. Error analysis **only on `bench-dev` items** and on dev IPOs outside the bench; from `bench` only aggregate numbers are looked at.
3. Fix the pipeline (rules, normaliser, prompts, retrain if needed), with tests.
4. Bench v2: FinSight re-run on the same frozen `bench/v1` items; frontier answers re-collected only if time allows (the apps change over time, so the report states when each frontier answer set was collected, from the recorded timestamps). C4.5 is below the cut line (C05 §6).
5. Any change that was motivated by a `bench` (test) item is disclosed as test-informed.

## 8. Effort estimate for Akshat (time, not dates)

| Work | Approx. |
| --- | --- |
| Verify gold v4 (Task A ∪ red-flag inputs) + answer keys for the 4 new bench IPOs | ~1.5 h per document (~6 h) |
| Verify Q&A answer keys for the 2 showcase bench IPOs + 2 bench-dev | ~20 min per document (~1.3 h) |
| Verify TOC page ranges for 8 documents | ~10 min per document (~1.3 h) |
| Frontier runs (2 apps) on 6 bench + 2 bench-dev documents | ~35 min per document per app (~9 h; ~7 h without bench-dev) |
| Blind rating (Tasks C + D) with 20 % repeats | ~2.5 h total |

About **19 hours** of Akshat's time, spread over many sittings: the biggest time risk in Phase 3 (C05 §6). If that is too much, drop bench-dev frontier runs first (they only feed C4.5). The bench never goes below 6 documents.
