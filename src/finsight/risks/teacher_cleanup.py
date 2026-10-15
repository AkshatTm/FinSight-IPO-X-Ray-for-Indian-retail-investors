"""Clean the kept teacher outputs before student / classifier training (C2.3b).

    uv run python -m finsight.risks.teacher_cleanup run

Reads ``simplify.jsonl``, ``labels.jsonl`` and ``risks.jsonl`` in ``data/processed/teacher/`` and
writes ``simplify.clean.jsonl`` and ``labels.clean.jsonl`` beside them, plus
``eval_results/c/teacher_cleanup_report.json``:

1. strict number checks (``strict_numbers``): rows failing ``unit_dropped`` / ``sign_flip`` leave
   the student pairs (their category and seriousness labels stay for the classifier); rows with
   ``inclusion_polarity`` are only flagged;
2. deterministic category remap (``configs/category_remap.yaml``) on the labels; a rule can
   match only the subject of the title (before "... may adversely affect ...") and can name
   exclusions;
3. non-risk titles (page headings captured as a risk title) are counted and listed;
4. ``seriousness_band``: 1, 2, 3 and 4 = severe (levels 4 and 5 merged, level 5 is too rare).
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from finsight.risks.strict_numbers import FLAG_REASONS, strict_check
from finsight.risks.teacher_run import read_jsonl

REMAP_CONFIG = Path("configs/category_remap.yaml")
DEFAULT_DIR = Path("data/processed/teacher")
REPORT_PATH = Path("eval_results/c/teacher_cleanup_report.json")
BODY_CHARS = 200
EXAMPLES = 10

_HEADING = re.compile(
    r"^(currency of (financial )?presentation|presentation of financial|financial (year|data)|"
    r"fiscal (year|\d)|(industry|market) (and market )?data|forward[- ]looking|certain conventions|"
    r"definitions|use of market|summary of|table of contents|general information|"
    r"notice to (prospective )?investors)",
    re.I,
)
# Where a title's consequence clause starts: "... may adversely affect our business, reputation",
# ", which could ...", "... resulting in ...", or the second sentence. A ``subject_only`` rule
# ignores what follows. A conditional title ("If X, our reputation ...") ends its subject at the
# first comma.
_CONSEQUENCE = re.compile(
    r",?\s*\b(?:which|this|that)\s+(?:in turn\s+)?(?:may|could|might|would|will|can)\b"
    r"|\b(?:may|could|might|would|will|can)\s+(?:\w+\s+){0,3}?"
    r"(?:adversely|materially|negatively|significantly|adverse|affect|impact|harm|hurt|damage|"
    r"lead|result|cause|expose)\w*"
    r"|\b(?:affecting|impacting|harming|resulting in|leading to)\b"
    r"|,?\s*\b(?:have|has|had|having)\b,?\s+(?:\w+\s+){0,3}?(?:an?\s+)?(?:material\s+)?adverse"
    r"|\.\s+(?=[A-Z])",
    re.I,
)
_CONDITIONAL = re.compile(r"^(?:if|in (?:the )?(?:event|case)|should|unless|where)\b[^,]*,", re.I)
# "Our business, reputation ... could be impacted by X": the subject is the cause after "by".
_PASSIVE_EFFECT = re.compile(
    r"^(?:our|the company.s|its)\s+(?:business|operations|results|financial|growth|profitab)", re.I
)
_PASSIVE_CAUSE = re.compile(r"\b(?:by|due to|because of|as a result of|from)\b", re.I)
MIN_SUBJECT_WORDS = 4  # a shorter subject ("We could be adversely affected by ...") says nothing
_RISK_WORDS = re.compile(
    r"\b(may|might|could|can|will|would|are|is|was|were|have|has|had|not|any|our|we|us|no|"
    r"depend\w*|subject|risk|adverse\w*|affect\w*|fail\w*|unable|inability)\b",
    re.I,
)


def _any(patterns: list[str]) -> re.Pattern[str] | None:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I) if patterns else None


def remap_version(path: Path = REMAP_CONFIG) -> str:
    """The ``version`` of the remap config (written into the report)."""
    return str(yaml.safe_load(path.read_text(encoding="utf-8"))["version"])


def load_rules(path: Path = REMAP_CONFIG) -> list[dict[str, Any]]:
    """Remap rules with their patterns (and optional exclusions) compiled."""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = []
    for rule in cfg["rules"]:
        rules.append(
            {
                "name": rule["name"],
                "target": rule["target"],
                "regex": _any(rule["patterns"]),
                "exclude": _any(rule.get("exclude", [])),
                "subject_only": bool(rule.get("subject_only", False)),
            }
        )
    return rules


def subject_of(title: str) -> str:
    """The title up to its consequence clause ("X may adversely affect our reputation" -> "X").

    A conditional title keeps its condition ("If X, our reputation ..." -> "If X,"); a passive
    title about the business keeps its cause ("Our business and reputation could be impacted by
    X" -> "by X"); a subject shorter than ``MIN_SUBJECT_WORDS`` words falls back to the whole
    title.
    """
    cond = _CONDITIONAL.match(title)
    if cond:
        return cond.group(0)
    m = _CONSEQUENCE.search(title)
    if m and _PASSIVE_EFFECT.match(title):
        cause = _PASSIVE_CAUSE.search(title, m.end())
        return title[cause.start() :] if cause else ""
    subject = title[: m.start()] if m else title
    return subject if len(subject.split()) >= MIN_SUBJECT_WORDS else title


def remap_category(
    title: str, body: str, category: str, rules: list[dict[str, Any]]
) -> tuple[str, str | None]:
    """(new category, rule name or None). The first rule matching the title wins (the start of
    the body stands in when there is no title)."""
    text = title or body[:BODY_CHARS]
    for rule in rules:
        if rule["exclude"] is not None and rule["exclude"].search(text):
            continue
        if rule["regex"].search(subject_of(text) if rule["subject_only"] else text):
            return rule["target"], rule["name"]
    return category, None


def is_nonrisk_title(title: str) -> bool:
    """True for a page heading captured as the title: known heading or a short title with no risk
    wording ("Currency of Presentation")."""
    t = title.strip()
    if not t:
        return False
    if _HEADING.match(t):
        return True
    return len(t.split()) <= 6 and not _RISK_WORDS.search(t)


def seriousness_band(level: int) -> int:
    """1, 2, 3 as given; 4 and 5 merge into band 4 (severe)."""
    return min(level, 4)


def _split_original(original: str) -> tuple[str, str]:
    if original.startswith("Title: "):
        title, _, body = original.partition("\n\n")
        return title.removeprefix("Title: ").strip(), body
    return "", original


def clean(
    teacher_dir: Path = DEFAULT_DIR,
    rules_path: Path = REMAP_CONFIG,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Run all cleaning steps and write the ``*.clean.jsonl`` files; returns the report."""
    rules = load_rules(rules_path)
    pairs = list(read_jsonl(teacher_dir / "simplify.jsonl"))
    labels = list(read_jsonl(teacher_dir / "labels.jsonl"))
    titles = {
        str(r["risk_id"]): str(r.get("title") or "")
        for r in read_jsonl(teacher_dir / "risks.jsonl")
    }
    bodies = {str(p["risk_id"]): _split_original(str(p["original"]))[1] for p in pairs}

    dropped: dict[str, list[dict[str, str]]] = {}
    flagged: list[dict[str, str]] = []
    drop_ids: set[str] = set()
    kept_pairs = []
    for p in pairs:
        findings = strict_check(str(p["original"]), str(p["simple"]))
        hard = [f for f in findings if f.drops]
        for f in findings:
            row = {"risk_id": p["risk_id"], "detail": f.detail}
            (flagged if f.reason in FLAG_REASONS else dropped.setdefault(f.reason, [])).append(row)
        if hard:
            drop_ids.add(str(p["risk_id"]))
        else:
            kept_pairs.append(p)

    changed: Counter[str] = Counter()
    moves: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    nonrisk: list[dict[str, str]] = []
    band: Counter[int] = Counter()
    out_labels = []
    for lab in labels:
        rid = str(lab["risk_id"])
        title = titles.get(rid, "")
        new, rule = remap_category(title, bodies.get(rid, ""), str(lab["category"]), rules)
        if rule and new != lab["category"]:
            changed[rule] += 1
            moves[f"{lab['category']} -> {new}"] += 1
            samples.setdefault(rule, [])
            if len(samples[rule]) < 5:
                samples[rule].append(f"[{lab['category']} -> {new}] {title[:110]}")
        if is_nonrisk_title(title):
            nonrisk.append({"risk_id": rid, "title": title[:100]})
        b = seriousness_band(int(lab["seriousness_1to5"]))
        band[b] += 1
        out_labels.append(
            {**lab, "category_teacher": lab["category"], "category": new, "seriousness_band": b}
        )

    _write(teacher_dir / "simplify.clean.jsonl", kept_pairs)
    _write(teacher_dir / "labels.clean.jsonl", out_labels)
    n_pairs = len(pairs)
    report = {
        "remap_version": remap_version(rules_path),
        "pairs_in": n_pairs,
        "pairs_kept": len(kept_pairs),
        "strict_dropped": {r: len(v) for r, v in dropped.items()},
        "strict_dropped_rows": len(drop_ids),
        "strict_flagged": len(flagged),
        "strict_examples": {
            r: v[:EXAMPLES] for r, v in {**dropped, "inclusion_polarity": flagged}.items()
        },
        "labels": len(labels),
        "category_changed_by_rule": dict(changed),
        "category_changed_total": sum(changed.values()),
        "category_moves": dict(moves.most_common()),
        "category_samples": samples,
        "category_counts_after": dict(
            Counter(str(r["category"]) for r in out_labels).most_common()
        ),
        "seriousness_band_counts": {str(k): v for k, v in sorted(band.items())},
        "seriousness_level_counts": dict(
            sorted(Counter(int(r["seriousness_1to5"]) for r in labels).items())
        ),
        "nonrisk_titles": len(nonrisk),
        "nonrisk_title_examples": nonrisk[:15],
    }
    out = report_path or REPORT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write JSONL (LF); a file with the same rows is left alone, even with CRLF endings from an
    older run, because a training job may be reading it."""
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
    if path.exists() and path.read_bytes().replace(b"\r\n", b"\n") == data:
        return
    path.write_bytes(data)


def main(argv: list[str] | None = None) -> None:
    """CLI: ``run`` the clean-up on ``data/processed/teacher``."""
    p = argparse.ArgumentParser(prog="python -m finsight.risks.teacher_cleanup")
    p.add_argument("command", choices=["run"])
    p.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    p.add_argument("--report", type=Path, default=REPORT_PATH)
    args = p.parse_args(argv)
    r = clean(args.dir, report_path=args.report)
    print(
        f"pairs {r['pairs_in']} -> {r['pairs_kept']} (strict dropped {r['strict_dropped']}, "
        f"flagged {r['strict_flagged']}); categories changed {r['category_changed_total']} "
        f"{r['category_changed_by_rule']}; non-risk titles {r['nonrisk_titles']}; "
        f"bands {r['seriousness_band_counts']}"
    )


if __name__ == "__main__":
    main()
