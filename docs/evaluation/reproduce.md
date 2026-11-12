# Reproduce the numbers

Every row of the [v1.1 scorecard](../evaluation.md#v11-scorecard) is either **re-measured** (run again
for v1.1 on 3 Nov 2026) or **carried** (the last Phase 3 / Phase 4 run, not repeated because it needs a
GPU or a long CPU job). This page gives the command behind each result file.

Most commands read the cached parses in `data/processed/` (built from the PDFs, which are not in git)
and the gold files in `data/gold/`. They never train anything and never read test documents for
tuning (C-ADR-02). Write to a scratch path with `--out` when you only want to check a number: the files
in `eval_results/` are the record and are never edited by hand.

## Re-measured for v1.1 (verified again on 7 Nov 2026)

These four were run again while writing these docs, into a scratch folder, and gave identical results
to the committed files:

| Result | Command | Time on the laptop |
| --- | --- | --- |
| E14 summary extraction (`final/e14_today.json`) | `uv run python scripts/summary_eval.py --slice all --final --out eval_results/final/e14_today.json` | 48 s |
| E15 red-flag statuses (`final/e15_today.json`) | `uv run python scripts/redflag_eval.py --slice all --final --out eval_results/final/e15_today.json` | 57 s |
| C-ADR-26 count (`final/severe_about.jsonl`) | `uv run python scripts/final_severe_about.py > eval_results/final/severe_about.jsonl` | under 1 min |
| E14 / E15 history (`c/e14_e15_versions.json`) | `uv run python scripts/e14_e15_versions.py` | seconds (reads result files only) |

The Jio Platforms rows and the stage timings come from a live upload through the running app:

```bash
uv run python scripts/preload.py path/to/jio-platforms-rhp.pdf   # appends a row to data/preload_log.csv
curl -s http://127.0.0.1:8000/api/docs/doc_72480c2e249eb8da/redflags
```

## Carried (not re-run for v1.1)

| Result | How it was made | Needs |
| --- | --- | --- |
| Extractor ladder, E2 / E3 / E11 (`ladder_table.json`, `extractor_metrics-*.json`, `bilstm_metrics-*.json`) | Kaggle notebooks `notebooks/01_finetune_extractor.ipynb`, `02_bilstm_crf.ipynb`; then `uv run python -m finsight.evaluate.run_gold` and `uv run python -m finsight.evaluate.ladder` | Kaggle GPU, weights |
| Extractor v1 / v2 on the v3 dev set (`c/extractor_v1_on_v3dev.json`, `c/extractor_v2/`) | `scripts/extractor_v2.py`, `extractor_v2_compare.py`, `extractor_v2_gold.py` | Kaggle GPU |
| Classifier base, E16 (`b/classifier_base.json`, `b/classifier_tfidf.json`) | `uv run python scripts/classifier_kaggle.py push run`, `status`, `fetch`, `summary` | Kaggle GPU |
| Classifier large (`c/classifier_large.json`) | Colab job `classifier_large` through `scripts/gpu_jobs.py`, then `scripts/classifier_large_summary.py` | Colab G4 |
| ONNX export check (`c/classifier_onnx_check.json`) | `uv run python scripts/export_onnx_classifier.py --model <seed folder>` | the trained weights |
| Gold-150 agreement (`c/gold150_verification.json`) | `scripts/gold_sets.py` (`sample`, `sheet150`, `gold150`) | Akshat's review |
| Student gold-50, E18 (`c/simplify_gold50.json`) | `scripts/gold_sets.py sheet50` / `score50` on Akshat's blind ratings | the ratings |
| Student post-checks and E19 / E20 (`c/student_vs_base_gold50.json`, `c/student_eval.json`) | `uv run python scripts/student_vs_base.py`, `uv run python scripts/student_eval.py --n-dev 60` | Ollama with the student and the base model |
| 8B student (`c/student_8b_vs_4b_gold50.json`) | Colab job `student_8b`, then `scripts/student_8b_eval.py` | Colab G4 |
| Teacher bake-off (`c/teacher_bakeoff.json`) | Colab job `bakeoff` (`docs/phase3/COLAB_STEPS_teacher_bakeoff.md`), `scripts/teacher_bakeoff.py` | Colab G4 |
| Bench v1 (`c4/bench_*.json`) | `scripts/bench_run.py`, `scripts/bench_score.py` ([Bench](bench.md)) | Ollama, full documents |
| Retrieval E6, chat E7, latency E10 (`retrieval.json`, `e7.json`, `latency.json`) | `finsight.retrieve.evaluate`, `finsight.evaluate.answers`, `finsight.evaluate.latency` | Ollama, profile `full` |
| Verifier E5 (`verifier.json`) | `finsight.evaluate.seeded_errors` | — |
| Guard E8 (`guard.json`, `guard_clf.json`, `guard_compare.json`) | `uv run python -m finsight.evaluate.guard_eval`; MuRIL via `finsight.guard.kaggle_clf` | Kaggle for MuRIL |
| Decided checks over 289 RHPs (1,561 → 1,714) | `uv run python scripts/p4_decided_counts.py --data-root <checkout> --out <file>` and `--compare` | cached parses of all 289 |
| Risk-level fit (`b/risklevel_fit.json`, `c/risklevel_scoring.json`) | `scripts/score_reference_ipos.py`, `scripts/validate_risklevel.py` | classifier on the GPU |
| Corpus stats (`corpus_stats.json`) | the corpus builder in `finsight.ingest` | the Ghosh corpus |

Commands in this table were taken from each script's own usage text and were not run again for these
docs.

## Compute log

Every GPU job on Kaggle and Colab is appended to `eval_results/c/compute_log.jsonl` by
`scripts/log_compute.py` ([Training lanes](../operations/training-lanes.md#compute-log)).
