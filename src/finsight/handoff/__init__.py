"""Phase 4 handoff pack (CC-02): the frozen data, baselines and interfaces ARGON works from.

``scripts/export_handoff.py`` builds ``ml/handoff/`` from the product repo's saved artefacts. This
package holds the pure parts: the exclusion rule (``selection``), row exports (``tables``), the two
frozen student prompt templates (``templates``), the baselines (``baselines``), a stand-alone copy
of the number normaliser for notebooks (``vendor``) and the file manifest (``manifest``). Nothing
here trains or scores a model; it exports what exists.
"""

from finsight.handoff.baselines import build_baselines
from finsight.handoff.manifest import GIT_LIMIT_BYTES, build_manifest, sha256_file, write_manifest
from finsight.handoff.selection import RULE, excluded_ipos, splits_by_ipo
from finsight.handoff.tables import (
    five_things,
    ipo_of,
    risk_bank_rows,
    with_ipo,
    write_jsonl_gz,
    write_parquet,
)
from finsight.handoff.templates import chat_template, rewrite_template
from finsight.handoff.vendor import build_lite

__all__ = [
    "GIT_LIMIT_BYTES",
    "RULE",
    "build_baselines",
    "build_lite",
    "build_manifest",
    "chat_template",
    "excluded_ipos",
    "five_things",
    "ipo_of",
    "rewrite_template",
    "risk_bank_rows",
    "sha256_file",
    "splits_by_ipo",
    "with_ipo",
    "write_jsonl_gz",
    "write_manifest",
    "write_parquet",
]
