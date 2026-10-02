"""The tokenizer shared by the BIO labels and the BiLSTM-CRF extractor (P5.3).

A number with its commas and decimals stays one token ("19,000.50"); words; single symbols.
Training (``weaklabel.bio``), the Kaggle notebook (its baseline) and inference must split text
the same way, so the pattern lives here once; ``tests/extract/test_bilstm_crf.py`` checks that
the notebook's copy has not drifted.
"""

from __future__ import annotations

import re

TOKEN_PATTERN = r"\d+(?:,\d+)*(?:\.\d+)?|\w+|[^\w\s]"
TOKEN = re.compile(TOKEN_PATTERN)


def tokenize(text: str) -> list[tuple[str, int, int]]:
    """``(token, start, end)`` with character offsets into ``text``."""
    return [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(text)]
