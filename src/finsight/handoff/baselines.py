"""``baselines.json``: every current number ARGON must beat, taken from saved result files.

Nothing is re-run or typed by hand: each number is read from a committed result file and the
file's path and sha256 are recorded beside it. Severity is reported exactly as it is measured:
the seriousness *band* head of the shipped DeBERTa-v3-base classifier on the dev split
(IPO-disjoint from train), mean of three seeds, with the support that makes the severe numbers
noisy. The category macro-F1 is a separate guardrail, not a severity target.
"""

from __future__ import annotations

from typing import Any


def _pick(d: dict[str, Any], *path: str) -> Any:
    cur: Any = d
    for key in path:
        cur = cur[key]
    return cur


def build_baselines(
    classifier: dict[str, Any],
    band_seed_metrics: dict[str, Any],
    bench: dict[str, Any],
    gold50_rating: dict[str, Any],
    gold50_checks: dict[str, Any],
    student_eval: dict[str, Any],
    sources: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Assemble the baselines.

    Args:
        classifier: ``eval_results/b/classifier_base.json`` (category + seriousness, 3 seeds).
        band_seed_metrics: ``models/risk_classifier/metrics-band-42.json`` (for the dev support).
        bench: ``eval_results/c4/bench_summary.json`` (Bench v1 results, systems student/rules_v1).
        gold50_rating: ``eval_results/c/simplify_gold50.json`` (human rating, Akshat, blind).
        gold50_checks: ``eval_results/c/student_vs_base_gold50.json`` (post-checks).
        student_eval: ``eval_results/c/student_eval.json`` (readability, CPU timing).
        sources: ``{name: {"path": ..., "sha256": ...}}`` recorded as provenance.
    """
    cat = classifier["category"]
    ser = classifier["seriousness"]
    dev_support = _pick(band_seed_metrics, "dev", "severe_support")
    student = bench["systems"]["student"]
    rules = bench["systems"]["rules_v1"]
    return {
        "note": (
            "All numbers are copied from the result files in `sources`; none are typed by hand. "
            "Single run unless a seed list is given. Teacher labels for the classifier are AI "
            "labels; gold-150 and gold-50 ratings are human (Akshat)."
        ),
        "m4_severity": {
            "what": (
                "Seriousness band head (bands 1-4, 4 = severe; levels 4 and 5 merged) of "
                "microsoft/deberta-v3-base. 'Severe recall' is the recall of band 4."
            ),
            "split": "dev (IPO-disjoint from train), label_source ai (teacher) bands",
            "seeds": ser["seeds"],
            "n_dev": cat["n_dev"],
            "severe_support_dev": dev_support,
            "severe_recall_mean": ser["dev_mean"]["severe_recall"],
            "severe_precision_mean": ser["dev_mean"]["severe_precision"],
            "band_macro_f1_mean": ser["dev_mean"]["macro_f1"],
            "band_mae_mean": ser["dev_mean"]["mae"],
            "by_seed": ser["dev_by_seed"],
            "caveat": "Severe support is small (about 58 dev rows), so the recall is noisy.",
            "target": {"severe_recall_min": 0.70},
        },
        "guardrail_category": {
            "what": "10-way risk category macro-F1; must not regress (drop <= 0.01).",
            "split": "dev",
            "seeds": cat["seeds"],
            "dev_macro_f1_mean": cat["dev_macro_f1_mean"],
            "dev_macro_f1_sd": cat["dev_macro_f1_sd"],
            "gold150_test_macro_f1_mean": cat["test_macro_f1_mean"],
            "gold150_label_source": cat["test_label_source"],
            "max_drop": 0.01,
        },
        "m1_chat_bench_v1": {
            "what": (
                "Bench v1 Task C (chat questions on 7 test-slice showcase IPOs; frozen retrieved "
                "passages), finsight-student:q4. Single run."
            ),
            "n_ipos": 7,
            "hallucinated_number_on_unanswerable": student["C"]["hallucinated_number_unanswerable"],
            "abstention_on_unanswerable": student["C"]["abstention_unanswerable"],
            "correct_on_answerable": student["C"]["correct_answerable"],
            "verified_share": student["C"]["verified_share"],
            "target": {"hallucinated_max": 0.10, "correct_answerable_min": 0.49},
            "rules_v1_task_a": rules["A"],
            "student_task_a": student["A"],
            "student_task_b": student["B"],
        },
        "m1_rewrite_gold50": {
            "what": "Risk rewrite on gold-50 (test slice), human blind rating by Akshat.",
            "faithful_yes_share": _pick(gold50_rating, "systems", "student", "faithful_yes_share"),
            "faithful_yes_ci95": _pick(gold50_rating, "systems", "student", "faithful_yes_ci95"),
            "plain_english_mean": _pick(gold50_rating, "systems", "student", "plain_english_mean"),
            "post_check_pass": _pick(gold50_checks, "systems", "student", "passed"),
            "post_check_n": gold50_checks["n"],
            "mean_words": _pick(gold50_checks, "systems", "student", "mean_words"),
            "readability_fkgl_drop": _pick(student_eval, "e19_readability", "gold50", "fkgl_drop"),
            "must_not_regress": {"faithful_min": 0.92, "plain_min": 4.5, "post_check_min": 49},
        },
        "m3_event_rules": {"baseline": "rules_v1 (finsight.redflags.severe)", "primary": None},
        "m2_five_things": {
            "baseline": "importance rank (five_things_selection.jsonl)",
            "ndcg7": None,
        },
        "sources": sources,
    }
