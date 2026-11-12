"""Row-level exports of the handoff pack: risk bank, classifier sets, student sets, five things.

Everything here is a pure transform over rows the caller has already read, plus two writers.
Each export drops rows of excluded IPOs (see ``selection``) and returns how many it dropped, so
the pack README can state it. Every row carries ``ipo_id`` and a ``label_source`` of ``human``,
``human_verified_ai``, ``ai``, ``rule`` or ``model`` (a shipped classifier's prediction).
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

TOP_FIVE = 5  # reports.TOP_RISKS: the "Five things to know" size at v1.0
FIVE_METHOD = "top 5 risks by (-importance, order) of risks_scored (reports.assemble at v1.0)"
MAX_BAND = 4  # seriousness bands 4 and 5 are merged (risks.clf_metrics.SEVERE_BAND)


def ipo_of(risk_id: str) -> str:
    """``<ipo_id>#r<k>`` -> ``<ipo_id>``."""
    return risk_id.split("#", 1)[0]


def rid_of(risk_id: str) -> str:
    """``<ipo_id>#r<k>`` -> ``r<k>``."""
    return risk_id.split("#", 1)[1] if "#" in risk_id else risk_id


def risk_bank_rows(
    bank: Iterable[Mapping[str, Any]],
    scored: Mapping[str, Sequence[Mapping[str, Any]]],
    teacher: Mapping[str, Mapping[str, Any]],
    categories: Mapping[str, Sequence[Any]],
    excluded: set[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """The risk bank without embeddings: text, page, category and severity with their sources.

    Category and severity band (1-4) come from the teacher labels (``ai``) when the risk has one;
    otherwise the category is the shipped classifier's (``model``) and the band is ``None`` (the
    bank stores no predicted band). ``rule_seriousness`` (low / medium / high) is the product's
    rule output and is not comparable with the bands. ``section`` is not stored by the bank and is
    left ``None`` (a known gap, named in the README).
    """
    by_ipo: dict[str, dict[str, Mapping[str, Any]]] = {
        i: {str(r["rid"]): r for r in rows} for i, rows in scored.items()
    }
    out: list[dict[str, Any]] = []
    stats = {"dropped_excluded": 0, "no_text": 0, "teacher": 0, "model": 0, "no_category": 0}
    for row in bank:
        risk_id = str(row["risk_id"])
        ipo_id = str(row.get("ipo_id") or ipo_of(risk_id))
        if ipo_id in excluded:
            stats["dropped_excluded"] += 1
            continue
        sc = by_ipo.get(ipo_id, {}).get(rid_of(risk_id), {})
        t = teacher.get(risk_id)
        cat: str | None
        band: int | None = None
        band_src: str | None = None
        if t is not None:
            cat, cat_src = str(t["category"]), "ai"
            band, band_src = min(int(t["seriousness_band"]), MAX_BAND), "ai"
            stats["teacher"] += 1
        else:
            pred = categories.get(risk_id)
            cat, cat_src = (str(pred[0]), "model") if pred else (None, None)  # type: ignore[assignment]
            stats["model" if pred else "no_category"] += 1
        text = sc.get("body")
        if not text:
            stats["no_text"] += 1
        out.append(
            {
                "risk_id": risk_id,
                "ipo_id": ipo_id,
                "company": row.get("company"),
                "year": row.get("year"),
                "doc_date": row.get("doc_date"),
                "split": row.get("split"),
                "title": row.get("title"),
                "text": text or None,
                "section": None,
                "page": sc.get("page_start"),
                "page_end": sc.get("page_end"),
                "category": cat,
                "severity_band": band,
                "severity_source": band_src,
                "rule_seriousness": sc.get("seriousness"),
                "label_source": cat_src,
            }
        )
    return out, stats


def with_ipo(
    rows: Iterable[Mapping[str, Any]], label_source: str, excluded: set[str], *, keep: bool = False
) -> tuple[list[dict[str, Any]], int]:
    """Rows with ``ipo_id`` and ``label_source`` added; excluded IPOs dropped unless ``keep``.

    ``keep`` is for evaluation-only sets (gold-150 comes from test-slice IPOs on purpose); those
    rows also get ``eval_only: true``.
    """
    out: list[dict[str, Any]] = []
    dropped = 0
    for row in rows:
        ipo_id = ipo_of(str(row["risk_id"]))
        bad = ipo_id in excluded
        if bad and not keep:
            dropped += 1
            continue
        new = dict(row)
        new["ipo_id"] = ipo_id
        new["label_source"] = label_source
        if keep:
            new["eval_only"] = bad
        out.append(new)
    return out, dropped


def five_things(scored: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """What the "Five things to know" card picked for each scored IPO (the M2 baseline)."""
    out: list[dict[str, Any]] = []
    for ipo_id in sorted(scored):
        rows = sorted(
            scored[ipo_id],
            key=lambda r: (-float(r.get("importance") or 0.0), int(r.get("order") or 0)),
        )
        for rank, r in enumerate(rows[:TOP_FIVE], start=1):
            out.append(
                {
                    "ipo_id": ipo_id,
                    "rank": rank,
                    "risk_id": f"{ipo_id}#{r['rid']}",
                    "title": r.get("title"),
                    "page": r.get("page_start"),
                    "importance": r.get("importance"),
                    "category": r.get("category"),
                    "method": FIVE_METHOD,
                    "label_source": "rule",
                }
            )
    return out


def write_jsonl_gz(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    """Write rows as gzip JSON lines, byte-deterministic (no mtime or name); return the count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
        for row in rows:
            gz.write((json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
            n += 1
    return n


def write_parquet(path: Path, rows: Sequence[Mapping[str, Any]]) -> int:
    """Write rows as a Parquet file; return the count."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(list(rows)), path, compression="zstd")
    return len(rows)
