"""A self-contained copy of the product's number normaliser for ARGON's notebooks.

ARGON must not import the product package, but M1's number-keeping filter and the classifier
metrics must use the product's exact rules. ``build_lite`` copies the pure modules into a package
named ``finsight_lite`` (imports rewritten) plus ``numcheck.py``, a stand-alone copy of
``risks.checks.unmatched_numbers``. A parity test runs both on the same inputs.
"""

from __future__ import annotations

import shutil
from pathlib import Path

PACKAGE = "finsight_lite"

# (source relative to src/finsight, target relative to finsight_lite)
COPIES: tuple[tuple[str, str], ...] = (
    ("core/schemas.py", "core/schemas.py"),
    ("normalize/__init__.py", "normalize/__init__.py"),
    ("normalize/equality.py", "normalize/equality.py"),
    ("normalize/numerals.py", "normalize/numerals.py"),
    ("normalize/periods.py", "normalize/periods.py"),
    ("risks/clf_metrics.py", "clf_metrics.py"),
    ("risks/strict_numbers.py", "strict_numbers.py"),
)

NUMCHECK = '''"""Numbers in a rewrite or answer that are not in its source (copy of risks.checks).
"""

from __future__ import annotations

import re

from finsight_lite.core.schemas import Amount, Count, Money
from finsight_lite.normalize import equal, parse_amounts

_BARE_NUMBER = re.compile(r"(?<![\\w.])\\d[\\d,]*(?:\\.\\d+)?(?![\\w])")


def _as_money(amount: Amount) -> Money | None:
    if isinstance(amount, Money):
        return amount if amount.value_inr is not None else None
    if isinstance(amount, Count):
        spans = parse_amounts(f"\\u20b9 {amount.raw}")
        if spans and isinstance(spans[0].amount, Money) and spans[0].amount.value_inr is not None:
            return spans[0].amount
    return None


def same_value(a: Amount, b: Amount) -> bool:
    """Equal within the printed precision."""
    if a.kind != b.kind:
        return False
    if isinstance(a, Count) and isinstance(b, Count):
        ma, mb = _as_money(a), _as_money(b)
        return a.value == b.value or (ma is not None and mb is not None and equal(ma, mb))
    return equal(a, b)


def _bare_numbers(text: str, spans: list[tuple[int, int]]) -> set[str]:
    out = set()
    for m in _BARE_NUMBER.finditer(text):
        if any(s <= m.start() < e for s, e in spans):
            continue
        out.add(m.group(0).replace(",", "").rstrip("."))
    return out


def unmatched_numbers(original: str, rewrite: str) -> list[str]:
    """Numbers in ``rewrite`` that are not in ``original`` (empty = every number is copied)."""
    src_spans = parse_amounts(original)
    out_spans = parse_amounts(rewrite)
    missing = [
        s.amount.raw
        for s in out_spans
        if not any(
            s.amount.kind == o.amount.kind and same_value(s.amount, o.amount) for o in src_spans
        )
    ]
    src_plain = _bare_numbers(original, [(s.start, s.end) for s in src_spans])
    src_plain |= {re.sub(r"[^\\d.]", "", s.amount.raw) for s in src_spans}
    for number in _bare_numbers(rewrite, [(s.start, s.end) for s in out_spans]):
        if number not in src_plain:
            missing.append(number)
    return missing
'''


def build_lite(src_root: Path, out_dir: Path) -> list[str]:
    """Write ``out_dir/finsight_lite`` from ``src_root`` (= ``src/finsight``); return its files."""
    pkg = out_dir / PACKAGE
    if pkg.exists():
        shutil.rmtree(pkg)
    written: list[str] = []
    for rel_src, rel_dst in COPIES:
        text = (src_root / rel_src).read_text(encoding="utf-8")
        text = text.replace("from finsight.", f"from {PACKAGE}.").replace(
            "import finsight.", f"import {PACKAGE}."
        )
        dst = pkg / rel_dst
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8", newline="\n")
        written.append(rel_dst)
    (pkg / "__init__.py").write_text(
        '"""Stand-alone copy of the FinSight normaliser (handoff.vendor)."""\n',
        encoding="utf-8",
        newline="\n",
    )
    core_init = pkg / "core" / "__init__.py"
    core_init.write_text('"""Schemas."""\n', encoding="utf-8", newline="\n")
    (pkg / "numcheck.py").write_text(NUMCHECK, encoding="utf-8", newline="\n")
    return [*written, "__init__.py", "core/__init__.py", "numcheck.py"]
