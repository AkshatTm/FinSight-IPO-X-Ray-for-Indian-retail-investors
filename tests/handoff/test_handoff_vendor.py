"""The stand-alone normaliser copy behaves like the product's and imports no product code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from finsight.handoff import build_lite
from finsight.risks.checks import unmatched_numbers

ROOT = Path(__file__).resolve().parents[2]

PAIRS = [
    (
        "Issue size is ₹1,234.56 crore for 3 plants in Fiscal 2024.",
        "The issue is ₹1,235 crore for 3 plants in Fiscal 2024.",
    ),
    ("Debt was ₹500 million.", "Debt was ₹900 million."),
    ("Promoters hold 62.5% of shares.", "Promoters hold 62.5% and 12 directors."),
]

_CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
from finsight_lite.numcheck import unmatched_numbers
from finsight_lite.clf_metrics import band_scores
pairs = json.loads(sys.argv[2])
out = [unmatched_numbers(a, b) for a, b in pairs]
assert band_scores([4, 1], [4, 2])["severe_recall"] == 1.0
assert not [m for m in sys.modules if m == "finsight" or m.startswith("finsight.")]
print(json.dumps(out))
"""


def test_lite_copy_matches_the_product_and_is_self_contained(tmp_path: Path) -> None:
    build_lite(ROOT / "src" / "finsight", tmp_path)
    run = subprocess.run(
        [sys.executable, "-I", "-c", _CHILD, str(tmp_path), json.dumps(PAIRS)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == [unmatched_numbers(a, b) for a, b in PAIRS]


@pytest.mark.parametrize("name", ["core/schemas.py", "normalize/numerals.py", "numcheck.py"])
def test_no_product_imports_remain(tmp_path: Path, name: str) -> None:
    build_lite(ROOT / "src" / "finsight", tmp_path)
    text = (tmp_path / "finsight_lite" / name).read_text(encoding="utf-8")
    assert "from finsight." not in text
    assert "import finsight." not in text
