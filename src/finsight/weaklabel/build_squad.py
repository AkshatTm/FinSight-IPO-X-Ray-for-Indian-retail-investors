"""Corpus -> SQuAD 2.0 JSONL (train/dev split by IPO) plus the dataset card numbers.

Every example keeps its IPO id so the split can be made by IPO: no company appears in both
train and dev, and no demo or gold-v2 company appears at all (checked twice: when a document is
read and again before writing).
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from finsight.core.schemas import Page, ParsedDoc
from finsight.extract import get_field
from finsight.ingest.corpus import CorpusDoc, load_corpus_doc
from finsight.ingest.exclusion import is_excluded
from finsight.weaklabel.negatives import negatives
from finsight.weaklabel.propagate import Example, propagate
from finsight.weaklabel.seeds import LADDER_FIELDS, excel_values, find_seeds

SPLIT_SEED = 2026
# Older PDFs draw ₹ with a font that extracts as a backtick, and lose the ● inside [●].
_RUPEE_GLYPH = re.compile(r"`(?=\s?\d)")
_EMPTY_BLANK = re.compile(r"\[\s*\]")


def clean_text(text: str) -> str:
    """Corpus text with the rupee glyph and blank markers restored (demo PDFs print them)."""
    return _EMPTY_BLANK.sub("[●]", _RUPEE_GLYPH.sub("₹", text))


DEV_SHARE = 0.1


def to_squad(example: Example, question: str) -> dict[str, Any]:
    """One SQuAD 2.0 record (Hugging Face ``squad_v2`` layout); no answer = empty lists."""
    answers: dict[str, list[Any]] = {"text": [], "answer_start": []}
    if not example.is_impossible:
        answers = {"text": [example.answer_text], "answer_start": [example.answer_start]}
    return {
        "id": example.id,
        "ipo_id": example.ipo_id,
        "field_id": example.field_id,
        "title": example.ipo_id,
        "question": question,
        "context": example.context,
        "answers": answers,
    }


def split_by_ipo(ipo_ids: list[str], dev_share: float = DEV_SHARE) -> tuple[set[str], set[str]]:
    """Train and dev IPO sets; the same input set always gives the same split."""
    ordered = sorted(set(ipo_ids))
    random.Random(SPLIT_SEED).shuffle(ordered)
    n_dev = round(len(ordered) * dev_share)
    return set(ordered[n_dev:]), set(ordered[:n_dev])


def _parsed(doc: CorpusDoc) -> ParsedDoc:
    pages = [
        Page(
            number=p.number,
            width=0,
            height=0,
            words=[],
            text=clean_text(p.text),
            is_scanned=False,
        )
        for p in doc.pages
    ]
    return ParsedDoc(
        ipo_id=doc.ipo_id, doc_type=doc.doc_kind, source_path=doc.source_file,
        n_pages=len(pages), pages=pages, sha256="",
    )  # fmt: skip


def build_dataset(
    corpus_dir: Path,
    out_dir: Path,
    excel: Mapping[str, Mapping[str, str | None]],
    excluded: list[str],
) -> dict[str, Any]:
    """Write ``train.jsonl`` and ``dev.jsonl`` to ``out_dir``; return the dataset card."""
    by_ipo: dict[str, list[dict[str, Any]]] = {}
    excluded_ipos: list[str] = []
    seeded: Counter[str] = Counter()
    dropped: dict[str, Counter[str]] = {f: Counter() for f in LADDER_FIELDS}
    excel_agree: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    n_docs = 0
    for path in sorted(corpus_dir.glob("*.json")):
        doc = load_corpus_doc(path)
        if is_excluded(doc.company, excluded):
            excluded_ipos.append(doc.ipo_id)
            continue
        n_docs += 1
        kinds[doc.doc_kind] += 1
        parsed = _parsed(doc)
        report = find_seeds(parsed, doc.sections, excel_values(excel.get(doc.mapping_key, {})))
        for field_id, reason in report.dropped.items():
            dropped[field_id][reason] += 1
        rows: list[dict[str, Any]] = []
        for field_id, seed in report.seeds.items():
            seeded[field_id] += 1
            excel_agree[field_id] += seed.excel == "agree"
            spec = get_field(field_id)
            pos = propagate(parsed, doc.sections, spec, seed)
            neg = negatives(parsed, doc.sections, spec, seed, pos)
            for k, example in enumerate(pos + neg):
                question = spec.questions[k % len(spec.questions)]
                rows.append(to_squad(example, question))
        if rows:
            by_ipo[doc.ipo_id] = rows

    train_ipos, dev_ipos = split_by_ipo(list(by_ipo))
    out_dir.mkdir(parents=True, exist_ok=True)
    card: dict[str, Any] = {
        "n_ipos": n_docs,
        "by_doc_kind": dict(sorted(kinds.items())),
        "excluded_ipos": sorted(excluded_ipos),
        "seed_coverage": {f: f"{seeded[f]}/{n_docs}" for f in LADDER_FIELDS},
        "seed_dropped": {f: dict(sorted(c.items())) for f, c in dropped.items()},
        "seed_agrees_with_excel": {f: excel_agree[f] for f in LADDER_FIELDS},
        "split_seed": SPLIT_SEED,
    }
    all_rows: list[dict[str, Any]] = []
    for name, ipos in (("train", train_ipos), ("dev", dev_ipos)):
        rows = [r for ipo in sorted(ipos) for r in by_ipo[ipo]]
        assert not any(r["ipo_id"] in excluded_ipos for r in rows), "demo/gold IPO leaked"
        with (out_dir / f"{name}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        card[name] = {
            "ipos": len(ipos),
            "examples": len(rows),
            "positives": sum(bool(r["answers"]["text"]) for r in rows),
        }
        all_rows += rows
    card["per_field"] = {
        f: {
            "positives": sum(r["field_id"] == f and bool(r["answers"]["text"]) for r in all_rows),
            "negatives": sum(r["field_id"] == f and not r["answers"]["text"] for r in all_rows),
            "ipos": len({r["ipo_id"] for r in all_rows if r["field_id"] == f}),
        }
        for f in LADDER_FIELDS
    }
    lengths = [len(r["context"]) for r in all_rows]
    card["avg_context_chars"] = round(sum(lengths) / len(lengths)) if lengths else 0
    return card
