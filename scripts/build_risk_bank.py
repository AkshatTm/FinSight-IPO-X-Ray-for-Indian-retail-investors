"""Build the risk bank, the evaluation bank and their manifests (C2.1).

    uv run python scripts/build_risk_bank.py [--limit-ipos 5] [--no-embed]

Needs the split (`configs/splits.yaml`), the corpus (`data/processed/corpus/`) and the batch
parse outputs (`data/processed/batch/`). Embeds with bge-m3 on the GPU when free (stop Ollama
first). Writes `data/processed/bank/risk_bank.parquet` (train + dev), `risk_eval.parquet` (test),
manifests in `data/manifests/` and `eval_results/b/segmentation.json` (E13, automatic part).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.core.ids import make_doc_id  # noqa: E402
from finsight.core.schemas import Risk  # noqa: E402
from finsight.ingest.corpus import load_corpus_doc  # noqa: E402
from finsight.ingest.fetch import read_rows  # noqa: E402
from finsight.risks.bank_build import (  # noqa: E402
    build_rows,
    corpus_risks,
    count_by_year,
    segmentation_stats,
    write_json,
    write_parquet,
)
from finsight.splits import Manifest, file_sha256, load_splits, write_manifest  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
BANK_DIR = PROCESSED / "bank"
MANIFESTS = ROOT / "data" / "manifests"
SCRIPT = "scripts/build_risk_bank.py"


def make_source(splits):  # type: ignore[no-untyped-def]
    """``SplitEntry -> list[Risk]`` from the corpus JSONs and the batch store."""
    sha = {r["ipo_id"]: r["sha256"] for r in read_rows(ROOT / "configs" / "ipo_universe.csv")}
    store = PROCESSED / "batch" / "store" / "docs"
    cache: dict[str, list[Risk]] = {}

    def source(entry):  # type: ignore[no-untyped-def]
        path = PROCESSED / "corpus" / f"{entry.ipo_id}.json"
        if entry.source == "corpus":
            risks = corpus_risks(load_corpus_doc(path)) if path.exists() else []
        else:
            digest = sha.get(entry.ipo_id)
            file = store / make_doc_id(digest) / "risks.json" if digest else None
            risks = (
                [Risk.model_validate(x) for x in json.loads(file.read_text(encoding="utf-8"))]
                if file is not None and file.exists()
                else []
            )
        cache[entry.ipo_id] = risks
        return risks

    source.cache = cache  # type: ignore[attr-defined]
    return source


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit-ipos", type=int, default=None)
    ap.add_argument(
        "--no-embed", action="store_true", help="zero vectors (segmentation stats only)"
    )
    ap.add_argument("--splits", type=Path, default=ROOT / "configs" / "splits.yaml")
    a = ap.parse_args(argv)
    splits = load_splits(a.splits)
    if a.limit_ipos:
        splits = splits.model_copy(update={"ipos": splits.ipos[: a.limit_ipos]})
    if a.no_embed:

        def embed(texts):  # type: ignore[no-untyped-def]
            return np.zeros((len(texts), 8), dtype=np.float32)
    else:
        from finsight.retrieve import BgeM3Embedder

        embed = BgeM3Embedder().embed
    source = make_source(splits)
    res = build_rows(splits, source, embed, log=lambda m: print(m, flush=True))
    n_bank = write_parquet(res.rows["bank"], BANK_DIR / "risk_bank.parquet")
    n_eval = write_parquet(res.rows["eval"], BANK_DIR / "risk_eval.parquet")
    by = {e.ipo_id: e for e in splits.ipos}
    bank_ids = sorted({r["ipo_id"] for r in res.rows["bank"]})
    eval_ids = sorted({r["ipo_id"] for r in res.rows["eval"]})
    write_manifest(
        Manifest(artefact="risk_bank", kind="train", ipo_ids=bank_ids, written_by=SCRIPT,
                 sha256=file_sha256(BANK_DIR / "risk_bank.parquet"), note="train + dev IPOs"),
        MANIFESTS,
    )  # fmt: skip
    write_manifest(
        Manifest(artefact="risk_eval", kind="eval", ipo_ids=eval_ids, written_by=SCRIPT,
                 sha256=file_sha256(BANK_DIR / "risk_eval.parquet"), note="test IPOs, eval only"),
        MANIFESTS,
    )  # fmt: skip
    write_manifest(
        Manifest(artefact="risk_bank_product", kind="product_reference",
                 ipo_ids=[*bank_ids, *eval_ids], inputs=["risk_bank", "risk_eval"],
                 written_by=SCRIPT, note="every collected IPO; product novelty window only"),
        MANIFESTS,
    )  # fmt: skip
    stats = segmentation_stats(
        {k: v for k, v in source.cache.items() if v},
        by,  # type: ignore[attr-defined]
    )
    stats["_meta"] = {
        "bank_rows": n_bank, "eval_rows": n_eval, "risks_by_year": count_by_year(res.rows["bank"]),
        "missing_documents": res.missing, "skipped": res.skipped,
        "gold_boundaries_e13b": "pending: Akshat's segmentation spot-check (AKSHAT_TODO)",
    }  # fmt: skip
    write_json(ROOT / "eval_results" / "b" / "segmentation.json", stats)
    print(f"bank {n_bank} rows ({len(bank_ids)} IPOs), eval {n_eval} rows ({len(eval_ids)} IPOs)")
    print("missing documents:", len(res.missing), res.missing[:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
