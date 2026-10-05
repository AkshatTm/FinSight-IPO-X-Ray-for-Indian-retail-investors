"""Teacher bake-off helper: sample, blind sheet, score (C2.2, C-ADR-05).

    uv run python scripts/teacher_bakeoff.py sample            # 300 train+dev risks -> bakeoff_risks.jsonl
    # ... run the Colab notebook (COLAB_STEPS_teacher_bakeoff.md), copy raw_<model>.jsonl back ...
    uv run python scripts/teacher_bakeoff.py sheet             # blind 100-row sheet + secret key
    # ... Akshat rates data/processed/teacher/bakeoff/bakeoff_sheet.csv (not the key!) ...
    uv run python scripts/teacher_bakeoff.py score             # -> eval_results/c/teacher_bakeoff.json

Files live in `data/processed/teacher/bakeoff/` (gitignored). Only the result JSON is committed.
The key file maps sheet ids to models: do not open it before rating.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from finsight.risks.bakeoff import (  # noqa: E402
    build_sheet,
    read_sheet,
    sample_risks,
    score,
    write_result,
    write_sheet,
)
from finsight.risks.teacher_data import filter_file  # noqa: E402
from finsight.risks.teacher_input import Candidate  # noqa: E402

DIR = ROOT / "data" / "processed" / "teacher" / "bakeoff"
RISKS = DIR / "bakeoff_risks.jsonl"
SHEET = DIR / "bakeoff_sheet.csv"
KEY = DIR / "bakeoff_key.json"
RESULT = ROOT / "eval_results" / "c" / "teacher_bakeoff.json"


def raw_files() -> dict[str, Path]:
    """``model slug -> raw_<slug>.jsonl`` for every model run copied back from Colab."""
    return {p.stem.removeprefix("raw_"): p for p in sorted(DIR.glob("raw_*.jsonl"))}


def cmd_sample() -> None:
    """Write the 300-risk input and its manifest."""
    from build_risk_bank import make_source

    from finsight.splits import Manifest, file_sha256, load_splits, write_manifest

    splits = load_splits(ROOT / "configs" / "splits.yaml")
    source = make_source(splits)
    cands = []
    for e in splits.ipos:
        if e.slice not in ("train", "dev"):
            continue  # never test or bench
        year = e.doc_date.year if e.doc_date else e.close_year
        for r in source(e) or []:
            if 40 <= len(f"{r.title} {r.body}".split()) <= 600:
                cands.append(Candidate(f"{e.ipo_id}#{r.rid}", e.ipo_id, e.company, int(year or 0),
                                       r.title, r.body))  # fmt: skip
    picked = sample_risks(cands, 300)
    DIR.mkdir(parents=True, exist_ok=True)
    with RISKS.open("w", encoding="utf-8", newline="\n") as fh:
        for c in picked:
            fh.write(json.dumps(c.as_row(), ensure_ascii=False) + "\n")
    write_manifest(
        Manifest(artefact="teacher_bakeoff_input", kind="train",
                 ipo_ids=sorted({c.ipo_id for c in picked}), sha256=file_sha256(RISKS),
                 written_by="scripts/teacher_bakeoff.py", note="300 train+dev risks"),
        ROOT / "data" / "manifests",
    )  # fmt: skip
    print(f"wrote {len(picked)} risks from {len({c.ipo_id for c in picked})} IPOs -> {RISKS}")


def reports() -> tuple[dict, dict, dict]:
    """Filter reports, kept outputs and run seconds per model."""
    rep, kept, secs = {}, {}, {}
    for slug, raw in raw_files().items():
        report, _ = filter_file(RISKS, raw)
        rep[slug], kept[slug] = report.summary(), report.kept
        summary = DIR / f"run_summary_{slug}.json"
        secs[slug] = json.loads(summary.read_text())["seconds"] if summary.exists() else None
    return rep, kept, secs


def cmd_sheet() -> None:
    """Write the blind sheet and the secret key."""
    _, kept, _ = reports()
    if len(kept) < 2:
        sys.exit("need raw_<model>.jsonl for two models in " + str(DIR))
    rows, key = build_sheet(kept)
    write_sheet(rows, SHEET)
    KEY.write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"wrote {len(rows)} rows -> {SHEET}; the model key is in {KEY.name} (do not open it)")


def cmd_score() -> None:
    """Score the rated sheet and write ``eval_results/c/teacher_bakeoff.json``."""
    rep, _, secs = reports()
    result = score(read_sheet(SHEET), json.loads(KEY.read_text(encoding="utf-8")), rep, secs)
    result["label_source"] = "human:akshat (ratings); teacher outputs are AI labels"
    write_result(result, RESULT)
    print(json.dumps(result["pick"]), "->", RESULT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["sample", "sheet", "score"])
    {"sample": cmd_sample, "sheet": cmd_sheet, "score": cmd_score}[ap.parse_args(argv).command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
