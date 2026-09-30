"""Negatives: passages from the same sections that do not hold the value ("no answer").

SQuAD 2.0 models must also learn to say "not here". For every positive we add one or two
passages from the field's sections where the seed value is absent, chosen with a fixed random
seed so the dataset is reproducible.
"""

from __future__ import annotations

import random

from finsight.core.schemas import FieldSpec, ParsedDoc, Section
from finsight.extract import build_passages
from finsight.weaklabel.propagate import Example, find_answer
from finsight.weaklabel.seeds import Seed

SEED = 2026
MIN_RATIO, MAX_RATIO = 1, 2


def negatives(
    doc: ParsedDoc,
    sections: list[Section],
    field: FieldSpec,
    seed: Seed,
    positives: list[Example],
) -> list[Example]:
    if not positives:
        return []
    used = {p.passage_id for p in positives}
    pool = [
        p for p in build_passages(doc, sections, field)
        if p.id not in used and find_answer(field, seed.value, p.text) is None
    ]  # fmt: skip
    rng = random.Random(f"{doc.ipo_id}:{field.id}:{SEED}")
    want = sum(rng.randint(MIN_RATIO, MAX_RATIO) for _ in positives)
    chosen = sorted(rng.sample(pool, min(want, len(pool))), key=lambda p: p.id)
    return [
        Example(
            id=f"{p.id}:{field.id}:neg",
            ipo_id=doc.ipo_id,
            field_id=field.id,
            passage_id=p.id,
            page=p.page,
            context=p.text,
            answer_text="",
            answer_start=-1,
            is_impossible=True,
        )
        for p in chosen
    ]
