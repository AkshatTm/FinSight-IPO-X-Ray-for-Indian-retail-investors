"""Export the teacher's input: train-slice risks, capped per company (C2.1).

    uv run python scripts/export_teacher_input.py [--n 12000]

Writes `data/processed/teacher/risks.jsonl` (gitignored) and the committed manifest
`data/manifests/teacher_input.json` (kind train: the leakage test checks it). Prints the
achievable number, because the cap can make it smaller than the 12,000 target.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_risk_bank import make_source  # noqa: E402

from finsight.risks import risks_config  # noqa: E402
from finsight.risks.teacher_input import Candidate, select  # noqa: E402
from finsight.splits import Manifest, file_sha256, load_splits, write_manifest  # noqa: E402

OUT = ROOT / "data" / "processed" / "teacher" / "risks.jsonl"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=None, help="override teacher.n_risks")
    ap.add_argument("--splits", type=Path, default=ROOT / "configs" / "splits.yaml")
    a = ap.parse_args(argv)
    cfg = dict(risks_config()["teacher"])
    if a.n:
        cfg["n_risks"] = a.n
    splits = load_splits(a.splits)
    source = make_source(splits)
    cands = []
    for e in splits.ipos:
        if e.slice != "train":
            continue  # dev, test and bench never reach the teacher's training input
        year = e.doc_date.year if e.doc_date else e.close_year
        for r in source(e) or []:
            cands.append(Candidate(f"{e.ipo_id}#{r.rid}", e.ipo_id, e.company, int(year or 0),
                                   r.title, r.body))  # fmt: skip
    sel = select(cands, **cfg)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for c in sel.chosen:
            fh.write(json.dumps(c.as_row(), ensure_ascii=False) + "\n")
    ids = sorted({c.ipo_id for c in sel.chosen})
    write_manifest(
        Manifest(artefact="teacher_input", kind="train", ipo_ids=ids,
                 written_by="scripts/export_teacher_input.py", sha256=file_sha256(OUT),
                 note=f"{len(sel.chosen)} risks; achievable {sel.achievable}; cap "
                      f"{cfg['per_company_cap']} per company"),
        ROOT / "data" / "manifests",
    )  # fmt: skip
    by_year = Counter(c.year for c in sel.chosen)
    print(f"candidates {len(cands)} -> achievable {sel.achievable}, target {sel.target}, "
          f"written {len(sel.chosen)} from {len(ids)} IPOs")  # fmt: skip
    print("dropped:", sel.dropped)
    print("by year:", dict(sorted(by_year.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
