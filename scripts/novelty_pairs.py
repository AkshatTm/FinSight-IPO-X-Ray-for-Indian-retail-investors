"""Novelty threshold (C2.6, E22): blind pair sheet, then score the ratings.

    uv run python scripts/novelty_pairs.py sheet      # dev risks vs their reference window
    # ... rate data/gold/novelty_pairs.csv: column same_risk = yes / no / unsure (not the key!) ...
    uv run python scripts/novelty_pairs.py score      # -> eval_results/b/novelty.json

Needs the bank built by ``scripts/build_risk_bank.py``. Only ``dev`` IPOs are queried; the
reference window of each is cut with ``finsight.splits.reference_bank`` (``kind="eval"``: no test
or bench IPO is ever a neighbour). The similarity is kept in a separate key file so the rating is
blind. The rule that picks tau is in ``finsight.risks.novelty_tau.RULE``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from finsight.risks.bank import company_key, load_bank, risks_config  # noqa: E402
from finsight.risks.bank_build import write_json  # noqa: E402
from finsight.risks.novelty_tau import (  # noqa: E402
    Pair,
    nearest_other,
    read_ratings,
    result,
    sample_pairs,
    write_sheet,
)
from finsight.splits import load_splits, reference_bank  # noqa: E402

BANK = ROOT / "data" / "processed" / "risk_bank" / "risk_bank.parquet"
SHEET = ROOT / "data" / "gold" / "novelty_pairs.csv"
KEY = ROOT / "data" / "processed" / "risk_bank" / "novelty_pairs_key.json"
RESULT = ROOT / "eval_results" / "b" / "novelty.json"


def parquet_columns(path: Path) -> dict[str, list]:
    """``risk_id`` and ``split`` (the bank class does not keep them)."""
    import pyarrow.parquet as pq

    t = pq.read_table(path, columns=["risk_id", "split"])
    return {"risk_id": t.column("risk_id").to_pylist(), "split": t.column("split").to_pylist()}


def collect_pairs(bank, extra, splits, source, per_ipo_cap: int = 60) -> list[Pair]:  # type: ignore[no-untyped-def]
    """Nearest past risk of another company for the risks of every ``dev`` IPO."""
    ids = np.array(bank.ipo_ids)
    out: list[Pair] = []
    for e in splits.ipos:
        if e.slice != "dev" or e.doc_date is None:
            continue
        ref = reference_bank(
            bank, splits, e.doc_date, kind="eval", exclude_ipo=e.ipo_id, exclude_company=e.company
        )
        q_rows = np.flatnonzero((ids == e.ipo_id) & (np.array(extra["split"]) == "dev"))[
            :per_ipo_cap
        ]
        r_rows = np.flatnonzero(np.isin(ids, sorted(set(ref.ipo_ids or []))))
        if len(q_rows) == 0 or len(r_rows) == 0:
            continue
        own = {r.rid: r for r in source(e) or []}
        keys = [company_key(bank.companies[i]) for i in r_rows]
        for qi, (j, sim) in zip(
            q_rows,
            nearest_other(bank.vectors[q_rows], bank.vectors[r_rows], keys, company_key(e.company)),
            strict=False,
        ):
            rid = extra["risk_id"][qi].split("#", 1)[1]
            ref_i = r_rows[j]
            ref_entry = next((x for x in splits.ipos if x.ipo_id == bank.ipo_ids[ref_i]), None)
            ref_risks = (source(ref_entry) or []) if ref_entry else []
            ref_risk = next((r for r in ref_risks if r.title == bank.titles[ref_i]), None)
            mine = own.get(rid)
            out.append(
                Pair(extra["risk_id"][qi], bank.ipo_ids[ref_i], bank.titles[ref_i], sim,
                     a_company=e.company, a_title=bank.titles[qi],
                     a_text=(mine.body if mine else "")[:900], b_company=bank.companies[ref_i],
                     b_text=(ref_risk.body if ref_risk else "")[:900])
            )  # fmt: skip
    return out


def cmd_sheet() -> None:
    """Write the blind sheet and the key."""
    from build_risk_bank import make_source

    splits = load_splits(ROOT / "configs" / "splits.yaml")
    bank = load_bank(BANK, years=None)
    pairs = collect_pairs(bank, parquet_columns(BANK), splits, make_source(splits))
    picked = sample_pairs(pairs, 100)
    write_sheet(picked, SHEET, KEY)
    print(
        f"{len(pairs)} candidate pairs; wrote {len(picked)} to {SHEET} (key: {KEY.name}, do not open)"
    )


def cmd_score() -> None:
    """Score the rated sheet and write the E22 record."""
    placeholder = float(risks_config()["novelty"]["tau"])
    res = result(read_ratings(SHEET, KEY), placeholder)
    write_json(RESULT, res)
    print(json.dumps({k: res[k] for k in ("tau", "n_rated") if k in res}), "->", RESULT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["sheet", "score"])
    {"sheet": cmd_sheet, "score": cmd_score}[ap.parse_args(argv).command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
