"""Field extractors (rules, pretrained QA, fine-tuned QA, BiLSTM-CRF) and the X-Ray builder."""

from finsight.extract.fields import field_ids, get_field, load_fields
from finsight.extract.passages import QAPassage, build_passages
from finsight.extract.qa_pretrained import QAExtractor, RawAnswer
from finsight.extract.rules import RulesExtractor
from finsight.extract.select import Selection, select_field
from finsight.extract.table import TableExtractor, objects_pure_ofs
from finsight.extract.xray import DocInputs, build_xray

__all__ = [
    "DocInputs",
    "QAExtractor",
    "QAPassage",
    "RawAnswer",
    "RulesExtractor",
    "Selection",
    "TableExtractor",
    "build_passages",
    "build_xray",
    "field_ids",
    "get_field",
    "load_fields",
    "objects_pure_ofs",
    "select_field",
]
