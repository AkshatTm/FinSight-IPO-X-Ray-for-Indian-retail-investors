"""C2.7 extractor v2: weak labels over the time-split ``train`` slice incl. 2024+ IPOs.

    uv run python scripts/extractor_v2.py build --processed <data/processed> --raw <data/raw>
        # -> <processed>/weaklabel_v3/{train,dev}.jsonl, eval_results/c/weaklabel_v3_stats.json,
        #    data/manifests/weaklabel_v3_{train,dev}.json

What is different from v1 (label_version 2):

* the documents are chosen by ``configs/splits.yaml``: ``train`` slice = training rows, ``dev`` slice
  = dev rows (new, so v1 and v2 can be compared on documents neither saw); the ``test`` slice and
  every showcase / gold-v3 / demo IPO never enter (C-ADR-02, checked again before writing);
* 2024+ documents are read from the batch parse store (``parsed.json`` + ``sections.json``);
* seed values come from the Rung-1 rules on the cover pages alone for those documents (the Excel
  columns end in 2023, so ``excel`` is ``absent``); the same single-value and arithmetic checks
  apply, nothing is hand-labelled.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.core.ids import make_doc_id  # noqa: E402
from finsight.core.schemas import ParsedDoc, Section  # noqa: E402
from finsight.extract import get_field  # noqa: E402
from finsight.ingest.corpus import EXCEL_NAME, load_corpus_doc  # noqa: E402
from finsight.ingest.exclusion import excluded_names, is_excluded  # noqa: E402
from finsight.ingest.fetch import read_rows  # noqa: E402
from finsight.splits import Manifest, file_sha256, load_splits, write_manifest  # noqa: E402
from finsight.weaklabel.__main__ import excel_rows  # noqa: E402
from finsight.weaklabel.build_squad import _parsed, to_squad  # noqa: E402
from finsight.weaklabel.negatives import negatives  # noqa: E402
from finsight.weaklabel.propagate import propagate  # noqa: E402
from finsight.weaklabel.seeds import LADDER_FIELDS, excel_values, find_seeds  # noqa: E402

LABEL_VERSION = 3
SCRIPT = "scripts/extractor_v2.py"
MANIFESTS = ROOT / "data" / "manifests"
STATS = ROOT / "eval_results" / "c" / "weaklabel_v3_stats.json"


def _load(entry: Any, processed: Path, sha: dict[str, str], excel: dict[str, Any]):  # type: ignore[no-untyped-def]
    """``(ParsedDoc, sections, excel values)`` for one split entry, or ``None`` when unavailable."""
    if entry.source == "corpus":
        path = processed / "corpus" / f"{entry.ipo_id}.json"
        if not path.exists():
            return None
        doc = load_corpus_doc(path)
        return _parsed(doc), doc.sections, excel_values(excel.get(doc.mapping_key, {}))
    digest = sha.get(entry.ipo_id)
    if not digest:
        return None
    folder = processed / "batch" / "store" / "docs" / make_doc_id(digest)
    if not (folder / "parsed.json").exists() or not (folder / "sections.json").exists():
        return None
    parsed = ParsedDoc.model_validate_json((folder / "parsed.json").read_text(encoding="utf-8"))
    sections = [
        Section.model_validate(x) for x in json.loads((folder / "sections.json").read_text("utf-8"))
    ]
    return parsed, sections, {}


def build(processed: Path, raw: Path) -> dict[str, Any]:
    """Write v3 train/dev SQuAD rows from the split slices; return the dataset card."""
    splits = load_splits(ROOT / "configs" / "splits.yaml")
    showcase = {e.ipo_id for e in splits.ipos if e.source == "showcase"}
    excluded = excluded_names()
    sha = {r["ipo_id"]: r["sha256"] for r in read_rows(ROOT / "configs" / "ipo_universe.csv")}
    excel = excel_rows(raw / "ipo_dataset" / EXCEL_NAME)
    out_dir = processed / "weaklabel_v3"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_by_slice: dict[str, list[dict[str, Any]]] = {"train": [], "dev": []}
    seeded: Counter[str] = Counter()
    dropped: dict[str, Counter[str]] = {f: Counter() for f in LADDER_FIELDS}
    docs: Counter[str] = Counter()
    missing: list[str] = []
    skipped_showcase = skipped_excluded = 0
    for entry in splits.ipos:
        if entry.slice not in ("train", "dev"):
            continue
        if entry.ipo_id in showcase or entry.source == "showcase":
            skipped_showcase += 1
            continue
        if is_excluded(entry.company, excluded):
            skipped_excluded += 1
            continue
        loaded = _load(entry, processed, sha, excel)
        if loaded is None:
            missing.append(entry.ipo_id)
            continue
        parsed, sections, xl = loaded
        parsed = parsed.model_copy(update={"ipo_id": entry.ipo_id})
        docs[f"{entry.slice}/{entry.source}"] += 1
        report = find_seeds(parsed, sections, xl)
        for field_id, reason in report.dropped.items():
            dropped[field_id][reason] += 1
        for field_id, seed in report.seeds.items():
            seeded[f"{entry.source}:{field_id}"] += 1
            spec = get_field(field_id)
            pos = propagate(parsed, sections, spec, seed)
            neg = negatives(parsed, sections, spec, seed, pos)
            for k, example in enumerate(pos + neg):
                row = to_squad(example, spec.questions[k % len(spec.questions)])
                row["label_source"] = (
                    "rules_cover_seed" if entry.source == "new" else "rules+excel_seed"
                )
                rows_by_slice[entry.slice].append(row)

    leaked = [
        r["ipo_id"] for rows in rows_by_slice.values() for r in rows if r["ipo_id"] in showcase
    ]
    assert not leaked, f"showcase / gold IPO in the training data: {sorted(set(leaked))[:3]}"
    card: dict[str, Any] = {
        "label_version": LABEL_VERSION,
        "documents": dict(sorted(docs.items())),
        "skipped_showcase": skipped_showcase,
        "skipped_excluded": skipped_excluded,
        "missing_inputs": sorted(missing),
        "seeds_by_source_field": dict(sorted(seeded.items())),
        "seed_dropped": {f: dict(sorted(c.items())) for f, c in dropped.items()},
    }
    for name, rows in rows_by_slice.items():
        path = out_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        ids = sorted({r["ipo_id"] for r in rows})
        card[name] = {
            "ipos": len(ids),
            "examples": len(rows),
            "positives": sum(bool(r["answers"]["text"]) for r in rows),
            "by_label_source": dict(Counter(r["label_source"] for r in rows)),
        }
        write_manifest(
            Manifest(artefact=f"weaklabel_v3_{name}", kind="train" if name == "train" else "fit",
                     ipo_ids=ids, written_by=SCRIPT, sha256=file_sha256(path),
                     note="weak labels v3: split-slice documents only, no showcase / gold-v3 IPO"),
            MANIFESTS,
        )  # fmt: skip
    STATS.write_text(json.dumps(card, indent=1) + "\n", encoding="utf-8", newline="\n")
    return card


DATASET = "finsight-weaklabel-v3"
V2_MODELS = ROOT / "models" / "extractor_v2"
V2_EVAL = ROOT / "eval_results" / "c" / "extractor_v2"


def _patched_kaggle():  # type: ignore[no-untyped-def]
    """``finsight.weaklabel.kaggle`` pointed at the v3 dataset and v2 kernel names (v1 untouched)."""
    from finsight.weaklabel import kaggle, package

    package.DATASET_NAME = DATASET
    kaggle.DATASET_NAME = DATASET
    orig_slug, orig_params = kaggle.kernel_slug, kaggle.run_params

    def slug(run: str) -> str:
        return orig_slug(run).replace("finsight-extractor", "finsight-extractor-v2")

    def params(run: str) -> dict[str, Any]:
        return {**orig_params(run), "DATASET": DATASET}

    kaggle.kernel_slug, kaggle.run_params = slug, params
    return kaggle, package


def kaggle_command(a: argparse.Namespace) -> int:
    """package / push / status / fetch for the v2 runs (smoke, baseline, 13, 42, 2026)."""
    import shutil

    kaggle, package = _patched_kaggle()
    user = a.username.lower()
    work = a.processed / "kaggle"
    if a.command == "package":
        out = package.package_dataset(a.processed / "weaklabel_v3", work / DATASET, user)
        print("packaged", out)
        return 0
    slug = kaggle.kernel_slug(a.run)
    if a.command == "push":
        folder = kaggle.write_kernel(work / "kernels" / slug, user, a.run)
        return kaggle._kaggle(
            "kernels", "push", "-p", str(folder), "--accelerator", kaggle.ACCELERATOR
        )
    if a.command == "status":
        return kaggle._kaggle("kernels", "status", f"{user}/{slug}")
    out = work / "output" / slug
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    code = kaggle._kaggle("kernels", "output", f"{user}/{slug}", "-p", str(out), "-o", "-q")
    if code != 0:
        return code
    dev = [
        json.loads(x)
        for x in (a.processed / "weaklabel_v3" / "dev.jsonl").read_text("utf-8").splitlines()
        if x
    ]
    result = kaggle.collect(out, a.run, V2_MODELS, V2_EVAL, dev)
    for e in result["per_epoch"]:
        print(
            "epoch", e["epoch"], {k: round(v, 4) for k, v in e.items() if k in ("EM", "F1", "NVM")}
        )
    for w in result.get("warnings", []):
        print("WARNING:", w)
    for pr in result["problems"]:
        print("PROBLEM:", pr)
    return 1 if result["problems"] else 0


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    b.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    for name in ("package", "push", "status", "fetch"):
        k = sub.add_parser(name)
        k.add_argument("--username", required=True)
        k.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
        if name != "package":
            k.add_argument("run", help="smoke | baseline | 13 | 42 | 2026")
    a = ap.parse_args()
    if a.command == "build":
        card = build(a.processed, a.raw)
        print(
            json.dumps(
                {k: card[k] for k in ("documents", "skipped_showcase", "train", "dev")}, indent=1
            )
        )
    else:
        raise SystemExit(kaggle_command(a))


if __name__ == "__main__":
    main()
