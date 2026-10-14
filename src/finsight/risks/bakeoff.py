"""Teacher bake-off: sample, blind rating sheet, scoring, recorded pick rule (C2.2, C-ADR-05).

Candidate teachers (C-ADR-05: Qwen3.8-27B-FP8, Gemma-4-31B-it bf16, Qwen3-32B-AWQ baseline) answer
the same 300 risks with the same prompt on the same GPU (G4). The filters run on every output.
Akshat rates a **blind, shuffled** sheet of 50 risks x every teacher (150 rows for three; no model
column; the key is kept in a separate file). The pick rule is fixed before any rating exists:

1. highest share of ``faithful == yes`` among the rated outputs; every model within ``TIE`` (0.05)
   of the best share is tied with it;
2. among tied models, the lowest *critical* drop rate on all 300 risks: ``number_mismatch`` plus
   ``certainty_changed`` (the overall drop rate is reported, not used);
3. if still tied, the faster run (generation seconds on the same 300 risks and GPU).

Everything is computed from files by this code; nothing is typed in by hand. The C2.2 ratings were
made by a blind AI rater (Claude, separate session, never saw the key) and accepted by Akshat
(``rater: ai_blind`` in the result file); the teacher outputs
carry their own ``teacher:<model>:<prompt>`` label source.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from finsight.risks.filters import Kept
from finsight.risks.teacher_input import Candidate

SAMPLE_SEED = 2026
SHEET_SEED = 4242
TIE = 0.05  # shares of "faithful: yes" within this of the best count as a tie
CRITICAL_REASONS = ("number_mismatch", "certainty_changed")  # tie-break drop reasons
SHEET_COLUMNS = (
    "sheet_id", "original", "simple", "category", "seriousness_1to5", "hard_fact",
    "faithful", "category_correct", "notes",
)  # fmt: skip
RULE = (
    "highest faithful=yes share among rated outputs; models within 0.05 of the best are tied; "
    "among tied, lowest number_mismatch + certainty_changed drop rate on the 300 risks; "
    "if still tied, the faster run"
)


def sample_risks(
    candidates: Iterable[Candidate], n: int = 300, seed: int = SAMPLE_SEED
) -> list[Candidate]:
    """``n`` risks spread over years and companies: round-robin over (year) then company.

    Callers pass only train and dev risks (never test or bench).
    """
    rng = random.Random(seed)
    by_year: dict[int, dict[str, list[Candidate]]] = defaultdict(lambda: defaultdict(list))
    for c in sorted(candidates, key=lambda c: c.risk_id):
        by_year[c.year][c.company].append(c)
    for companies in by_year.values():
        for items in companies.values():
            rng.shuffle(items)
    pools = {y: sorted(cs.items()) for y, cs in sorted(by_year.items())}
    for items in pools.values():
        rng.shuffle(items)
    picked: list[Candidate] = []
    while len(picked) < n and any(pools.values()):
        for y in list(pools):
            if len(picked) >= n:
                break
            if not pools[y]:
                continue
            company, items = pools[y].pop(0)
            picked.append(items.pop())
            if items:
                pools[y].append((company, items))
    return picked


def build_sheet(
    kept: dict[str, list[Kept]],
    *,
    n_risks: int = 50,
    seed: int = SHEET_SEED,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Blind sheet rows and the secret key.

    Args:
        kept: ``model -> kept outputs`` (each model's filter report). Only risks kept by every
            model are eligible, so the comparison is paired.
        n_risks: Risks to rate (the sheet has ``n_risks`` x number of models rows).
        seed: Shuffle seed.

    Returns:
        ``(rows, key)`` where ``key[sheet_id] = {"model": ..., "risk_id": ...}``.
    """
    models = sorted(kept)
    by_model = {m: {k.risk_id: k for k in kept[m]} for m in models}
    common = sorted(set.intersection(*(set(d) for d in by_model.values())))
    rng = random.Random(seed)
    chosen = rng.sample(common, min(n_risks, len(common)))
    entries = [(rid, m) for rid in chosen for m in models]
    rng.shuffle(entries)
    rows: list[dict[str, Any]] = []
    key: dict[str, dict[str, str]] = {}
    for i, (rid, m) in enumerate(entries, start=1):
        k = by_model[m][rid]
        sid = f"s{i:03d}"
        rows.append(
            {
                "sheet_id": sid, "original": k.original, "simple": k.output.simple,
                "category": k.output.category, "seriousness_1to5": k.output.seriousness_1to5,
                "hard_fact": k.output.hard_fact, "faithful": "", "category_correct": "",
                "notes": "",
            }
        )  # fmt: skip
        key[sid] = {"model": m, "risk_id": rid}
    return rows, key


def write_sheet(rows: list[dict[str, Any]], path: Path) -> None:
    """The blind sheet as CSV (UTF-8 with BOM so Excel reads it)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def read_sheet(path: Path) -> list[dict[str, str]]:
    """A (rated) sheet back from CSV."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % Wilson interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(centre - half, 4), round(centre + half, 4))


def score(
    rated: list[dict[str, str]],
    key: dict[str, dict[str, str]],
    reports: dict[str, dict[str, Any]],
    seconds: dict[str, float],
) -> dict[str, Any]:
    """Per-model scores and the pick.

    Args:
        rated: Sheet rows with ``faithful`` (yes/partly/no) and ``category_correct`` (yes/no).
        key: The secret key from ``build_sheet``.
        reports: ``model -> FilterReport.summary()`` on all 300 risks.
        seconds: ``model -> generation seconds``.

    Raises:
        ValueError: when a row is unrated or has an unknown value.
    """
    per: dict[str, dict[str, Any]] = {
        m: {"faithful": defaultdict(int), "cat": defaultdict(int)} for m in reports
    }
    for row in rated:
        f, c = row["faithful"].strip().lower(), row["category_correct"].strip().lower()
        if f not in {"yes", "partly", "no"} or c not in {"yes", "no"}:
            raise ValueError(
                f"{row['sheet_id']}: unrated or invalid (faithful={f!r}, category_correct={c!r})"
            )
        model = key[row["sheet_id"]]["model"]
        per[model]["faithful"][f] += 1
        per[model]["cat"][c] += 1
    out: dict[str, Any] = {"rule": RULE, "tie": TIE, "models": {}}
    for m, rep in reports.items():
        n = sum(per[m]["faithful"].values())
        yes = per[m]["faithful"]["yes"]
        catyes = per[m]["cat"]["yes"]
        out["models"][m] = {
            "rated": n,
            "faithful": dict(per[m]["faithful"]),
            "faithful_yes_share": round(yes / n, 4) if n else None,
            "faithful_yes_ci95": wilson(yes, n),
            "category_correct_share": round(catyes / n, 4) if n else None,
            "drop_rate_total": round(1 - rep["kept"] / rep["total"], 4) if rep["total"] else None,
            "drop_rate_critical": critical_drop_rate(rep),
            "kept": rep["kept"],
            "total": rep["total"],
            "seconds": seconds.get(m),
        }
    out["pick"] = pick(out["models"])
    return out


def critical_drop_rate(report: dict[str, Any]) -> float | None:
    """Share of the risks dropped for ``number_mismatch`` or ``certainty_changed``."""
    total = report.get("total") or 0
    if not total:
        return None
    dropped = report.get("dropped") or {}
    return round(sum(dropped.get(r, 0) for r in CRITICAL_REASONS) / total, 4)


def pick(models: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Apply the recorded rule (C-ADR-05) to the per-model scores (any number of models)."""
    names = sorted(models)
    if len(names) == 1:
        return {"model": names[0], "because": "only one model", "tied": names}
    share = {m: models[m]["faithful_yes_share"] or 0.0 for m in names}
    best = max(share.values())
    tied = [m for m in names if best - share[m] <= TIE + 1e-9]
    if len(tied) == 1:
        runner_up = max(v for m, v in share.items() if m != tied[0])
        because = f"faithful=yes share higher by {best - runner_up:.3f} (> {TIE})"
        return {"model": tied[0], "tied": tied, "because": because}

    def crit(m: str) -> float:
        d = models[m].get("drop_rate_critical")
        return float("inf") if d is None else d

    low = min(crit(m) for m in tied)
    tied2 = [m for m in tied if crit(m) == low]
    if len(tied2) == 1:
        because = "faithful=yes tie; lowest number_mismatch + certainty_changed drop rate"
        return {"model": tied2[0], "tied": tied, "because": because}

    def secs(m: str) -> float:
        s = models[m].get("seconds")
        return float("inf") if s is None else s

    fastest = min(tied2, key=lambda m: (secs(m), m))
    if sum(secs(m) == secs(fastest) for m in tied2) == 1:
        because = "tie on quality and critical drops; faster"
        return {"model": fastest, "tied": tied, "because": because}
    return {"model": fastest, "tied": tied, "because": "complete tie; first by name"}


def write_result(result: dict[str, Any], path: Path) -> None:
    """``eval_results/c/teacher_bakeoff.json`` (LF endings)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
