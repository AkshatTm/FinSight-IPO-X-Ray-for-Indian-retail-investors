"""Smoke test for retrieval before the real question sets exist.

Uses the field questions in ``configs/fields.yaml`` as queries and the gold value of each present
field as the target: does the top-5 contain a passage that states the value (or sits on the gold
page of the right document)? This is a
sanity check on the index (tables, ids, tokenizer), not E6: the questions are templated and the
gold covers 10 IPOs, so nothing here is tuned or reported as a result.

    uv run python scripts/retrieval_field_smoke.py [--dense]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from finsight.core.config import get_settings
from finsight.extract import load_fields
from finsight.retrieve import Retriever
from finsight.retrieve.evaluate import compact

_NOISE = ("₹", "MILLION", "EQUITY SHARES", "CRORE")


def needle(value: object) -> str:
    """The part of a gold value worth searching for: first list item, no unit words."""
    while isinstance(value, list):
        value = value[0]
    text = str(value)
    for noise in _NOISE:
        text = text.replace(noise, "")
    return compact(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dense", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    embedder = None
    if args.dense:
        from finsight.retrieve import BgeM3Embedder

        embedder = BgeM3Embedder()
    retriever = Retriever(settings.paths.processed_dir, embedder=embedder)
    gold = [
        json.loads(x)
        for x in (settings.paths.data_dir / "gold" / "gold_values.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if x.strip()
    ]
    questions = {f.id: f.questions for f in load_fields()}
    per_field: dict[str, list[int]] = defaultdict(list)
    for row in gold:
        if row["status"] != "present" or row["page"] is None:
            continue
        hit = 0
        for question in questions[row["field_id"]]:
            result = retriever.search(question, row["ipo_id"], top_k=5)
            hit = max(
                hit,
                int(
                    any(
                        h.passage.doc_type == row["doc"]
                        and (
                            h.passage.page_start <= row["page"] <= h.passage.page_end
                            or needle(row["value_raw"]) in compact(h.passage.text)
                        )
                        for h in result.hits
                    )
                ),
            )
        per_field[row["field_id"]].append(hit)
    for field_id, hits in sorted(per_field.items()):
        print(f"{field_id:24} recall@5 {sum(hits)}/{len(hits)}")
    total = [h for v in per_field.values() for h in v]
    print(f"{'all':24} recall@5 {sum(total)}/{len(total)}  (method: {result.method})")


if __name__ == "__main__":
    main()
