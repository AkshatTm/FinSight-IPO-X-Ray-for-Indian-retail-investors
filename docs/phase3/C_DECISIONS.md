# C_DECISIONS — Phase 3 decisions (C-ADRs)

Full text of the Phase 3 decisions. `docs/09_DECISIONS.md` lists them in its index. Status **proposed** until Akshat marks one accepted; C-ADR-12 was approved by Akshat at the kickoff review.

Each ADR follows the template in `docs/09_DECISIONS.md`. Where a decision came from the kickoff review, the finding number (F1–F40) is given.

## C-ADR-01 Gate-driven plan, no dates — proposed

**Context:** Phase 2 plans carried calendar dates that went stale whenever work moved.
**Decision:** Phase 3 parts are ordered by dependencies and gates (CG0–CG6), not dates. The course deadline is written in exactly one place, the CLAUDE.md header. Evaluation records (bench answers, run summaries, compute logs) keep their timestamps, because the report must say when each frontier answer set was collected (F3).
**Consequences:** `PROGRESS.md` "next" lines and C-docs carry no dates. Slack is managed by the critical path and cut line (C05 §6), not by a calendar.

## C-ADR-02 Strict time split — proposed

**Context:** Users upload new offer documents; the showcase IPOs are dated across 2025, so a percentage split would put IPOs filed after test showcase IPOs into training (F9).
**Decision:** split by offer-document date and by IPO. Every `train` document is dated before every `test` document; the cut is the earliest test-slice document. Showcase roles come from `configs/demo_ipos.yaml` (F10). Leakage is checked on committed manifests in `data/manifests/` by `ipo_id` and company key (F11, F12).
**Consequences:** train gets the corpus plus roughly 2024 and early 2025; fewer fresh training documents than a 70 % split, in exchange for a real time split. `tests/test_split_leakage.py` runs in `poe test`.

## C-ADR-03 Rolling reference window — proposed

**Context:** the code compares against a fixed 2018–2023 corpus (`risks/bank.py`, `configs/risklevel.yaml`, `configs/compare.yaml`), which is stale for 2026 documents (F15).
**Decision:** "compared with past IPOs" means IPOs dated before the document, within 4 years; corpus rows count by close year. Two references: *eval* (as of each test IPO, train + dev only, never stored in configs) and *product* (all collected IPOs before today, `product_reference` manifest, never an input to threshold fitting) (F13). Window n is reported per as-of date (F17).
**Consequences:** the bank gains `ipo_id`, `doc_date`, `split`; deciles come from a per-IPO `reference_scores` table. The corpus has no financial tables, so risk-level references come from new PDFs only, and E21 uses a risk-points-only variant (F16).

## C-ADR-04 Compute: Colab for heavy jobs, Kaggle for small ones, laptop never trains — proposed

**Context:** Google AI Pro gives 200 Colab compute units (expiring 90 days after purchase) and 2 TB Drive; Kaggle gives a free T4; the laptop has an RTX 2050 with 4 GB.
**Decision:** Colab runs the teacher and the student (Akshat starts every run from a `COLAB_STEPS_<job>.md`); Kaggle runs the base classifier and extractor v2 (CLI from a local session); the laptop parses, embeds, evaluates and serves, and never trains. Checkpoints go to local disk and sync to Drive; HF gets adapters, GGUF and ONNX only (F19, F24).
**Consequences:** the budget is planned in compute units (C03 §4) with a large reserve; C0.2 measures real rates and pins a working vLLM (F18).

## C-ADR-05 Teacher chosen by a blind bake-off — proposed

**Context:** the teacher is the ceiling for both the classifier and the simplifier.
**Decision:** Qwen3-14B-AWQ vs Qwen3-32B-AWQ (both Apache-2.0, run with `enable_thinking=False`), 300 risks each, a blind 100-row sheet rated by Akshat; pick by "meaning: yes" after filters, then drop rate, then speed (F21).
**Consequences:** if Colab gives no A100, or the bake-off falls below the cut line, Qwen3-14B-AWQ is used directly and that is recorded here.

## C-ADR-06 FinSight Bench is pre-registered and frozen — proposed

**Context:** a "better than" claim is only credible if the test was fixed before anyone looked at results.
**Decision:** `bench/v1/manifest.yaml` lists `frozen_files` with sha256 and pins `redflags_version`; once `frozen: true`, those files never change, and a test checks the hashes. Answers and rating sheets are outputs, not frozen inputs (F31, F34).
**Consequences:** fixes after the freeze are scored on the same items as bench v2; any change motivated by a bench (test) item is disclosed as test-informed.

## C-ADR-07 Frontier systems — proposed

**Context:** the comparison should reflect what a retail investor actually uses.
**Decision:** Claude Opus in the Claude.ai app on a paid plan, and ChatGPT Go in the ChatGPT app; a new chat per document; memory and web search off; plan, exact model string, input condition and timestamp recorded per run (F37). Input ladder: full PDF, else fixed page ranges from the RHP's own table of contents, verified by Akshat, the same for both apps (F27).
**Consequences:** results describe these apps at collection time, not the underlying models in general.

## C-ADR-08 Downloader policy — proposed

**Decision:** official sources only (SEBI first, then exchange and company pages), polite rate, honest User-Agent, no scraping around bot protection (manual-download list instead), multi-part filings merged or excluded with a reason, never re-hosted (F38).

## C-ADR-09 SME IPOs excluded — proposed

**Decision:** mainboard only in Phase 3; SME offer documents have a different format and rules. Future work.

## C-ADR-10 Google Cloud trial used only at deploy — proposed

**Context:** B-ADR-16 removed the cloud code on the premise that the credit was used up; a new Google Cloud free trial is now active (F1).
**Decision:** the code stays local-only until C5.1. The trial is used only at C5.1, after a budget alert, and only on Akshat's explicit "go". No upgrade, no paid resource, no GPU quota request without that "go". Deploy code is restored path by path from `458207c^`, not by reverting the commit (F7).
**Consequences:** corrects B-ADR-16's premise; B-ADR-16's local-only rule stands for everything before C5.1.

## C-ADR-11 Bias rule for gold — proposed

**Context:** the gold scores Claude, ChatGPT and FinSight; pre-fill from any one of them could anchor the verifier (F28).
**Decision:** every gold value is verified by Akshat on the PDF page. Pre-fill mixes FinSight and Claude-chat values with the source hidden; each field records whether it was changed; the source key is applied by script afterwards to report change rates per source. Gold v4 covers Task A fields and every red-flag input (F33).
**Consequences:** more verification time (C06); AI-assisted pre-fill is disclosed (`label_source`).

## C-ADR-12 Kickoff scope: cuts 1–5, critical path and cut line — accepted

**Context:** the course deadline (CLAUDE.md header) leaves about 19 build days for about 30 parts, ~31 h of Akshat's hand-work and ~15 A100 hours (F2).
**Decision:** cuts 1–5 of C05 §5 are applied now: 8B student, BIR backfill (C1.5), large classifier, Compare-window rework (C3.4), bench Task E. The bench is 6 documents + 2 bench-dev. The critical path and the ranked cut line in C05 §6 decide any further cut. Approved by Akshat at the kickoff review.
**Consequences:** the large classifier and 8B student are not reported; the Compare tab keeps provisional, labelled data; consistency is stated as a property of a deterministic pipeline, not measured against frontier apps.
