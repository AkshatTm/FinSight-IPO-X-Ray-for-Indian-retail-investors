"""Which IPOs ARGON may train on (C-ADR-02, stricter rule confirmed by Akshat for Phase 4).

``excluded_ipos`` = every test-slice IPO + SME/unusable IPOs + demo and showcase IPOs + the Bench v1
IPOs + every Platform Bench IPO (Jio included). Nothing in it enters training data, thresholds,
prompts or parser tuning. ``splits_by_ipo`` is the frozen Phase 3 split with those roles added.
"""

from __future__ import annotations

from typing import Any

RULE = (
    "C-ADR-02 (strict): all test-slice IPOs, SME/unusable IPOs, demo + showcase IPOs, "
    "Bench v1 IPOs "
    "and Platform Bench IPOs never enter training data, thresholds, prompts or parser tuning."
)


def _ids(items: Any) -> list[str]:
    """Ids from a list of strings or of ``{"ipo_id": ...}`` mappings."""
    out: list[str] = []
    for item in items or []:
        out.append(str(item["ipo_id"] if isinstance(item, dict) else item))
    return out


def excluded_ipos(
    splits: dict[str, Any],
    demo_ids: list[str],
    bench_v1_ids: list[str],
    platform_ids: list[str],
) -> dict[str, Any]:
    """``{"rule", "ipos": {ipo_id: {"reasons": [...], "company_key": str | None}}}``.

    Args:
        splits: Parsed ``configs/splits.yaml``.
        demo_ids: Showcase ids from ``configs/demo_ipos.yaml``.
        bench_v1_ids: IPO ids of ``bench/v1/manifest.yaml``.
        platform_ids: Normalised Platform Bench ids.
    """
    keys = {str(r["ipo_id"]): r.get("company_key") for r in splits.get("ipos", [])}
    reasons: dict[str, list[str]] = {}

    def add(ipo_id: str, reason: str) -> None:
        bucket = reasons.setdefault(ipo_id, [])
        if reason not in bucket:
            bucket.append(reason)

    for row in splits.get("ipos", []):
        if row.get("slice") == "test":
            add(str(row["ipo_id"]), "test_slice")
    for row in splits.get("excluded", []):
        add(str(row["ipo_id"]), "excluded_by_splits")
    for i in _ids(splits.get("demo")):
        add(i, "demo_newest")
    for i in _ids(splits.get("bench")):
        add(i, "bench")
    for i in _ids(splits.get("bench_dev")):
        add(i, "bench_dev")
    for i in demo_ids:
        add(i, "showcase_demo")
    for i in bench_v1_ids:
        add(i, "bench_v1")
    for i in platform_ids:
        add(i, "platform_bench")
    ipos = {
        i: {"reasons": sorted(r), "company_key": keys.get(i)} for i, r in sorted(reasons.items())
    }
    return {"rule": RULE, "n": len(ipos), "ipos": ipos}


def splits_by_ipo(splits: dict[str, Any], excluded: dict[str, Any]) -> dict[str, Any]:
    """The Phase 3 split, one row per IPO, with ``excluded`` and its reasons."""
    bad = excluded["ipos"]
    rows: list[dict[str, Any]] = []
    for row in splits.get("ipos", []):
        ipo_id = str(row["ipo_id"])
        rows.append(
            {
                "ipo_id": ipo_id,
                "company_key": row.get("company_key"),
                "slice": row.get("slice"),
                "source": row.get("source"),
                "doc_date": row.get("doc_date"),
                "close_year": row.get("close_year"),
                "excluded": ipo_id in bad,
                "reasons": bad.get(ipo_id, {}).get("reasons", []),
            }
        )
    for row in splits.get("excluded", []):
        ipo_id = str(row["ipo_id"])
        rows.append(
            {
                "ipo_id": ipo_id,
                "company_key": None,
                "slice": "excluded",
                "source": None,
                "doc_date": None,
                "close_year": None,
                "excluded": True,
                "reasons": bad.get(ipo_id, {}).get("reasons", ["excluded_by_splits"]),
            }
        )
    trainable = [r["ipo_id"] for r in rows if not r["excluded"] and r["slice"] == "train"]
    dev = [r["ipo_id"] for r in rows if not r["excluded"] and r["slice"] == "dev"]
    return {
        "version": splits.get("version"),
        "train_cut": splits.get("train_cut"),
        "rule": RULE,
        "counts": {"train": len(trainable), "dev": len(dev), "excluded": len(bad)},
        "ipos": rows,
    }
