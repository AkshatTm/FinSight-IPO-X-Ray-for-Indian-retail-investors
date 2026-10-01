"""E2 and E3: run each rung of the extractor ladder on gold v1 (05 sections 4-5, ADR-031).

    uv run --group ml python -m finsight.evaluate.run_gold --rung rules
    uv run --group ml python -m finsight.evaluate.run_gold --rung qa_pretrained
    uv run --group ml python -m finsight.evaluate.run_gold --rung qa_finetuned --seed 13

One row per (IPO, ladder field): the top candidate of the rung, read from the document the field
lives in, is compared with the gold value by normalized value match (NVM), exact match and token
F1 on the printed text. No candidate is "no answer" and matches only ``not_in_document``.

Two settings, because cover sentences are templated and rules read them almost perfectly:

- **full**: the extractor sees the whole document.
- **body_only**: pages 1-``COVER_PAGES`` (cover, summary) are blanked first. Scored only on rows
  whose gold value is still stated in the pages the extractor may read, so that "robust to other
  wordings" is not confused with "value is not there"; ``n`` is printed.

Rules are developed on the 3 dev IPOs, so dev scores can only be used to choose between rungs; the
headline is the 7 test IPOs (``evaluate.ladder``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.core.interfaces import Extractor
from finsight.core.schemas import (
    Candidate,
    DocType,
    FieldSpec,
    ListValue,
    ParsedDoc,
    Placeholder,
    Section,
    TextValue,
    Value,
)
from finsight.evaluate.metrics import exact_match, nvm, token_f1
from finsight.extract import (
    COVER_PAGES,
    SEEDS,
    FineTunedExtractor,
    QAExtractor,
    RawAnswer,
    RulesExtractor,
    load_fields,
)
from finsight.extract.qa_finetuned import MAX_ANSWER_TOKENS
from finsight.extract.qa_pretrained import Answerer, default_answerer
from finsight.extract.rules import pages_to_search
from finsight.ingest.registry import list_demo_ipos
from finsight.normalize import equal, parse_amount, parse_amounts
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.sections_stage import load_sections

SETTINGS = ("full", "body_only")
SPLITS = ("dev", "test")
RUNGS = ("rules", "qa_pretrained", "qa_finetuned")
GOLD_VERSION = "v1"
_MARKS = str.maketrans("", "", "^*#†‡")


def result_name(rung: str, seed: int | None = None) -> str:
    return f"qa_finetuned_seed{seed}" if rung == "qa_finetuned" else rung


# ----------------------------------------------------------------------------- gold rows


def _compact(text: str) -> str:
    return "".join(text.translate(_MARKS).split()).casefold()


def gold_value(row: dict[str, Any], field: FieldSpec) -> Value | None:
    """The typed gold value; None for ``not_in_document`` (the extractor should say nothing)."""
    if row["status"] == "not_in_document":
        return None
    raw = row["value_raw"]
    if row["status"] == "placeholder":
        value = parse_amount(raw)
        return value if isinstance(value, Placeholder) else Placeholder(raw=str(raw))
    if field.type == "text":
        return TextValue(text=raw)
    if field.type == "list":
        return ListValue(items=list(raw))
    amount = parse_amount(raw)
    assert amount is not None, f"gold value {raw!r} does not parse"
    return amount  # type: ignore[no-any-return]


def gold_text(row: dict[str, Any]) -> str:
    raw = row.get("value_raw")
    if row["status"] == "not_in_document" or raw is None:
        return ""
    return raw if isinstance(raw, str) else "; ".join(raw)


def ladder_rows(gold: list[dict[str, Any]], fields: list[FieldSpec]) -> list[dict[str, Any]]:
    """Gold rows of the ladder fields, read from the document each field lives in."""
    by_id = {f.id: f for f in fields if f.ladder}
    return [r for r in gold if r["field_id"] in by_id and r["doc"] == by_id[r["field_id"]].doc]


# ----------------------------------------------------------------------------- body-only


def mask_cover(doc: ParsedDoc, pages: int = COVER_PAGES) -> ParsedDoc:
    """A copy of the document with the text of the first ``pages`` pages blanked."""
    masked = [p.model_copy(update={"text": "", "words": []}) if p.number <= pages else p
              for p in doc.pages]  # fmt: skip
    return doc.model_copy(update={"pages": masked})


def stated_in_body(
    row: dict[str, Any], field: FieldSpec, masked: ParsedDoc, sections: list[Section]
) -> bool:
    """Is the gold value still on the pages the extractor may read once the cover is masked?"""
    if row["status"] == "not_in_document":
        return True  # nothing to find, so abstaining is still the right answer
    text = " ".join(
        " ".join(masked.pages[n - 1].text.split()) for n in pages_to_search(masked, sections, field)
    )
    if not text.strip():
        return False
    if field.type in ("text", "list"):
        items = [row["value_raw"]] if isinstance(row["value_raw"], str) else row["value_raw"]
        return all(_compact(i) in _compact(text) for i in items)
    spans = parse_amounts(text)
    if row["status"] == "placeholder":
        return any(isinstance(s.amount, Placeholder) for s in spans)
    gold = parse_amount(row["value_raw"])
    return gold is not None and any(s.amount.kind == gold.kind and equal(s.amount, gold)
                                    for s in spans)  # fmt: skip


# ----------------------------------------------------------------------------- running a rung

Make = Callable[[], Extractor]


def cached(answerer: Answerer) -> Answerer:
    """Remember answers by (question, passage): body-only re-reads the same pages for free."""
    memo: dict[tuple[str, str], RawAnswer | None] = {}

    def answer(question: str, contexts: list[str]) -> list[RawAnswer | None]:
        todo = [c for c in dict.fromkeys(contexts) if (question, c) not in memo]
        for context, found in zip(todo, answerer(question, todo) if todo else [], strict=True):
            memo[(question, context)] = found
        return [memo[(question, c)] for c in contexts]

    return answer


def make_extractor(
    rung: str, seed: int | None = None, answerer: Answerer | None = None
) -> Extractor:
    if rung == "rules":
        return RulesExtractor()
    if rung == "qa_pretrained":
        base = answerer or default_answerer(max_answer_tokens=MAX_ANSWER_TOKENS)
        return QAExtractor(answerer=cached(base))
    if rung == "qa_finetuned":
        assert seed is not None
        return FineTunedExtractor(seed, answerer=answerer and cached(answerer))
    raise ValueError(f"unknown rung {rung!r}")


def _asked(extractor: Extractor, field: FieldSpec) -> FieldSpec:
    """The field as if it named this extractor, so a QA rung runs on every ladder field."""
    return field.model_copy(update={"fallback": getattr(extractor, "name", field.fallback)})


def top_candidate(
    extractor: Extractor, doc: ParsedDoc, sections: list[Section], field: FieldSpec
) -> Candidate | None:
    found = extractor.extract(doc, sections, [], _asked(extractor, field))
    return found[0] if found else None


def _prediction(cand: Candidate | None, gold: Value | None, row: dict[str, Any]) -> dict[str, Any]:
    pred_text = cand.raw if cand else ""
    return {
        "pred_raw": pred_text,
        "pred_page": cand.page if cand else None,
        "pred_score": cand.score if cand else None,
        "nvm": nvm(cand.value if cand else None, gold),
        "em": exact_match(pred_text, gold_text(row)),
        "f1": round(token_f1(pred_text, gold_text(row)), 4),
    }


def run_document(
    extractor: Extractor,
    rows: list[dict[str, Any]],
    fields: dict[str, FieldSpec],
    doc: ParsedDoc,
    sections: list[Section],
) -> list[dict[str, Any]]:
    """Both settings for the gold rows of one document."""
    masked = mask_cover(doc)
    out = []
    for row in rows:
        field = fields[row["field_id"]]
        gold = gold_value(row, field)
        full = top_candidate(extractor, doc, sections, field)
        in_body = stated_in_body(row, field, masked, sections)
        body = top_candidate(extractor, masked, sections, field) if in_body else None
        out.append(
            {
                "ipo_id": row["ipo_id"],
                "field_id": row["field_id"],
                "doc": row["doc"],
                "status": row["status"],
                "gold": gold_text(row),
                "full": _prediction(full, gold, row),
                "in_body": in_body,
                "body_only": _prediction(body, gold, row) if in_body else None,
            }
        )
    return out


# ----------------------------------------------------------------------------- summary


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _scores(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(items),
        "nvm": _mean([float(i["nvm"]) for i in items]),
        "em": _mean([float(i["em"]) for i in items]),
        "f1": _mean([i["f1"] for i in items]),
        "coverage": _mean([float(bool(i["pred_raw"])) for i in items]),
    }


def summarise(predictions: list[dict[str, Any]], splits: dict[str, str]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    per_field: dict[str, Any] = {}
    for split in SPLITS:
        rows = [p for p in predictions if splits[p["ipo_id"]] == split]
        metrics[split] = {
            "full": _scores([r["full"] for r in rows]),
            "body_only": _scores([r["body_only"] for r in rows if r["in_body"]]),
        }
        per_field[split] = {
            fid: {
                "full": _scores([r["full"] for r in rows if r["field_id"] == fid]),
                "body_only": _scores(
                    [r["body_only"] for r in rows if r["field_id"] == fid and r["in_body"]]
                ),
            }
            for fid in sorted({r["field_id"] for r in rows})
        }
    return {"metrics": metrics, "per_field": per_field}


def _git_sha() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, check=True)  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def _split_ids(predictions: list[dict[str, Any]], splits: dict[str, str]) -> dict[str, list[str]]:
    ids = {p["ipo_id"] for p in predictions}
    return {s: sorted(i for i in ids if splits[i] == s) for s in SPLITS}


def report(
    rung: str, seed: int | None, predictions: list[dict[str, Any]], splits: dict[str, str]
) -> dict[str, Any]:
    experiment = "E2" if rung == "rules" else "E3"
    return {
        "experiment": experiment,
        "name": result_name(rung, seed),
        "rung": rung,
        "seed": seed,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "data": {
            "gold_version": GOLD_VERSION,
            "n_ipos": len({p["ipo_id"] for p in predictions}),
            "n_values": len(predictions),
            "splits": _split_ids(predictions, splits),
            "cover_pages_masked": COVER_PAGES,
            "max_answer_tokens": MAX_ANSWER_TOKENS if rung != "rules" else None,
        },
        **summarise(predictions, splits),
        "notes": (
            "NVM = normalized value match of the top candidate against gold. body_only blanks "
            f"pages 1-{COVER_PAGES} and is scored on rows whose gold value is still stated in the "
            "searched pages. Choose rungs on dev, quote test (ADR-031, ADR-018)."
        ),
        "predictions": predictions,
    }


def run_rung(
    rung: str,
    seed: int | None = None,
    ipo_ids: list[str] | None = None,
    answerer: Answerer | None = None,
    gold: list[dict[str, Any]] | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    paths = get_settings().paths
    fields = {f.id: f for f in load_fields()}
    ipos = [i for i in list_demo_ipos() if ipo_ids is None or i.ipo_id in ipo_ids]
    splits = {i.ipo_id: i.split for i in ipos}
    if gold is None:
        text = (Path(paths.gold_dir) / "gold_values.jsonl").read_text(encoding="utf-8")
        gold = [json.loads(x) for x in text.splitlines() if x.strip()]
    rows = ladder_rows([r for r in gold if r["ipo_id"] in splits], list(fields.values()))
    extractor = make_extractor(rung, seed, answerer)
    predictions: list[dict[str, Any]] = []
    for ipo in ipos:
        for doc_type in ("rhp", "prospectus"):
            mine = [r for r in rows if r["ipo_id"] == ipo.ipo_id and r["doc"] == doc_type]
            if not mine:
                continue
            doc = _load_doc(paths.processed_dir, ipo.ipo_id, doc_type)  # type: ignore[arg-type]
            sections = load_sections(paths.processed_dir, ipo.ipo_id, doc_type)  # type: ignore[arg-type]
            done = run_document(extractor, mine, fields, doc, sections)
            predictions += done
            hit = sum(p["full"]["nvm"] for p in done)
            log(f"{result_name(rung, seed):22} {ipo.ipo_id:28} {doc_type:10} NVM {hit}/{len(done)}")
    return report(rung, seed, predictions, splits)


def _load_doc(processed_dir: Path, ipo_id: str, doc: DocType) -> ParsedDoc:
    return ParsedDoc.model_validate_json(
        doc_outputs(processed_dir, ipo_id, doc).parsed.read_text(encoding="utf-8")
    )


def write_result(result: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result['name']}.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                    newline="\n")  # fmt: skip
    return path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.evaluate.run_gold")
    parser.add_argument("--rung", choices=(*RUNGS, "all"), required=True)
    parser.add_argument("--seed", type=int, choices=SEEDS, help="fine-tuned rung only")
    parser.add_argument("--ipo", action="append", help="limit to these IPOs (no file is written)")
    args = parser.parse_args(argv)
    jobs: list[tuple[str, int | None]] = []
    for rung in RUNGS if args.rung == "all" else (args.rung,):
        if rung == "qa_finetuned":
            jobs += [(rung, s) for s in ([args.seed] if args.seed else SEEDS)]
        else:
            jobs.append((rung, None))
    out_dir = Path(get_settings().paths.eval_dir) / "ladder"
    for rung, seed in jobs:
        result = run_rung(rung, seed, args.ipo)
        for split in SPLITS:
            for setting in SETTINGS:
                m = result["metrics"][split][setting]
                print(f"  {result['name']:22} {split:5} {setting:10} n={m['n']:3} NVM={m['nvm']}"
                      f" EM={m['em']} F1={m['f1']}")  # fmt: skip
        if args.ipo is None:
            print(f"wrote {write_result(result, out_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
