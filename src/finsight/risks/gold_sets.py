"""Gold sets on test IPOs: category gold-150 (C2.4, E16) and simplification gold-50 (C2.5, E18).

Both are drawn from ``test``-slice IPOs only (C-ADR-02: they evaluate, never train or tune), with
disjoint IPOs and a fixed seed (B04: gold-150 = 15 risks x 10 IPOs, gold-50 = 5 risks x 10 IPOs).

- **gold-150:** a verification sheet with the category pre-filled by a model (by default the
  bake-off runner-up, so the pre-fill is not the classifier's own teacher); the pre-fill and its
  source stay in a separate key so the number of changed labels can be reported.
- **gold-50:** a blind, shuffled rating sheet of rewrites from several systems (zero-shot base,
  student, teacher); the system of each row is in a separate key.

Everything here is pure and tested; ``scripts/gold_sets.py`` does the file work.
"""

from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from finsight.risks.bakeoff import wilson
from finsight.risks.teacher_data import original_text
from finsight.risks.teacher_input import Candidate

SEED = 2027
GOLD150 = (10, 15)  # (IPOs, risks per IPO)
GOLD50 = (10, 5)
MIN_WORDS, MAX_WORDS = 40, 600
CATEGORY_COLUMNS = ("risk_id", "company", "title", "text", "category", "notes")
REWRITE_COLUMNS = ("sheet_id", "original", "rewrite", "faithful", "plain_english_1to5", "notes")


def pick(
    by_ipo: Mapping[str, list[Candidate]],
    n_ipos: int,
    per_ipo: int,
    *,
    seed: int = SEED,
    exclude_ipos: Iterable[str] = (),
) -> list[Candidate]:
    """``per_ipo`` risks from each of ``n_ipos`` IPOs (only IPOs with enough eligible risks)."""
    rng = random.Random(seed)
    skip = set(exclude_ipos)
    ok = {
        ipo: sorted((c for c in cs if MIN_WORDS <= c.words <= MAX_WORDS), key=lambda c: c.risk_id)
        for ipo, cs in by_ipo.items()
        if ipo not in skip
    }
    eligible = sorted(ipo for ipo, cs in ok.items() if len(cs) >= per_ipo)
    if len(eligible) < n_ipos:
        raise ValueError(f"only {len(eligible)} IPOs have {per_ipo} eligible risks")
    chosen: list[Candidate] = []
    for ipo in sorted(rng.sample(eligible, n_ipos)):
        chosen += sorted(rng.sample(ok[ipo], per_ipo), key=lambda c: c.risk_id)
    return chosen


# ----------------------------------------------------------------------------- gold-150
def category_sheet(risks: list[Candidate], prefill: Mapping[str, str]) -> list[dict[str, str]]:
    """Verification rows: ``category`` pre-filled (blank when the model gave none)."""
    return [
        {"risk_id": c.risk_id, "company": c.company, "title": c.title, "text": c.body,
         "category": prefill.get(c.risk_id, ""), "notes": ""}
        for c in risks
    ]  # fmt: skip


def category_gold(
    rated: list[dict[str, str]],
    prefill: Mapping[str, str],
    categories: Iterable[str],
    bands: Mapping[str, int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verified rows for ``classify --gold`` and the change count against the pre-fill.

    The text has the layout the teacher and the classifier's training rows use
    (``teacher_data.original_text``). ``bands`` (the teacher's seriousness band per risk) is
    added as ``band`` when given: gold-150 has no human seriousness label.

    Raises:
        ValueError: when a row has no category or one outside the list.
    """
    allowed = set(categories)
    rows, changed = [], 0
    for r in rated:
        cat = r["category"].strip()
        if cat not in allowed:
            raise ValueError(f"{r['risk_id']}: category {cat!r} is not one of the {len(allowed)}")
        changed += cat != prefill.get(r["risk_id"], "")
        row: dict[str, Any] = {
            "risk_id": r["risk_id"], "company": r["company"],
            "text": original_text({"title": r["title"], "body": r["text"]}), "label": cat,
        }  # fmt: skip
        if bands is not None:
            row["band"] = bands.get(r["risk_id"])
        rows.append(row)
    n = len(rows)
    return rows, {"n": n, "changed_from_prefill": changed,
                  "changed_share": round(changed / n, 4) if n else None}  # fmt: skip


def agreement(
    gold: Mapping[str, str], pred: Mapping[str, str], categories: Iterable[str]
) -> dict[str, Any]:
    """How often a model's category equals the gold one: overall and per gold category (the
    share of that category's gold rows the model got), plus the rows it missed per category."""
    ids = [i for i in gold if i in pred]
    per: dict[str, dict[str, Any]] = {}
    for cat in categories:
        rows = [i for i in ids if gold[i] == cat]
        if not rows:
            continue
        hit = sum(pred[i] == cat for i in rows)
        wrong = Counter(pred[i] for i in rows if pred[i] != cat)
        per[cat] = {"n": len(rows), "agree": hit, "share": round(hit / len(rows), 4),
                    "model_said": dict(wrong.most_common())}  # fmt: skip
    hit = sum(gold[i] == pred[i] for i in ids)
    return {"n": len(ids), "missing": len(gold) - len(ids), "agree": hit,
            "share": round(hit / len(ids), 4) if ids else None,
            "ci95": wilson(hit, len(ids)) if ids else None, "per_category": per}  # fmt: skip


# ----------------------------------------------------------------------------- gold-50
def rewrite_sheet(
    risks: list[Candidate],
    outputs: Mapping[str, Mapping[str, Mapping[str, str]]],
    *,
    seed: int = SEED,
) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    """Blind shuffled rows (risk x system) and the key ``sheet_id -> {system, risk_id, check}``.

    ``outputs[system][risk_id] = {"text": cleaned output, "check": post-check failure or ""}``.
    Every output is rated, also one the post-checks would reject, so a system's rejections do not
    shrink the comparison; the check result stays in the key and is reported separately. A risk
    is used only when every system gave some text for it.
    """
    systems = sorted(outputs)
    usable = [
        c for c in risks
        if all(outputs[s].get(c.risk_id, {}).get("text", "").strip() for s in systems)
    ]  # fmt: skip
    entries = [(c, s) for c in usable for s in systems]
    rng = random.Random(seed)
    rng.shuffle(entries)
    rows, key = [], {}
    for i, (c, s) in enumerate(entries, start=1):
        sid = f"g{i:03d}"
        out = outputs[s][c.risk_id]
        original = f"{c.title}\n\n{c.body}".strip()
        rows.append({"sheet_id": sid, "original": original, "rewrite": out["text"],
                     "faithful": "", "plain_english_1to5": "", "notes": ""})  # fmt: skip
        key[sid] = {"system": s, "risk_id": c.risk_id, "check": out.get("check", "")}
    return rows, key


def score_rewrites(
    rated: list[dict[str, str]], key: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    """Per system: faithful yes/partly/no with the yes share (95 % Wilson), mean plainness, and
    the share that passed the post-checks (only those would be shown in the product).

    Raises:
        ValueError: when a row is unrated or has an unknown value.
    """
    faith: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    plain: dict[str, list[int]] = defaultdict(list)
    checks: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rated:
        f = r["faithful"].strip().lower()
        p = r["plain_english_1to5"].strip()
        if f not in {"yes", "partly", "no"} or p not in {"1", "2", "3", "4", "5"}:
            raise ValueError(f"{r['sheet_id']}: unrated or invalid (faithful={f!r}, plain={p!r})")
        k = key[r["sheet_id"]]
        s = k["system"]
        faith[s][f] += 1
        plain[s].append(int(p))
        checks[s][k.get("check") or "passed"] += 1
    out: dict[str, Any] = {}
    for s in sorted(faith):
        n, yes = sum(faith[s].values()), faith[s].get("yes", 0)
        out[s] = {"rated": n, "faithful": dict(faith[s]), "faithful_yes_share": round(yes / n, 4),
                  "faithful_yes_ci95": wilson(yes, n),
                  "plain_english_mean": round(sum(plain[s]) / len(plain[s]), 2),
                  "post_checks": dict(checks[s]),
                  "passed_checks_share": round(checks[s].get("passed", 0) / n, 4)}  # fmt: skip
    return out


# ----------------------------------------------------------------------------- csv helpers
def write_csv(rows: list[dict[str, str]], columns: Iterable[str], path: Path) -> None:
    """UTF-8 with BOM (Excel), LF line ends."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Rows of a (rated) sheet."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))
