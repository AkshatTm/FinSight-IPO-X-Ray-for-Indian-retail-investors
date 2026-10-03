"""Risk intelligence: teacher prompt and filters, rewrite checks (numbers, phrases, length,
certainty), the category classifier (TF-IDF baseline, ONNX int8 serving); segmentation and
simplification arrive with B2.1 and B2.5."""

from finsight.risks.certainty import certainty_changed
from finsight.risks.checks import unmatched_numbers, word_count
from finsight.risks.classify import (
    Example,
    OnnxClassifier,
    TfidfBaseline,
    predict,
    split_by_company,
)
from finsight.risks.clf_metrics import scores
from finsight.risks.filters import FilterReport, Kept, TeacherItem, check_one, filter_outputs
from finsight.risks.teacher import (
    CATEGORIES,
    OUTPUT_SCHEMA,
    PROMPT_VERSION,
    ParseError,
    TeacherOutput,
    messages,
    parse_output,
)

__all__ = [
    "CATEGORIES",
    "OUTPUT_SCHEMA",
    "PROMPT_VERSION",
    "Example",
    "FilterReport",
    "Kept",
    "OnnxClassifier",
    "ParseError",
    "TeacherItem",
    "TeacherOutput",
    "TfidfBaseline",
    "certainty_changed",
    "check_one",
    "filter_outputs",
    "messages",
    "parse_output",
    "predict",
    "scores",
    "split_by_company",
    "unmatched_numbers",
    "word_count",
]
