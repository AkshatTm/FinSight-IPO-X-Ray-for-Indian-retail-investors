# Vidura Bench v1

A small, pre-registered benchmark that asks every system the same questions about the same 7 test-slice
IPOs, with the same retrieved passages and the same prompt text (C-ADR-06, C-ADR-24). It is frozen:
the files listed in `bench/v1/manifest.yaml` `frozen_files` never change; a new version would get
`bench/v2/`.

## What is in it

| Part | Where |
| --- | --- |
| Documents | 7 test-slice showcase IPOs (all 2025): Groww, HDB Financial Services, Lenskart, LG Electronics India, Meesho, PhysicsWallah, Tata Capital |
| Items | `bench/v1/items/task_{a,c,d,g}.jsonl` |
| Keys | `bench/v1/keys/`, copied from Akshat-verified gold v3 and the status gold |
| Prompts as sent | `bench/v1/inputs/prompts.jsonl.gz` (templates in `bench/v1/prompts/`) |
| Scoring | `bench/v1/scoring.yaml`, `bench/v1/pinned/redflags.yaml` |
| Answers | `bench/v1/answers/<system>/` |
| Results | `eval_results/c4/bench_summary.json`, `bench_rules_v1.json`, `bench_student.json`, `bench_failures.json` |

**Tasks:** A key facts (NVM against gold v3); B red-flag statuses (computed by the same rule engine from
each system's Task A answers); C questions, including 3 unanswerable ones per IPO; D plain-English
rewrites; G advice probes that must be refused.

## Results (single run, 95 % bootstrap intervals over IPOs)

From [`eval_results/c4/bench_summary.json`](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/c4/bench_summary.json)
(written 16 Oct 2026, carried into v1.1):

| Task | Metric | rules_v1 | student | n |
| --- | --- | --- | --- | --- |
| A | key facts, NVM | 0.724 [0.636, 0.816] | 0.340 [0.282, 0.395] | 156 |
| B | red-flag status accuracy | 0.703 [0.582, 0.824] | 0.473 [0.429, 0.527] | 91 |
| C | correct on answerable questions | 0.327 [0.245, 0.388] | 0.490 [0.388, 0.612] | 49 |
| C | abstains on unanswerable | 0.857 [0.762, 0.952] | 0.333 [0.190, 0.476] | 21 |
| C | hallucinated number on unanswerable | 0.048 [0.000, 0.143] | 0.333 [0.190, 0.476] | 21 |
| D | rewrite post-checks passed | — | 0.886 [0.771, 0.971] | 35 |
| G | advice probes refused | 1.000 [1.000, 1.000] | 0.429 [0.238, 0.571] | 21 |

**Paired comparison, student vs rules_v1** (McNemar): A worse (−0.385 [−0.506, −0.264]), B worse
(−0.231 [−0.385, −0.055]), C correct on par (−0.043 [−0.129, 0.071], p = 0.66), G worse
(−0.571 [−0.762, −0.429]).

**Systems.** `rules_v1` is the Vidura pipeline: rule extraction for A and B, and for C the Phase 1
chat with `qwen3.5:2b` and the guard. `student` is `finsight-student:q4` answering from the same
passages without the pipeline's rules or guard. In the product, the guard declines advice questions
before any model runs, so Task G for the student is a model-only probe.

## What did not run

- **Teacher, Claude Opus (app and API), ChatGPT Go**: listed as pending systems in the file; their
  answers were never collected. The frontier comparison (E9) therefore has no numbers.
- **Base Qwen3-4B**: 23 of 225 items answered; not scored.

## Disclosures (from the file)

- The 7 bench IPOs are the only test IPOs whose gold Akshat verified; the 4 newest 2026 IPOs would
  need gold v4 (cut).
- 2025 IPOs may be in frontier models' training data.
- There is no bench-dev set: error analysis on bench items is descriptive, and any fix it motivated is
  disclosed as test-informed. See [Bench error analysis](../phase3/bench_error_analysis.md).
- Task B is structurally easier for `rules_v1`, whose statuses come from the engine the gold was built
  with.
- Task C questions and the unanswerable ones were written by Claude Code from templates, not by Akshat.
- The scorer changed after the freeze in four documented ways (`post_freeze_scorer_changes`); none
  changed a correctness metric.

## Re-run

```bash
uv run python scripts/bench_run.py --system rules_v1 --processed data/processed   # Ollama running
uv run python scripts/bench_run.py --system student
uv run python scripts/bench_score.py
```

Not re-run for v1.1 (it needs the full documents in `data/processed/` and Ollama). Frontier and teacher
instructions are in [`bench/README.md`](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/bench/README.md).

## Platform Bench (cut)

Phase 4 planned a second benchmark ("Platform Bench", CC-03 / CC-10): 30 recent IPOs, comparing
Vidura with what Groww, Zerodha and AngelOne show for each, from pages Akshat would collect by hand.
The spreadsheet exists on the laptop (gitignored), but nothing was ingested or scored, and the work was cut when Phase 4
closed. Only the README of `data/platform_bench/` is in git; there is no `eval_results/p4/`.
