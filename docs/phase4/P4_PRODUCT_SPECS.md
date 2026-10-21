# Phase 4 — Product specs (CC)

CC keeps all phase 1–3 conventions (module contracts, pydantic at boundaries, tests per module, no reading PDFs/weights,
`poe` tasks, frontend rules). This file says **what** to build; CC's own execution plan says how.

---

## CC-01 — V1.0 freeze
- Fix the 3 failing tests: regenerate docs pages; restore the empty `gold_v3_template.jsonl` (regenerated, 280 rows) with the labelled content in `data/gold/gold_v3_labelled.jsonl`. *(done)*
- Commit or gitignore the untracked gold files and run logs (`api-run.log`, `frontend-run.log` → gitignore).
- Empty `BLOCKED.md` → delete or reset.
- Push `train/c2.5-student`, merge it into `main` by PR (merge commit); tag `v1.0` on the merged `main`; push the tag.
- Create `p4/cc` from the tag, install the Phase 4 files there and merge them to `main` by PR; create `p4/argon` from that `main`; push both.
- Install the Phase 4 files (this folder, `AGENTS.md`, CLAUDE.md addendum); add `data/platform_bench/` to `.gitignore` except `README.md` and the empty template.

## CC-02 — Handoff pack
Per `P4_HANDOFF_CONTRACT.md` section A. Includes running current baselines into `baselines.json` and the leakage test.
Touch `ml/handoff/READY` last.

## CC-03 — Platform Bench ingest
- `src/finsight/bench/platform.py` + `scripts/platform_bench.py`: read `data/platform_bench/FinSight_Platform_Bench.xlsx` → normalized JSONL per tab, using the product's numeral normalizer.
- Normalise `ipo_id` to the repo format (lowercase hyphen slug `<company>-<year>`, e.g. `jio_platforms_2026` becomes `jio-platforms-2026`); keep the sheet's original id for traceability. Add every bench IPO (Jio included) to `excluded_ipos.json`.
- Validate: every row's `ipo_id` exists in the IPOs tab; units parse; report bad rows.
- Write `excluded_ipos.json` additions (bench IPOs) — re-export to the handoff pack.
- Deterministic scorer (`eval_results/p4/cc/platform_bench_facts.json`): per platform and FinSight, vs gold v4:
  - **coverage**: fields present / fields RHP-derivable
  - **accuracy**: normalized value match (same tolerance rules as the verifier)
  - **citations**: share of shown figures with a page (brokers = 0 by construction)
  - **platform errors**: rows where a broker value contradicts gold v4 (list them; these are report findings)
- Risk-quality scoring is ARGON's judge (M5); CC's scorer reads its output and merges into one scorecard.

## CC-04 — Cache v2
- **Preflight** before any analysis job: check Ollama reachable + `finsight-student` tag present, classifier ONNX loaded, embeddings/reranker loaded. Missing → job refuses with a clear message, or runs only if the user ticks "analyse without X" (stored).
- **Cache key** = `sha256(pdf) + pipeline_version + models_fingerprint` (model tags + weight hashes). Bump `pipeline_version` in config whenever extraction/red-flag/risk-level logic changes → stale analyses re-run automatically on open (with a "re-analysing with the new version" banner).
- **Analysis status**: `complete | degraded | failed`, plus `degraded_reasons[]`. Degraded results show a banner and are never served as complete.
- **Delete** (removes analysis, indexes, page images; keeps nothing) and **Re-analyse** (forces a new run) on each IPO and upload: API endpoints + buttons + confirm dialog.
- One-off: script to purge all analyses with a degraded/unknown fingerprint.

## CC-05 — Summary-of-Offer (SOD) engine
- **First job = diagnosis.** `finsight.summary` already reads the SOD. Run it on Jio and report, per red-flag check, what the reader returned and where it broke (why 12/13 were "Not available"). CC-05 is then "fix the reader + layer `SODResult` on top", not a rebuild.
- Input: `ParsedDoc`. Output: `SODResult` (pydantic) mirroring `expected.json` in ARGON's fixtures (see `P4_MODEL_SPECS.md` L1).
- Locate SOD via TOC + heading regexes (variants in `FORMAT_CATALOGUE.md`); table extraction for financials and litigation; unit from table headers through the normalizer.
- Every value: `value`, `normalized`, `unit`, `page`, `bbox` if available, `confidence`.
- **Tests:** fixture-driven — each of ARGON's 10 `pages.txt` + `expected.json` is a test case. Gate: ≥8/10 fully match on financials, litigation counts and promoter holding.
- Use Opus for this module.

## CC-06 — Financials, strengths, promoter holding
- **Financials:** restated summary (from SOD first; fall back to "Summary of Financial Information"/"Restated Financial Information" tables). Derived (code, not models): revenue growth YoY, PAT margin, debt/equity, cash from operations, with formulas shown in the UI on hover.
- **Strengths:** "Our Strengths" / "Competitive Strengths" under "Our Business" → list of items (heading + first sentence + page). Plain-English rewrite through the student is optional and must pass the existing post-checks.
- **Promoter holding:** pre/post from SOD or Capital Structure.

## CC-07 — Red flags v2 + Risk level v2
- Rewire all 13 checks onto SOD/financials/strengths outputs; "Not available" only when the source section genuinely lacks the data (record why).
- **Event filter (rules baseline):** before a "serious finding" fires, the matched sentence must pass a negation/hypothetical rule set ("could", "may", "any", "in the event", "no", "not", "nil", "has not been"...). Export rule predictions on ARGON's L2 test set → `eval_results/p4/cc/event_rules_preds.jsonl`. When M3 is delivered and BEATS, it replaces the rules (rules stay as fallback).
- **New insight checks** (Zerodha-style, all computed from RHP numbers): contingent liabilities vs net worth; outstanding statutory dues/deferred payment obligations; dividend history; group companies in the same line of business; promoter post-issue control; OFS share of the issue; negative cash from operations in any period.
- **Risk level v2** (keeps Low/Medium/High): severity-weighted sum of risks normalized by risk-factor count (or a per-category share), plus red-flag contributions; refit thresholds on the 165 references; a serious finding forces High only when it is an `actual_event`. Show the percentile line as today, but computed on the new score. Write a short ADR.

## CC-08 — Frontend
- **Risks tab:** Top 7 (from M2 when delivered; current selection until then) as cards with category, severity, page chip; then the rest grouped by category, collapsed by default, with counts; search stays.
- **Financials tab** (new): table of 3 FY + stub, unit toggle (₹ crore / million / lakh), a simple bar chart for revenue/PAT, derived ratios with formula tooltips, every figure clickable to its page.
- **Overview:** add Strengths card and promoter holding; keep Five things → rename to "Top risks" once M2 lands.
- **Red flags UI v2:** each check shows OK / Watch / Concern / Not available + "why" + numbers used + page chips; serious findings show the sentence and its event label.
- **Compare fixes:** company name instead of "The Company"; negative money as `−₹3.30`; fill RoNW/P/E from the Basis for Offer Price table; "Against past IPOs" uses the reference set (provisional label kept).
- **Cache UI:** degraded banner, Delete and Re-analyse buttons, re-analysing banner.
- Regenerate API types and MSW mocks; Playwright flow updated.

## CC-09 — Integrate ARGON deliveries
For each delivery marked ready in `comms/to_cc.md`: read MODEL_CARD + metrics; if BEATS, wire `predict.py` behind the
existing interface with a config switch (`models.<id>.version`), keep the old path as fallback, add an integration
test, bump `pipeline_version`. Student v2: new Ollama tag, switch in config, run Bench v1 Task A/B/C locally to confirm.

## CC-10 — Re-run + scorecard
Re-analyse the 30 bench IPOs with the final config. Produce `eval_results/p4/P4_SCORECARD.md`:
FinSight vs Groww vs Zerodha vs AngelOne on coverage, accuracy, citations, risk quality (from M5), with the
platform-error list. Plus the Jio before/after (red flags found, risk level, tabs filled).
