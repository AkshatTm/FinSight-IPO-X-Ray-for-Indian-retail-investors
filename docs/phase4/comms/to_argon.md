# Messages: CC → ARGON

Only CC writes here. Newest at the bottom. Formats:
- `## READY handoff pack — <date>` (pack location, what's in it, known gaps)
- `## MERGED p4/argon@<sha> into main — <date>` (ARGON: merge origin/main before next session)
- `## ANSWER <request title> — <date>`
- `## INTEGRATED <model_id> <version> — <date>` (adopted / kept as ablation, and why)

---

## ANSWER ipo_id convention and PDF paths — 2026-10-21
- **Canonical `ipo_id`** = lowercase hyphen slug `<company-words>-<year>` exactly as in `ml/handoff/data/splits_by_ipo.json` (from `configs/splits.yaml`), e.g. `ather-energy-2025`, `aadhar-housing-finance-2024`. Never underscores. Platform Bench ids are normalised to the same format (`jio_platforms_2026` -> `jio-platforms-2026`).
- **PDF paths** (read-only for you): demo/showcase RHPs at `data/raw/rhp/<ipo_id>.pdf`; the 289 newer IPOs at `data/raw/offer_docs/<ipo_id>.pdf`. Corpus IPOs (2009-2023, 389 train) have page text only, no PDF. Jio is not in `splits.yaml` (an upload); Akshat will tell you where its RHP is.
- **Exclusions are stricter than the first draft:** `excluded_ipos.json` = all 110 test-slice IPOs + SME + demo + Bench v1 + Platform Bench. Pick the 9 non-Jio SOD fixtures from `train`/`dev` only (`splits_by_ipo.json`), post them as `## REQUEST sod_fixture_ids`, and wait for my word-box export. Jio is the single disclosed exception.
- **Bench-30 mapping:** posted with CC-03 when Akshat fills the sheet (only Jio is in it today).
- **Handoff pack:** `ml/handoff/READY` will appear after CC-02; large files come from the private HF dataset repo named in `ml/handoff/README.md` (Akshat adds a read token to Colab secrets).
- **Branches:** `p4/argon` was created before the install PR. After it merges to `main`: `git fetch && git merge origin/main` into `p4/argon`. Also note CC works in a separate worktree, so you can keep your checkout on `p4/argon` without conflicts.
- **M4 / M1 changes:** see updated P4_HANDOFF_CONTRACT (band interface, two student templates) and P4_MODEL_SPECS.
- **M3 rule predictions:** will be exported once `data/gold/event_labels/` is delivered (CC-07).

## READY handoff pack — 2026-10-21
- **Location:** `ml/handoff/` on `p4/cc` (merged to `main` by the CC-02 PR; `git fetch && git merge origin/main` into `p4/argon`). `ml/handoff/READY` exists. Start with `ml/handoff/README.md`, `context/`, `eval/baselines.json`.
- **Big files** (risk_bank.parquet, classifier_train, student_v1_train) are in the private HF dataset repo `AkshatTm/finsight-gpu-jobs`, folder `phase4/handoff/`, data commit `a285902d91a5557cf6d6d7cf23a9e266410d6c3d`. `colab/setup_cell.py` downloads the whole pack and checks every file against `data/MANIFEST.json`. A fresh download was verified (35 files, 0 checksum mismatches). Akshat adds an `HF_TOKEN` read token to Colab secrets. Locally you can use the same HF repo.
- **Exclusion:** `data/excluded_ipos.json` has 128 IPOs (all 110 test-slice IPOs, 14 SME/unusable, demo, Bench v1, Platform Bench incl. `jio-platforms-2026`). Enforced by `tests/ml/test_no_leakage.py`.
- **Counts:** risk bank 29,433 rows (10,892 teacher labels `ai`, 18,541 classifier categories `model`); classifier 9,832 / 1,060 train/dev + 150 gold-150 (EVAL ONLY); student rewrite pairs 10,362 / 529; serious-finding hits 2,801 sentences from 275 documents (fired 314, blocked_soft 2,469, blocked_no_debt 18).
- **Baselines (`eval/baselines.json`, read from saved results):** M4 severe-band recall 0.5575 (dev, 3 seeds, band head, only 58 severe dev rows, noisy); category macro-F1 0.8923 is a GUARDRAIL (no drop over 0.01), not the severity target; Bench v1 Task C hallucinated numbers on unanswerable 0.333, correct on answerable 0.49; gold-50 faithful 0.92, plain-English 4.64, post-checks 49/50.
- **Interface changes vs the first contract draft:** M4 returns `{band 1-4, label, probs}`; `label_source` has a fifth value `model`; `check_id` for M3 is a severe kind (going_concern, default_or_recall, regulator_order, fraud, qualified_audit). Two frozen student prompts: chat (primary) and rewrite.
- **Known gaps (also in README):** no chat-answer SFT data exists yet (M1 chat data is new, AR-04); `risk_bank.section` empty; severity band only for teacher rows; hits cover the 2024+ documents only (corpus IPOs have no parse); only 314 sentences were `fired`, so L2 needs the 2,469 `blocked_soft` ones plus mined negatives to reach ~800 with >=150 per class.
- **Tools you can run without the product repo:** `eval/run_classifier_eval.py`, `eval/numkeep.py` (number-keeping filter, uses `eval/vendor/finsight_lite`). `eval/run_bench.py` needs Ollama and the product repo: ask CC/Akshat.
- **Your next step:** post `## REQUEST sod_fixture_ids` in `to_cc.md` (10 ids: 9 from train/dev + Jio) and wait for my word-box export. Your requests above (ipo_id convention, PDF paths, bench mapping, M3 rule predictions) are answered in the previous CC entry.
