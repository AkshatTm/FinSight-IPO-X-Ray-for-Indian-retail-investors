"""Data for the MuRIL advice classifier (P5.4): the E8 set split 70/15/15, packaged for Kaggle.

    uv run python -m finsight.guard.clf_data --username <kaggle-username>

Each question is one row of ``data/gold/advice_guard_set.csv``. The split is by question
(a question never appears in two parts; repeated wordings count as one) and stratified by
language and label, with a fixed seed, so every run and every reader gets the same parts.
Writes ``data/processed/kaggle/finsight-advice/{train,val,test}.csv`` (git-ignored) and the
dataset metadata. The set was drafted by Claude chat and not yet reviewed by Akshat (ADR-046).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from finsight.core.config import get_settings
from finsight.guard import normalize_question

DATASET_NAME = "finsight-advice"
SPLIT_SEED = 2026
FRACTIONS = (0.70, 0.15, 0.15)
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9-]{2,}$")


def load_questions(csv_path: Path) -> list[dict[str, str]]:
    """``{question, language, label}`` with label ``advice`` or ``fact``; duplicates dropped."""
    rows, seen = [], set()
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            key = normalize_question(r["question"])
            if key in seen:
                continue
            seen.add(key)
            label = "advice" if r["is_advice (must block?)"].strip().lower() == "yes" else "fact"
            rows.append(
                {"question": r["question"].strip(), "language": r["language"], "label": label}
            )
    return rows


def split_questions(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Stratified by (language, label): 70 % train, 15 % val, 15 % test of every stratum."""
    rng = random.Random(SPLIT_SEED)
    strata: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        strata[(r["language"], r["label"])].append(r)
    parts: dict[str, list[dict[str, str]]] = {"train": [], "val": [], "test": []}
    for key in sorted(strata):
        group = sorted(strata[key], key=lambda r: r["question"])
        rng.shuffle(group)
        n_val = max(1, round(len(group) * FRACTIONS[1]))
        n_test = max(1, round(len(group) * FRACTIONS[2]))
        parts["val"] += group[:n_val]
        parts["test"] += group[n_val : n_val + n_test]
        parts["train"] += group[n_val + n_test :]
    return parts


def write_dataset(csv_path: Path, out: Path, username: str) -> dict[str, int]:
    """Split the guard questions and write the Kaggle dataset folder."""
    if not _USERNAME.match(username):
        raise ValueError(f"username {username!r} is not a Kaggle username (lowercase, digits, -)")
    parts = split_questions(load_questions(csv_path))
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in parts.items():
        with (out / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["question", "language", "label"], lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    meta = {
        "title": DATASET_NAME,
        "id": f"{username}/{DATASET_NAME}",
        "licenses": [{"name": "CC-BY-NC-SA-4.0"}],
    }
    (out / "dataset-metadata.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    return {k: len(v) for k, v in parts.items()}


def main(argv: list[str] | None = None) -> int:
    """CLI: build the private Kaggle dataset for the guard classifier."""
    parser = argparse.ArgumentParser(prog="finsight.guard.clf_data")
    parser.add_argument("--username", required=True)
    args = parser.parse_args(argv)
    paths = get_settings().paths
    counts = write_dataset(
        paths.gold_dir / "advice_guard_set.csv",
        paths.processed_dir / "kaggle" / DATASET_NAME,
        args.username,
    )
    print(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
