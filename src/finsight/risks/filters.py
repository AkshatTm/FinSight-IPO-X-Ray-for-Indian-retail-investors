"""Deterministic filters for teacher outputs (B03 §3.3), each drop logged with its reason.

Order (the first failing check names the drop): invalid JSON → category not in the list →
schema → a number not in the original → forbidden phrase → longer than 70 words → certainty
changed → duplicate of an earlier rewrite.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from finsight.guard import find_forbidden
from finsight.risks.certainty import certainty_changed
from finsight.risks.checks import unmatched_numbers, word_count
from finsight.risks.teacher import ParseError, TeacherOutput, parse_output

MAX_WORDS = 70
REASONS = (
    "invalid_json",
    "bad_category",
    "bad_schema",
    "number_mismatch",
    "forbidden_phrase",
    "too_long",
    "certainty_changed",
    "duplicate",
)


@dataclass(frozen=True)
class TeacherItem:
    """A risk as sent to the teacher and the teacher's raw reply."""

    risk_id: str
    original: str  # title + body as sent to the teacher
    raw: str  # the teacher's text


@dataclass(frozen=True)
class Kept:
    """A teacher reply that passed every filter."""

    risk_id: str
    original: str
    output: TeacherOutput


@dataclass
class FilterReport:
    """Replies kept and dropped, with the reason for each drop."""

    kept: list[Kept] = field(default_factory=list)
    dropped: list[tuple[str, str, str]] = field(default_factory=list)  # (risk_id, reason, detail)

    @property
    def counts(self) -> dict[str, int]:
        """Drops per filter reason (every reason listed, zero included)."""
        c = Counter(reason for _, reason, _ in self.dropped)
        return {r: c.get(r, 0) for r in REASONS}

    def summary(self) -> dict[str, object]:
        """Totals and drop rates per reason, for the datasheet."""
        total = len(self.kept) + len(self.dropped)
        return {
            "total": total,
            "kept": len(self.kept),
            "dropped": self.counts,
            "drop_rate": {r: (n / total if total else 0.0) for r, n in self.counts.items()},
        }


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def check_one(item: TeacherItem) -> tuple[TeacherOutput | None, str | None, str]:
    """(output, None, "") when kept, else (output-or-None, reason, detail)."""
    try:
        out = parse_output(item.raw)
    except ParseError as err:
        return None, err.reason, ""
    missing = unmatched_numbers(item.original, out.simple)
    if missing:
        return out, "number_mismatch", ", ".join(missing)
    hits = find_forbidden(out.simple)
    if hits:
        return out, "forbidden_phrase", hits[0].id
    if word_count(out.simple) > MAX_WORDS:
        return out, "too_long", str(word_count(out.simple))
    changed = certainty_changed(item.original, out.simple)
    if changed:
        return out, "certainty_changed", changed
    return out, None, ""


def filter_outputs(items: list[TeacherItem]) -> FilterReport:
    """Run every filter on each reply and drop duplicate rewrites."""
    report = FilterReport()
    seen: set[str] = set()
    for item in items:
        out, reason, detail = check_one(item)
        if reason is None and out is not None:
            key = _key(out.simple)
            if key in seen:
                reason, detail = "duplicate", ""
            else:
                seen.add(key)
                report.kept.append(Kept(item.risk_id, item.original, out))
                continue
        report.dropped.append((item.risk_id, reason or "invalid_json", detail))
    return report
