"""Score the reference IPOs' risks (and red flags) for the risk-level fit (C2.8).

    uv run --group ml python scripts/score_reference_ipos.py [--limit N] [--only ipo-id ...]
        [--slices train dev] [--no-flags] [--device cuda]

For every **train + dev** IPO that has rows in the risk bank, this does what the upload pipeline
will do for a new document (C3.3), in one batch:

1. category: the shipped classifier (``models/risk_classifier/seed-42/final``, torch fp32 on the
   laptop GPU; the ONNX export agrees with it on 1,060 dev risks, ``eval_results/c/classifier_onnx_check.json``);
2. novelty: against the bank cut to the IPO's rolling reference window (``kind="eval"``: train and
   dev IPOs only, the issuer left out, C-ADR-03), using the bank's stored bge-m3 vectors;
3. seriousness and importance from ``configs/risks.yaml`` (no reference amount, as in the pipeline);
4. for documents with word boxes (2024+), the red flags: ``extract_summary`` + the rules X-Ray (no
   Objects table, as in ``scripts/compare_reference.py``) + the severe overrides.

Writes ``data/processed/risk_bank/scored/<ipo_id>.json`` (and ``<ipo_id>.flags.json``) for
``scripts/corpus_points.py``. Test and bench IPOs are never scored here. Category predictions are
cached in ``data/processed/risk_bank/categories.json`` so an interrupted run resumes.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_risk_bank  # noqa: E402
import summary_coverage  # noqa: E402
from pydantic import TypeAdapter  # noqa: E402

from finsight.core.schemas import ParsedDoc, Risk, Section  # noqa: E402
from finsight.extract import upload_xray  # noqa: E402
from finsight.ingest.fetch import read_rows  # noqa: E402
from finsight.parse import find_sections  # noqa: E402
from finsight.redflags import detect_severe, evaluate, inputs_from_summary  # noqa: E402
from finsight.redflags.severe import with_auditor  # noqa: E402
from finsight.risks import risks_config  # noqa: E402
from finsight.risks.bank import load_bank  # noqa: E402
from finsight.risks.features import add_features  # noqa: E402
from finsight.risks.seriousness import score_risks  # noqa: E402
from finsight.risks.teacher_data import original_text  # noqa: E402
from finsight.splits import load_splits, reference_bank, reference_config  # noqa: E402
from finsight.summary import extract_summary  # noqa: E402

DATA = Path(
    os.environ.get("FINSIGHT_DATA_DIR", ROOT / "data")
)  # gitignored data may live elsewhere
PROCESSED = DATA / "processed"
build_risk_bank.PROCESSED = PROCESSED
BANK = PROCESSED / "bank" / "risk_bank.parquet"
OUT = PROCESSED / "risk_bank" / "scored"
CATEGORIES = PROCESSED / "risk_bank" / "categories.json"
MODEL = ROOT / "models" / "risk_classifier" / "seed-42" / "final"
LABELS = ROOT / "models" / "risk_classifier" / "onnx" / "labels.json"
REPORT = ROOT / "eval_results" / "c" / "risklevel_scoring.json"
SECTIONS = TypeAdapter(list[Section])


class StoredVectors:
    """An embedder that hands back the bank's stored bge-m3 vectors, in the document's order."""

    def __init__(self, vectors: np.ndarray) -> None:
        self.vectors = vectors

    def embed(self, texts: Any) -> np.ndarray:
        """The stored vectors (one per text, same order as the bank rows of the IPO)."""
        assert len(texts) == len(self.vectors)
        return self.vectors


def read_bank_rows() -> dict[str, tuple[list[str], np.ndarray]]:
    """IPO id -> (risk ids in bank order, stored embeddings)."""
    import pyarrow.parquet as pq

    table = pq.read_table(BANK, columns=["risk_id", "ipo_id", "embedding"])
    ids = table.column("ipo_id").to_pylist()
    rids = table.column("risk_id").to_pylist()
    emb = np.stack([np.asarray(e, dtype=np.float32) for e in table.column("embedding").to_pylist()])
    out: dict[str, tuple[list[str], list[int]]] = {}
    for i, (ipo, rid) in enumerate(zip(ids, rids, strict=True)):
        entry = out.setdefault(str(ipo), ([], []))
        entry[0].append(str(rid))
        entry[1].append(i)
    return {k: (v[0], emb[v[1]]) for k, v in out.items()}


def classify(texts: dict[str, str], device: str) -> dict[str, list[Any]]:
    """Category and probability per risk id (torch fp32, length-sorted batches, cached)."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    cache: dict[str, list[Any]] = (
        json.loads(CATEGORIES.read_text(encoding="utf-8")) if CATEGORIES.exists() else {}
    )
    todo = [k for k in texts if k not in cache]
    if not todo:
        return cache
    tok = AutoTokenizer.from_pretrained(str(MODEL))
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL)).to(device).eval()
    assert model.config.num_labels == len(labels)
    todo.sort(key=lambda k: len(texts[k]))
    started, batch = time.time(), 16
    for n, lo in enumerate(range(0, len(todo), batch)):
        keys = todo[lo : lo + batch]
        enc = tok(
            [texts[k] for k in keys], truncation=True, max_length=384, padding=True,
            return_tensors="pt",
        ).to(device)  # fmt: skip
        with torch.inference_mode():
            probs = torch.softmax(model(**enc).logits.float(), dim=-1).cpu().numpy()
        for k, p in zip(keys, probs, strict=True):
            j = int(p.argmax())
            cache[k] = [labels[j], round(float(p[j]), 4)]
        if n % 100 == 99 or lo + batch >= len(todo):
            CATEGORIES.parent.mkdir(parents=True, exist_ok=True)
            CATEGORIES.write_text(json.dumps(cache), encoding="utf-8", newline="\n")
            done = min(lo + batch, len(todo))
            print(f"classified {done}/{len(todo)} ({time.time() - started:.0f}s)", flush=True)
    return cache


def red_flags(
    entry: Any, sha: str | None, ipo_id: str, company: str
) -> tuple[dict[str, Any] | None, str]:
    """The red flags of one full document, or ``None`` and the reason."""
    parsed_path, _ = summary_coverage.doc_paths(PROCESSED, ipo_id, sha)
    if not parsed_path.exists():
        return None, "no_parse"
    doc = ParsedDoc.model_validate_json(parsed_path.read_bytes())
    if not any(p.words for p in doc.pages[:5]):
        return None, "no_word_boxes"
    sections: list[Section] = find_sections(doc)  # fresh, as the upload pipeline does
    summary = extract_summary(doc, sections, ipo_id)
    xray = upload_xray(doc, sections, [], ipo_id, company)
    inputs = inputs_from_summary(summary, xray)
    remark = next((v.evidence for v in summary.auditor_remarks if v.evidence), None)
    severe = with_auditor(
        inputs.auditor == "qualified", detect_severe(doc, sections, ipo_id), remark
    )
    return evaluate(inputs, severe=severe).model_dump(mode="json"), "ok"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slices", nargs="+", default=["train", "dev"], choices=["train", "dev"])
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-flags", action="store_true")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args(argv)

    splits = load_splits(ROOT / "configs" / "splits.yaml")
    entries = [e for e in splits.ipos if e.slice in a.slices]
    if a.only:
        entries = [e for e in entries if e.ipo_id in set(a.only)]
    rows = read_bank_rows()
    entries = [e for e in entries if e.ipo_id in rows]
    entries = entries[: a.limit] if a.limit else entries
    sha = {r["ipo_id"]: r["sha256"] for r in read_rows(ROOT / "configs" / "ipo_universe.csv")}
    source = build_risk_bank.make_source(splits)

    risks_by_ipo: dict[str, list[Risk]] = {}
    problems: dict[str, str] = {}
    texts: dict[str, str] = {}
    for e in entries:
        risks = source(e)
        ids = [f"{e.ipo_id}#{r.rid}" for r in risks]
        if ids != rows[e.ipo_id][0]:
            problems[e.ipo_id] = "risks differ from the bank rows"
            continue
        risks_by_ipo[e.ipo_id] = risks
        for r, rid in zip(risks, ids, strict=True):
            texts[rid] = original_text({"title": r.title, "body": r.body})
    print(f"{len(risks_by_ipo)} IPOs, {len(texts)} risks to score", flush=True)
    cats = classify(texts, a.device)

    cfg, window = risks_config(), int(reference_config()["window_years"])
    tau, nearest = float(cfg["novelty"]["tau"]), 1
    bank = load_bank(BANK, years=None)
    OUT.mkdir(parents=True, exist_ok=True)
    stats: list[dict[str, Any]] = []
    flag_status: dict[str, str] = {}
    started = time.time()
    for i, e in enumerate(entries, 1):
        if e.ipo_id not in risks_by_ipo:
            continue
        as_of = e.doc_date or date(int(e.close_year or 0), 12, 31)
        wb = reference_bank(
            bank,
            splits,
            as_of,
            window,
            kind="eval",
            exclude_ipo=e.ipo_id,
            exclude_company=e.company,
        )
        rids, vectors = rows[e.ipo_id]
        risks = [
            r.model_copy(update={"category": cats[rid][0], "category_conf": cats[rid][1]})
            for r, rid in zip(risks_by_ipo[e.ipo_id], rids, strict=True)
        ]
        feats = add_features(
            risks, e.company, bank=wb, embedder=StoredVectors(vectors), tau=tau, nearest=nearest
        )
        scored = score_risks(feats, cfg["seriousness"])
        (OUT / f"{e.ipo_id}.json").write_text(
            json.dumps([r.model_dump(mode="json") for r in scored]), encoding="utf-8", newline="\n"
        )
        high = sum(r.seriousness == "high" for r in scored)
        stats.append({"ipo_id": e.ipo_id, "slice": e.slice, "source": e.source, "risks": len(scored),
                      "window_ipos": len(set(wb.ipo_ids or [])), "high": high})  # fmt: skip
        if e.source != "corpus" and not a.no_flags:
            try:
                flags, why = red_flags(e, sha.get(e.ipo_id), e.ipo_id, e.company)
            except Exception as err:  # one bad document must not stop the run
                flags, why = None, f"error: {type(err).__name__}"
            flag_status[e.ipo_id] = why
            if flags is not None:
                (OUT / f"{e.ipo_id}.flags.json").write_text(
                    json.dumps(flags), encoding="utf-8", newline="\n"
                )
        if i % 20 == 0:
            print(f"{i}/{len(entries)} scored ({time.time() - started:.0f}s)", flush=True)

    n_window = [s["window_ipos"] for s in stats]
    report = {
        "written_by": "scripts/score_reference_ipos.py",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "classifier": "models/risk_classifier/seed-42/final (torch fp32; ONNX export agrees, 1.000)",
        "novelty": {"tau": tau, "window_years": window, "kind": "eval", "nearest": nearest},
        "n_ipos": len(stats), "n_risks": sum(s["risks"] for s in stats),
        "by_source": {k: sum(s["source"] == k for s in stats) for k in ("corpus", "new", "showcase")},
        "flags": {k: sum(v == k for v in flag_status.values()) for k in sorted(set(flag_status.values()))},
        "window_ipos": {"min": min(n_window), "median": statistics.median(n_window), "max": max(n_window)}
        if n_window else {},
        "problems": problems,
        "caveats": [
            "no reference amount for the material-number rule (as in the pipeline)",
            "X-Ray built from rules only, without the Objects table (as in compare_reference.py)",
        ],
        "ipos": stats,
    }  # fmt: skip
    REPORT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("ipos", "caveats")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
