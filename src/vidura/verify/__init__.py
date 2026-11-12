"""Claims, numeric checks, consistency checks and verdicts."""

from vidura.verify.claims import AnswerClaim, AnswerNumber, split_claims
from vidura.verify.consistency import CHECK_TOTAL, ConsistencyReport, check_consistency
from vidura.verify.metrics import MetricIndex, find_metrics, metric_at
from vidura.verify.numeric_check import (
    EvidenceAmount,
    NumericCheck,
    check_number,
    evidence_amounts,
    is_scale_mismatch,
    same_value,
)
from vidura.verify.verdict import (
    AnswerVerdict,
    NumberVerdict,
    answer_score,
    format_verdicts,
    verify_answer,
)

__all__ = [
    "CHECK_TOTAL",
    "AnswerClaim",
    "AnswerNumber",
    "AnswerVerdict",
    "ConsistencyReport",
    "EvidenceAmount",
    "MetricIndex",
    "NumberVerdict",
    "NumericCheck",
    "answer_score",
    "check_consistency",
    "check_number",
    "evidence_amounts",
    "find_metrics",
    "format_verdicts",
    "is_scale_mismatch",
    "metric_at",
    "same_value",
    "split_claims",
    "verify_answer",
]
