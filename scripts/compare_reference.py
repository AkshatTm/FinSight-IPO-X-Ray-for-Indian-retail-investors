"""Reference quantiles for the Compare tab over the rolling window (C3.4, C-ADR-03).

    uv run python scripts/compare_reference.py --data <data dir> [--as-of YYYY-MM-DD] [--limit N]
        [--only ipo-id ...] [--write]

"Past IPOs" are the product reference of ``finsight.splits`` (every collected IPO dated within
``configs/reference.yaml: window_years`` before ``--as-of``, default today). For each one found in
the batch store (full words and boxes) or the text corpus (close year only), the X-Ray is built
with the same ``upload_xray`` the upload pipeline uses and the four Compare numbers are read with
``finsight.compare.compare_metrics``. A number the document does not print is left out of that
metric's quantiles; ``metric_n`` records how many IPOs each metric rests on, and a metric with
fewer than ``--min-n`` values is dropped (the tab then shows no percentile for it, never a typed
one). Quantiles are linear-interpolated percentiles 0, 10, ..., 100.

Per-IPO numbers are cached in ``--cache`` so an interrupted run resumes. Nothing here reads listing
outcomes. Without ``--write`` the YAML is printed, not written.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.compare import METRICS, compare_metrics  # noqa: E402
from finsight.compare.metrics import plausible  # noqa: E402
from finsight.core.ids import make_doc_id  # noqa: E402
from finsight.core.schemas import FinancialSummary, Page, ParsedDoc, Section  # noqa: E402
from finsight.extract import upload_xray  # noqa: E402
from finsight.ingest.corpus import load_corpus_doc  # noqa: E402
from finsight.ingest.fetch import read_rows  # noqa: E402
from finsight.splits import ipos_before, load_splits, reference_config  # noqa: E402
from finsight.summary import extract_summary  # noqa: E402

CONFIG = ROOT / "configs" / "compare.yaml"
UNIVERSE = ROOT / "configs" / "ipo_universe.csv"
STEPS = [i * 10 for i in range(11)]


def percentile_points(values: list[float]) -> list[float]:
    """Linear-interpolated values at percentiles 0, 10, ..., 100."""
    ordered = sorted(values)
    out = []
    for q in STEPS:
        pos = (len(ordered) - 1) * q / 100
        lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
        out.append(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))
    return [float(f"{v:.6g}") for v in out]


def _batch_dir(data: Path, ipo_id: str, sha_by_ipo: dict[str, str]) -> Path | None:
    sha = sha_by_ipo.get(ipo_id)
    if not sha:
        return None
    path = data / "processed" / "batch" / "store" / "docs" / make_doc_id(sha)
    return path if (path / "parsed.json").exists() else None


def load_document(
    data: Path, ipo_id: str, sha_by_ipo: dict[str, str]
) -> tuple[ParsedDoc, list[Section]] | None:
    """Parsed document and sections from the batch store, else the text corpus."""
    batch = _batch_dir(data, ipo_id, sha_by_ipo)
    if batch is not None:
        doc = ParsedDoc.model_validate_json((batch / "parsed.json").read_bytes())
        sections = [
            Section.model_validate(s) for s in json.loads((batch / "sections.json").read_bytes())
        ]
        return doc, sections
    corpus = data / "processed" / "corpus" / f"{ipo_id}.json"
    if corpus.exists():
        c = load_corpus_doc(corpus)
        pages = [
            Page(number=p.number, width=0.0, height=0.0, words=[], text=p.text, is_scanned=False)
            for p in c.pages
        ]
        doc = ParsedDoc(
            ipo_id=ipo_id, doc_type=c.doc_kind, source_path=c.source_file,
            n_pages=len(pages), pages=pages, sha256="",
        )  # fmt: skip
        return doc, c.sections
    return None


def numbers_for(
    doc: ParsedDoc, sections: list[Section], ipo_id: str, company: str
) -> dict[str, Any]:
    """The four Compare numbers of one document (``None`` where it prints none)."""
    xray = upload_xray(doc, sections, [], ipo_id, company)
    has_boxes = any(p.words for p in doc.pages[:5])
    summary = (
        extract_summary(doc, sections, ipo_id) if has_boxes else FinancialSummary(doc_id=ipo_id)
    )
    metrics, _ = compare_metrics(xray, summary)
    return {k: (float(v) if v is not None else None) for k, v in metrics.items()}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    ap.add_argument("--min-n", type=int, default=20)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--cache", type=Path, default=ROOT / "data" / "processed" / "compare_ref.json")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    splits = load_splits(ROOT / "configs" / "splits.yaml")
    window = int(reference_config()["window_years"])
    entries = ipos_before(splits, a.as_of, window, kind="product")
    if a.only:
        entries = [e for e in entries if e.ipo_id in set(a.only)]
    if a.limit:
        entries = entries[: a.limit]
    sha_by_ipo = {r["ipo_id"]: r.get("sha256", "") for r in read_rows(UNIVERSE)}
    cache: dict[str, Any] = (
        json.loads(a.cache.read_text(encoding="utf-8")) if a.cache.exists() else {}
    )
    started = time.time()
    for i, e in enumerate(entries, 1):
        if e.ipo_id in cache:
            continue
        loaded = load_document(a.data, e.ipo_id, sha_by_ipo)
        if loaded is None:
            cache[e.ipo_id] = {"status": "no_document"}
            continue
        try:
            cache[e.ipo_id] = {"status": "ok", **numbers_for(*loaded, e.ipo_id, e.company)}
        except Exception as err:  # one bad document must not stop the run
            cache[e.ipo_id] = {"status": f"error: {type(err).__name__}"}
        a.cache.parent.mkdir(parents=True, exist_ok=True)
        a.cache.write_text(json.dumps(cache), encoding="utf-8", newline="\n")
        print(f"{i}/{len(entries)} {e.ipo_id} {cache[e.ipo_id]['status']} "
              f"({time.time() - started:.0f}s)", flush=True)  # fmt: skip

    done = {
        k: v
        for k, v in cache.items()
        if v.get("status") == "ok" and k in {e.ipo_id for e in entries}
    }
    quantiles: dict[str, list[float]] = {}
    metric_n: dict[str, int] = {}
    for metric in METRICS:
        values = [float(v[metric]) for v in done.values() if plausible(metric, v.get(metric))]
        metric_n[metric] = len(values)
        if len(values) >= a.min_n:
            quantiles[metric] = percentile_points(values)
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    ).stdout.strip()
    config = {
        "provisional": len(quantiles) < len(METRICS),
        "computed_on": f"{a.as_of.isoformat()} @ {sha}",
        "window_years": window,
        "corpus_n": len(done),
        "metric_n": metric_n,
        "reference_quantiles": quantiles,
    }
    status: dict[str, int] = {}
    for v in cache.values():
        status[v["status"]] = status.get(v["status"], 0) + 1
    header = (
        "# Compare tab reference (B05 §5.6, C3.4). Written by scripts/compare_reference.py over the\n"
        "# rolling window (configs/reference.yaml); never typed by hand. A metric with fewer than\n"
        "# min_n values is absent and the tab shows no percentile for it. provisional stays true\n"
        "# while any metric is missing.\n"
    )
    text = header + yaml.safe_dump(config, sort_keys=False)
    print(json.dumps({"entries": len(entries), "status": status, "metric_n": metric_n,
                      "median_values": {m: statistics.median([float(v[m]) for v in done.values()
                                         if v.get(m) is not None] or [0]) for m in METRICS},
                      "at": datetime.now(UTC).isoformat(timespec="seconds")}, indent=1))  # fmt: skip
    if a.write:
        CONFIG.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {CONFIG}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
