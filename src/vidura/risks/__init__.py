"""Risk intelligence: features (numbers, hedging, novelty against the risk bank), the category
classifier (TF-IDF baseline, ONNX int8 serving), plain-English rewrites with post-checks, and
the teacher that makes their training data, and segmentation of the Risk Factors section into
single risks (PDF pages with fonts, or corpus text)."""

from vidura.risks.bank import RiskBank, company_key, load_bank, risks_config
from vidura.risks.certainty import certainty_changed
from vidura.risks.checks import unmatched_numbers, word_count
from vidura.risks.classify import (
    Example,
    OnnxClassifier,
    TfidfBaseline,
    predict,
    split_by_company,
)
from vidura.risks.clf_metrics import scores
from vidura.risks.features import Embedder, add_features
from vidura.risks.filters import FilterReport, Kept, TeacherItem, check_one, filter_outputs
from vidura.risks.hedging import hedge_count, hedging
from vidura.risks.novelty import NoveltyResult, embed_text, novelty, unusualness_label
from vidura.risks.numbers import risk_numbers
from vidura.risks.readability import fkgl
from vidura.risks.segment import RiskSpan, segment_pages, segment_text, to_risks
from vidura.risks.seriousness import ranked_rids, score_risks
from vidura.risks.simplify import (
    Rewrite,
    Simplifier,
    make_simplifier,
    post_check,
    student_prompt,
)
from vidura.risks.simplify import clean as clean_rewrite
from vidura.risks.teacher import (
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
    "Embedder",
    "Example",
    "FilterReport",
    "Kept",
    "NoveltyResult",
    "OnnxClassifier",
    "ParseError",
    "Rewrite",
    "RiskBank",
    "RiskSpan",
    "Simplifier",
    "TeacherItem",
    "TeacherOutput",
    "TfidfBaseline",
    "add_features",
    "certainty_changed",
    "check_one",
    "clean_rewrite",
    "company_key",
    "embed_text",
    "filter_outputs",
    "fkgl",
    "hedge_count",
    "hedging",
    "load_bank",
    "make_simplifier",
    "messages",
    "novelty",
    "parse_output",
    "post_check",
    "predict",
    "ranked_rids",
    "risk_numbers",
    "risks_config",
    "score_risks",
    "scores",
    "segment_pages",
    "segment_text",
    "split_by_company",
    "student_prompt",
    "to_risks",
    "unmatched_numbers",
    "unusualness_label",
    "word_count",
]
