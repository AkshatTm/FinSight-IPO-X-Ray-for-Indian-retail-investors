"""Build the risk bank and the evaluation bank from the frozen split (C2.1, C03 §3).

* ``risk_bank.parquet``: every risk of every **train** and **dev** IPO (corpus + new + showcase),
  with ``ipo_id``, ``doc_date`` and ``split``. Manifest kind ``train``.
* ``risk_eval.parquet``: the risks of **test** (and bench) IPOs, used only at evaluation time.
  Manifest kind ``eval``.
* ``risk_bank_product`` manifest (kind ``product_reference``): every collected IPO; the product's
  novelty window reads both parquets.

Pure functions here; ``scripts/build_risk_bank.py`` supplies the real sources and the bge-m3
embedder, tests supply fakes. Embedding text is ``embed_text(title, body)`` (title + first two
sentences), the same text a new document's risks are embedded with.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from finsight.core.schemas import Risk
from finsight.risks.novelty import embed_text

BANK_SLICES = ("train", "dev")
EVAL_SLICES = ("test",)
COLUMNS = ("risk_id", "company", "year", "title", "embedding", "ipo_id", "doc_date", "split")

RiskSource = Callable[[Any], "list[Risk] | None"]  # SplitEntry -> risks, or None if missing
Embed = Callable[[Sequence[str]], np.ndarray]


@dataclass
class BuildResult:
    """What a build produced (for the manifest, the datasheet and E13)."""

    rows: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {"bank": [], "eval": []})
    per_ipo: dict[str, int] = field(default_factory=dict)  # ipo_id -> number of risks
    missing: list[str] = field(default_factory=list)  # IPOs with no document/risks
    skipped: list[str] = field(default_factory=list)  # IPOs in no slice (should be empty)


def corpus_risks(doc: Any) -> list[Risk]:
    """Risks of a corpus document: the Risk Factors section's page texts, split by numbering."""
    from finsight.risks.segment import segment_text, to_risks

    section = next((s for s in doc.sections if s.id == "risk_factors"), None)
    if section is None:
        return []
    text = "\n\n".join(
        p.text for p in doc.pages if section.start_page <= p.number <= section.end_page
    )
    return to_risks(segment_text(text))


def build_rows(
    splits: Any,
    source: RiskSource,
    embed: Embed,
    *,
    batch: int = 256,
    log: Callable[[str], None] = lambda m: None,
) -> BuildResult:
    """Segment (via ``source``) and embed every IPO of the split.

    Args:
        splits: A ``finsight.splits.SplitsFile``.
        source: ``SplitEntry -> list[Risk]`` (``None`` or empty = the document is missing).
        embed: ``texts -> (n, d) array`` (bge-m3, or a fake in tests).
        batch: Texts per embedding call.
        log: Progress sink.
    """
    out = BuildResult()
    for e in splits.ipos:
        which = "bank" if e.slice in BANK_SLICES else "eval" if e.slice in EVAL_SLICES else None
        if which is None:
            out.skipped.append(e.ipo_id)
            continue
        risks = source(e)
        if not risks:
            out.missing.append(e.ipo_id)
            continue
        texts = [embed_text(r.title, r.body) for r in risks]
        vectors = np.vstack([embed(texts[i : i + batch]) for i in range(0, len(texts), batch)])
        year = e.doc_date.year if e.doc_date else e.close_year
        for r, v in zip(risks, vectors, strict=True):
            out.rows[which].append(
                {
                    "risk_id": f"{e.ipo_id}#{r.rid}",
                    "company": e.company,
                    "year": int(year or 0),
                    "title": r.title,
                    "embedding": np.asarray(v, dtype=np.float32).tolist(),
                    "ipo_id": e.ipo_id,
                    "doc_date": e.doc_date.isoformat() if e.doc_date else "",
                    "split": e.slice,
                }
            )
        out.per_ipo[e.ipo_id] = len(risks)
        log(f"{e.ipo_id}: {len(risks)} risks")
    return out


def write_parquet(rows: Iterable[dict[str, Any]], path: Path) -> int:
    """Write rows to a parquet file (empty file with the right schema when there are none)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    rows = list(rows)
    dim = len(rows[0]["embedding"]) if rows else 1
    schema = pa.schema(
        [
            ("risk_id", pa.string()),
            ("company", pa.string()),
            ("year", pa.int32()),
            ("title", pa.string()),
            ("embedding", pa.list_(pa.float32(), dim)),
            ("ipo_id", pa.string()),
            ("doc_date", pa.string()),
            ("split", pa.string()),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema) if rows else schema.empty_table()
    pq.write_table(table, path)
    return len(rows)


def segmentation_stats(per_ipo: dict[str, list[Risk]], entries: dict[str, Any]) -> dict[str, Any]:
    """E13 (automatic part): how the segmenter behaves, by source. No gold is involved."""
    by_source: dict[str, list[list[Risk]]] = {}
    for ipo, risks in per_ipo.items():
        src = entries[ipo].source if ipo in entries else "unknown"
        by_source.setdefault(src, []).append(risks)
    out: dict[str, Any] = {}
    for src, docs in sorted(by_source.items()):
        counts = sorted(len(d) for d in docs)
        title_words = [len(r.title.split()) for d in docs for r in d]
        body_words = [len(r.body.split()) for d in docs for r in d]
        dupes = sum(len(d) - len({r.title for r in d}) for d in docs)
        out[src] = {
            "documents": len(docs),
            "documents_with_no_risks": sum(1 for d in docs if not d),
            "risks_total": sum(counts),
            "risks_per_doc": {
                "min": counts[0] if counts else 0,
                "median": statistics.median(counts) if counts else 0,
                "max": counts[-1] if counts else 0,
            },
            "title_words_median": statistics.median(title_words) if title_words else 0,
            "body_words_median": statistics.median(body_words) if body_words else 0,
            "body_empty": sum(1 for w in body_words if w == 0),
            "duplicate_titles_within_doc": dupes,
        }
    return out


def count_by_year(rows: Iterable[dict[str, Any]]) -> dict[int, int]:
    """Risks per year (for the datasheet)."""
    return dict(sorted(Counter(int(r["year"]) for r in rows).items()))


def write_json(path: Path, data: Any) -> None:
    """Write JSON with LF endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
