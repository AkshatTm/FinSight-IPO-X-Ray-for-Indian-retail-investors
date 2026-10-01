"""Package the weak-label SQuAD files as a private Kaggle dataset (the notebook's input).

    uv run python -m finsight.weaklabel.package --username <your-kaggle-username>

Writes ``data/processed/kaggle/finsight-weaklabel/`` (git-ignored): the full ``train.jsonl`` and
``dev.jsonl``, a 200-example slice of each for the smoke run, ``dataset-metadata.json`` and a
README. Upload with ``kaggle datasets create -p <folder>`` (private by default) or by dragging the
folder into kaggle.com/datasets/new. The data comes from public filings and the allow-listed
Excel columns only; nothing from the demo or gold IPOs is in it.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
from pathlib import Path

from finsight.core.config import get_settings

DATASET_NAME = "finsight-weaklabel"
SLICE_SIZE = 200
SLICE_SEED = 2026
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9-]{2,}$")

README = """# finsight-weaklabel

Weakly labelled SQuAD 2.0 data for the FinSight extractor (distant supervision from IPO cover
pages; see ADR-038). Files: `train.jsonl`, `dev.jsonl` (split by IPO), `*_200.jsonl` (smoke-test
slices with both answerable and unanswerable rows). Fields per row: id, ipo_id, field_id, title,
question, context, answers {text, answer_start}.
"""


def _slice(lines: list[str], n: int) -> list[str]:
    """``n`` rows, answerable and unanswerable kept in their original proportion."""
    if len(lines) <= n:
        return lines
    rng = random.Random(SLICE_SEED)
    has = [bool(json.loads(x)["answers"]["text"]) for x in lines]
    pos = [i for i, h in enumerate(has) if h]
    neg = [i for i, h in enumerate(has) if not h]
    n_pos = round(n * len(pos) / len(lines))
    picked = rng.sample(pos, min(n_pos, len(pos))) + rng.sample(neg, min(n - n_pos, len(neg)))
    return [lines[i] for i in sorted(picked)]


def package_dataset(
    source: Path, out_root: Path, username: str, slice_size: int = SLICE_SIZE
) -> Path:
    if not _USERNAME.match(username):
        raise ValueError(f"username {username!r} is not a Kaggle username (lowercase, digits, -)")
    train, dev = source / "train.jsonl", source / "dev.jsonl"
    if not (train.exists() and dev.exists()):
        raise FileNotFoundError(
            f"{source} has no train.jsonl/dev.jsonl; run `python -m finsight.weaklabel build`"
        )
    out = out_root
    out.mkdir(parents=True, exist_ok=True)
    for name, path in (("train", train), ("dev", dev)):
        shutil.copyfile(path, out / f"{name}.jsonl")
        lines = path.read_text(encoding="utf-8").splitlines()
        (out / f"{name}_{SLICE_SIZE}.jsonl").write_text(
            "\n".join(_slice(lines, slice_size)) + "\n", encoding="utf-8", newline="\n"
        )
    meta = {
        "title": DATASET_NAME,
        "id": f"{username}/{DATASET_NAME}",
        "licenses": [{"name": "CC-BY-NC-SA-4.0"}],
    }
    (out / "dataset-metadata.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    (out / "README.md").write_text(README, encoding="utf-8", newline="\n")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="finsight.weaklabel.package")
    parser.add_argument("--username", required=True, help="your Kaggle username")
    args = parser.parse_args(argv)
    paths = get_settings().paths
    out = package_dataset(
        paths.processed_dir / "weaklabel",
        paths.processed_dir / "kaggle" / DATASET_NAME,
        args.username,
    )
    size = sum(p.stat().st_size for p in out.iterdir()) / 1e6
    print(f'packaged {out} ({size:.1f} MB). Upload: kaggle datasets create -p "{out}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
