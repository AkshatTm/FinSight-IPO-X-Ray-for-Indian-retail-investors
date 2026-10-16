"""FinSight Bench (C04, C4.1): frozen items, identical prompts for every system, and scoring.

The bench compares the FinSight pipeline, its own models (student, base, teacher) and frontier
models on the ``bench`` slice of ``test`` IPOs, with the same retrieved passages and the same
prompt text for every system. ``scripts/bench_build.py`` writes and freezes ``bench/<v>/``;
``scripts/bench_run.py`` (local systems), ``scripts/bench_frontier.py`` (paste bundles or API)
and ``scripts/bench_vllm_job.py`` (the teacher on Colab) write answers; ``scripts/bench_score.py``
scores them. This package holds the pure parts: field texts, item builders, prompt rendering,
answer parsing, scoring rules, statistics and the freeze guard.
"""

from finsight.bench.answers import (
    FieldAnswer,
    TaskAReply,
    bundle,
    parse_task_a,
    split_bundle,
)
from finsight.bench.fields import FIELDS, GROUPS, PERIODS, describe, field_id
from finsight.bench.items import (
    Question,
    guard_questions,
    pick_rewrites,
    short_name,
    task_c,
)
from finsight.bench.manifest import (
    Manifest,
    changed_files,
    dump,
    hashes,
    input_files,
    load,
    sha256,
    unlisted_inputs,
)
from finsight.bench.prompts import (
    CHAT_BUDGET_CHARS,
    TASK_A_BUDGET_CHARS,
    chat_prompt,
    fit,
    rewrite_prompt,
    task_a_prompt,
)
from finsight.bench.score import (
    Patterns,
    advice,
    amounts,
    gold_amount_from_row,
    refused,
    score_guard,
    score_question,
    score_rewrite,
)
from finsight.bench.stats import mcnemar_exact, metric, paired, per_ipo

__all__ = [
    "CHAT_BUDGET_CHARS",
    "FIELDS",
    "GROUPS",
    "PERIODS",
    "TASK_A_BUDGET_CHARS",
    "FieldAnswer",
    "Manifest",
    "Patterns",
    "Question",
    "TaskAReply",
    "advice",
    "amounts",
    "bundle",
    "changed_files",
    "chat_prompt",
    "describe",
    "dump",
    "field_id",
    "fit",
    "gold_amount_from_row",
    "guard_questions",
    "hashes",
    "input_files",
    "load",
    "mcnemar_exact",
    "metric",
    "paired",
    "parse_task_a",
    "per_ipo",
    "pick_rewrites",
    "refused",
    "rewrite_prompt",
    "score_guard",
    "score_question",
    "score_rewrite",
    "sha256",
    "short_name",
    "split_bundle",
    "task_a_prompt",
    "task_c",
    "unlisted_inputs",
]
