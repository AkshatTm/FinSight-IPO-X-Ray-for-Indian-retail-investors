# Phase 4 handoff pack (CC to ARGON)

Built by `scripts/export_handoff.py` from saved Phase 3 artefacts at tag `v1.0`; nothing here was
re-labelled or re-run except where stated. Read `context/` first, then `eval/baselines.json`.
Interfaces are frozen (`context/interfaces.md`); ask CC in `comms/to_cc.md` for changes.
The README numbers are written by the exporter from `export_stats.json`, not typed.

## Where the big files are
Files over 4.5 MB are not in git. They are in the private HF dataset repo `AkshatTm/finsight-gpu-jobs` under
`phase4/handoff/data/` at commit `a285902d91a5557cf6d6d7cf23a9e266410d6c3d`: classifier_train.jsonl.gz, risk_bank.parquet, student_v1_train.jsonl.gz. `colab/setup_cell.py` downloads the pack and
checks every file against `data/MANIFEST.json` (sha256). Akshat puts an HF read token in Colab
secrets as `HF_TOKEN`.

## The exclusion rule (read this twice)
`data/excluded_ipos.json` lists 128 IPOs that must NEVER enter any training set: all
test-slice IPOs, SME/unusable IPOs, demo and showcase IPOs, Bench v1 IPOs and Platform Bench IPOs
(Jio included). Splits are by IPO (`data/splits_by_ipo.json`, with the train cut-off date). The one
disclosed exception is Jio as an SOD fixture (parser diagnosis only). The files below drop excluded
IPOs, except the sets marked EVAL ONLY.

## Files in `data/`
| File | Rows | What | label_source |
|---|---|---|---|
| `excluded_ipos.json`, `splits_by_ipo.json` | | exclusion list with reasons; frozen Phase 3 split | n/a |
| `risk_bank.parquet` | 29433 | train+dev risk factors: `risk_id, ipo_id, company, year, doc_date, split, title, text, page, page_end, category, severity_band, severity_source, rule_seriousness, label_source` | `ai` for 10892 rows (category + band 1-4 from the Gemma-4-31B teacher), `model` for 18541 (category predicted by the shipped classifier, no band) |
| `classifier_train.jsonl.gz`, `classifier_dev.jsonl.gz` | 9832 / 1060 | `risk_id, ipo_id, company, text, label (category), band (1-4)` | `ai` (teacher) |
| `classifier_test.jsonl.gz` | 150 | gold-150. EVAL ONLY: risks of test-slice IPOs (`eval_only` flag) | `human_verified_ai` (Akshat verified) |
| `student_v1_train.jsonl.gz`, `student_v1_dev.jsonl.gz` | 10362 / 529 | rewrite SFT pairs in chat `messages` form, with `ipo_id` | `ai` (teacher) |
| `student_prompt_template.txt` | | frozen risk-rewrite prompt (`student-v1`); placeholders `{{TITLE}}`, `{{BODY}}` | n/a |
| `student_chat_template.txt`, `student_chat_template_hi.txt` | | frozen chat prompt; placeholders `{{QUESTION}}` (twice), `{{PASSAGE_BLOCKS}}`; a block is `[n] (RHP page p)` then the text | n/a |
| `serious_finding_hits.jsonl.gz` | 2801 | every sentence a severe pattern matched, from 275 documents, with the rules' `rules_decision` (`fired`, `blocked_soft`, `blocked_no_debt`); counts: {'blocked_no_debt': 18, 'blocked_soft': 2469, 'fired': 314}. Fields: `id, ipo_id, slice, excluded, check_id, page, sentence, context_before, context_after, rules_decision` | `rule` |
| `five_things_selection.jsonl.gz` | 2147 | what the "Five things" card picked per IPO (437 train+dev IPOs): top 5 by importance. M2 baseline | `rule` |
| `bench_v1/` | | frozen FinSight Bench v1 items, keys, prompts and stored retrieval. EVAL ONLY | gold v3 (human) |
| `gold/` | | gold-150, gold-50 sheet and ratings, gold v3 / v3.1, red-flag status gold. EVAL ONLY | see `gold/README.md` |

## Known gaps (do not assume these exist)
- `risk_bank.parquet`: `section` is empty (the bank does not store it); `severity_band` exists only
  for the teacher-labelled rows; 107 rows have no body text (title only).
- There is **no chat-answer SFT data** yet. `student_v1_*` are risk-rewrite pairs only. The chat side
  of M1 (answerable / unanswerable questions over passages) is new data you generate (AR-04).
- `serious_finding_hits` covers the 2024+ parsed offer documents (word boxes); the 2009-2023 corpus
  IPOs have page text only and are not included. Rows with `slice=test` are evaluation-only.
- The student SFT split here is 10362 train / 529 dev (the local split of the clean teacher
  pairs); C-ADR-18 quotes 10,307 / 527 for the 8B run (a training-time filter on the same pairs).
- Bench v1 numbers are a single run on 7 IPOs; the severe-band recall rests on 58 dev rows. Both are noisy.
- M4's interface is the seriousness band head (1-4); see `context/interfaces.md`.

## Eval tools (`eval/`)
`baselines.json` (every number to beat, with the source file's sha256), `run_classifier_eval.py` (3-seed
mean and std plus verdict, no product import), `numkeep.py` (M1 number-keeping filter),
`run_bench.py` (Bench v1 Tasks A / C for a student candidate; runs on the laptop in the product repo),
`vendor/finsight_lite` (stand-alone copy of the product's number normaliser and metrics).

## Colab
`colab/setup_cell.py` (Drive mount, pack download and checksum, pinned deps, seeds 13 / 42 / 2026,
checkpoint every epoch to `/content/drive/MyDrive/finsight_p4/<job>`) and `colab/requirements_colab.txt`
(pins from the product lock; torch comes from the Colab image). Every notebook runs `DEBUG=True` on a
T4 before any G4 run.
