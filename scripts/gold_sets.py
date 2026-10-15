"""Test-slice gold sets: category gold-150 (C2.4) and simplification gold-50 (C2.5).

    uv run python scripts/gold_sets.py sample        # 150 + 50 test risks -> gold_eval_risks.jsonl
    uv run python scripts/gpu_jobs.py push gold_eval # Colab PRESET gold_eval (teacher + Qwen3.8)
    uv run python scripts/gpu_jobs.py pull gold_eval
    uv run python scripts/gold_sets.py sheet150      # data/gold/gold150_sheet.csv (pre-filled)
    # ... Akshat verifies the category column ...
    uv run python scripts/gold_sets.py gold150       # -> data/gold/gold150.jsonl (classify --gold)
    uv run python scripts/gold_sets.py generate --system base --backend ollama --model <tag>
    uv run python scripts/gold_sets.py generate --system student --backend llama-cpp --model <gguf>
    uv run python scripts/gold_sets.py sheet50       # blind data/gold/simplify_gold50_sheet.csv
    # ... Akshat rates faithful + plain_english_1to5 ...
    uv run python scripts/gold_sets.py score50       # -> eval_results/c/simplify_gold50.json

Risk text and model outputs stay in ``data/processed/gold_eval/`` (gitignored); the sheets Akshat
edits are in ``data/gold/``. Keys (pre-fill source, which system wrote which row) stay in
``data/processed/gold_eval/``: do not open them before rating. Test risks never train or tune
anything (C-ADR-02).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from finsight.risks.gold_sets import (  # noqa: E402
    CATEGORY_COLUMNS,
    GOLD50,
    GOLD150,
    REWRITE_COLUMNS,
    agreement,
    category_gold,
    category_sheet,
    pick,
    read_csv,
    rewrite_sheet,
    score_rewrites,
    write_csv,
)
from finsight.risks.teacher import CATEGORIES, TeacherOutput, parse_output  # noqa: E402
from finsight.risks.teacher_cleanup import (  # noqa: E402
    load_rules,
    remap_category,
    remap_version,
    seriousness_band,
)
from finsight.risks.teacher_input import Candidate  # noqa: E402
from finsight.risks.teacher_run import read_jsonl  # noqa: E402

DIR = ROOT / "data" / "processed" / "gold_eval"
GOLD = ROOT / "data" / "gold"
RISKS = DIR / "gold_eval_risks.jsonl"
SET150, SET50 = DIR / "gold150_risks.jsonl", DIR / "gold50_risks.jsonl"
SHEET150, PREFILL = GOLD / "gold150_sheet.csv", DIR / "gold150_prefill.json"
GOLD150_OUT = GOLD / "gold150.jsonl"
SHEET50, KEY50 = GOLD / "simplify_gold50_sheet.csv", DIR / "simplify_gold50_key.json"
RESULT150 = ROOT / "eval_results" / "c" / "gold150_verification.json"
RESULT50 = ROOT / "eval_results" / "c" / "simplify_gold50.json"
PREFILL_MODEL = "qwen3.8-27b-fp8"  # bake-off runner-up: not the classifier's own teacher
TEACHER_MODEL = "gemma-4-31b-it"


def _write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _load(path: Path) -> list[Candidate]:
    keys = ("risk_id", "ipo_id", "company", "year", "title", "body")
    return [Candidate(*(r[k] for k in keys)) for r in read_jsonl(path)]


def _dump(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                    newline="\n")  # fmt: skip


def cmd_sample(_: argparse.Namespace) -> None:
    """Pick gold-150 and gold-50 from disjoint test IPOs and write the manifest (kind eval)."""
    from build_risk_bank import make_source

    from finsight.splits import Manifest, file_sha256, load_splits, write_manifest

    splits = load_splits(ROOT / "configs" / "splits.yaml")
    source = make_source(splits)
    by_ipo: dict[str, list[Candidate]] = {}
    for e in splits.ipos:
        if e.slice != "test":
            continue  # gold sets are test-slice only; never bench
        year = int((e.doc_date.year if e.doc_date else e.close_year) or 0)
        by_ipo[e.ipo_id] = [Candidate(f"{e.ipo_id}#{r.rid}", e.ipo_id, e.company, year, r.title,
                                      r.body) for r in source(e) or []]  # fmt: skip
    g150 = pick(by_ipo, *GOLD150)
    g50 = pick(by_ipo, *GOLD50, exclude_ipos={c.ipo_id for c in g150})
    _write_jsonl([c.as_row() for c in g150], SET150)
    _write_jsonl([c.as_row() for c in g50], SET50)
    _write_jsonl([c.as_row() for c in g150 + g50], RISKS)
    ipos = sorted({c.ipo_id for c in g150 + g50})
    write_manifest(
        Manifest(artefact="gold_eval_risks", kind="eval", ipo_ids=ipos, sha256=file_sha256(RISKS),
                 written_by="scripts/gold_sets.py",
                 note="gold-150 (15 x 10 test IPOs) + gold-50 (5 x 10 other test IPOs)"),
        ROOT / "data" / "manifests",
    )  # fmt: skip
    print(f"gold-150 {len(g150)} risks, gold-50 {len(g50)} risks, {len(ipos)} test IPOs -> {RISKS}")


def _raw(model: str) -> dict[str, str]:
    path = DIR / f"raw_{model}.jsonl"
    if not path.exists():
        sys.exit(f"missing {path}: run the gold_eval Colab job and pull it first")
    return {str(r["risk_id"]): str(r["raw"]) for r in read_jsonl(path)}


def cmd_sheet150(a: argparse.Namespace) -> None:
    """The verification sheet with the category pre-filled by ``--prefill``'s answers."""
    prefill: dict[str, str] = {}
    for rid, raw in _raw(a.prefill).items():
        with contextlib.suppress(ValueError):  # unparsable: left blank for Akshat
            prefill[rid] = parse_output(raw).category
    risks = _load(SET150)
    write_csv(category_sheet(risks, prefill), CATEGORY_COLUMNS, SHEET150)
    _dump({"source": a.prefill, "prefill": {c.risk_id: prefill.get(c.risk_id, "") for c in risks}},
          PREFILL)  # fmt: skip
    blank = sum(not prefill.get(c.risk_id) for c in risks)
    print(
        f"wrote {len(risks)} rows ({blank} blank) -> {SHEET150}; categories: {', '.join(CATEGORIES)}"
    )


def _parsed(model: str, ids: set[str]) -> dict[str, TeacherOutput]:
    out = {}
    for rid, raw in _raw(model).items():
        if rid in ids:
            with contextlib.suppress(ValueError):
                out[rid] = parse_output(raw)
    return out


def cmd_gold150(_: argparse.Namespace) -> None:
    """Verified sheet -> ``data/gold/gold150.jsonl`` (category gold + the teacher's seriousness
    band as ``band``), the change count and the agreement of the pre-fill, the raw teacher and
    the remapped teacher with the gold categories."""
    key = json.loads(PREFILL.read_text(encoding="utf-8"))
    rated = read_csv(SHEET150)
    ids = {r["risk_id"] for r in rated}
    teacher = _parsed(TEACHER_MODEL, ids)
    bands = {rid: seriousness_band(o.seriousness_1to5) for rid, o in teacher.items()}
    rows, stats = category_gold(rated, key["prefill"], CATEGORIES, bands)
    _write_jsonl(rows, GOLD150_OUT)
    gold = {r["risk_id"]: r["label"] for r in rows}
    rules = load_rules()
    remapped = {r["risk_id"]: remap_category(r["title"], r["text"], teacher[r["risk_id"]].category,
                                             rules)[0]
                for r in rated if r["risk_id"] in teacher}  # fmt: skip
    prefill = {k: v for k, v in key["prefill"].items() if v}
    agree = {
        f"prefill:{key['source']}": agreement(gold, prefill, CATEGORIES),
        f"teacher_raw:{TEACHER_MODEL}": agreement(
            gold, {k: o.category for k, o in teacher.items()}, CATEGORIES
        ),
        f"teacher_remapped:{TEACHER_MODEL}+{remap_version()}": agreement(
            gold, remapped, CATEGORIES
        ),
    }
    _dump({**stats, "prefill_source": key["source"],
           "label_source": "human:akshat (verified a model pre-fill)",
           "band_source": f"teacher:{TEACHER_MODEL} (no human seriousness label on gold-150)",
           "band_counts": dict(sorted(Counter(r["band"] for r in rows).items(), key=str)),
           "agreement_with_gold": agree,
           "test_informed": "remap-v2 rules were tightened after the gold-150 review (C2.3b), so "
                            "the remapped-teacher agreement and classifier scores on gold-150 are "
                            "test-informed"}, RESULT150)  # fmt: skip
    print(json.dumps(stats), "->", GOLD150_OUT)
    for name, a in agree.items():
        print(f"{name}: {a['share']:.1%} ({a['agree']}/{a['n']})")


def cmd_generate(a: argparse.Namespace) -> None:
    """gold-50 rewrites from a local model (``base`` zero-shot or the ``student``).

    Same prompt and cleaning as the product (``simplify``); the cleaned text is kept even when a
    post-check fails, with the failure in ``check``, so it can still be rated.
    """
    from finsight.generate import LLMUnavailable
    from finsight.risks.simplify import Simplifier, _backend

    simp = Simplifier(_backend(a.backend, a.model, ROOT / "models"), a.model)
    out = []
    for c in _load(SET50):
        text, check = "", "unavailable"
        for _ in range(2):  # one retry on a timeout
            try:
                text, check = simp.draft(c.title, c.body)
                break
            except LLMUnavailable as err:
                print(c.risk_id, "unavailable:", str(err)[:80], flush=True)
        out.append({"risk_id": c.risk_id, "system": a.system, "model": a.model, "text": text,
                    "check": check})  # fmt: skip
        print(c.risk_id, check or "passed", flush=True)
    _write_jsonl(out, DIR / f"rewrites_{a.system}.jsonl")


def _check(c: Candidate, text: str) -> str:
    """The product's post-check on a rewrite: ``""`` when it passes, else the reason."""
    from finsight.risks.simplify import post_check

    original = f"{c.title}\n\n{c.body}" if c.title.strip() else c.body
    problem = post_check(original, text)
    return problem[0] if problem else ""


def _outputs() -> dict[str, dict[str, dict[str, str]]]:
    """``system -> risk_id -> {text, check}``: teacher from its raw answers, others from
    ``generate``. Every system's text passes through the same post-checks."""
    out: dict[str, dict[str, dict[str, str]]] = {}
    teacher: dict[str, dict[str, str]] = {}
    risks = {c.risk_id: c for c in _load(SET50)}
    for rid, raw in _raw(TEACHER_MODEL).items():
        if rid not in risks:
            continue
        try:
            text = parse_output(raw).simple
        except ValueError:
            continue
        teacher[rid] = {"text": text, "check": _check(risks[rid], text)}
    out["teacher"] = teacher
    for p in sorted(DIR.glob("rewrites_*.jsonl")):
        out[p.stem.removeprefix("rewrites_")] = {
            str(r["risk_id"]): {
                "text": str(r.get("text") or ""),
                "check": str(r.get("check") or ""),
            }
            for r in read_jsonl(p)
        }
    return out


def cmd_sheet50(_: argparse.Namespace) -> None:
    """Blind shuffled gold-50 sheet and its key."""
    outputs = _outputs()
    rows, key = rewrite_sheet(_load(SET50), outputs)
    write_csv(rows, REWRITE_COLUMNS, SHEET50)
    _dump(key, KEY50)
    print(
        f"wrote {len(rows)} rows ({len(outputs)} systems) -> {SHEET50}; key {KEY50.name} (do not open)"
    )


def cmd_score50(_: argparse.Namespace) -> None:
    """Rated gold-50 sheet -> ``eval_results/c/simplify_gold50.json``."""
    key = json.loads(KEY50.read_text(encoding="utf-8"))
    result = {"systems": score_rewrites(read_csv(SHEET50), key), "set": "gold-50 (test slice)",
              "label_source": "human:akshat (blind rating)"}  # fmt: skip
    _dump(result, RESULT50)
    print(json.dumps(result["systems"], indent=1), "->", RESULT50)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("sample")
    s = sub.add_parser("sheet150")
    s.add_argument(
        "--prefill", default=PREFILL_MODEL, help="raw_<model>.jsonl slug for the pre-fill"
    )
    sub.add_parser("gold150")
    g = sub.add_parser("generate")
    g.add_argument("--system", required=True, choices=["base", "student"])
    g.add_argument("--backend", default="ollama", choices=["ollama", "llama-cpp"])
    g.add_argument("--model", required=True)
    sub.add_parser("sheet50")
    sub.add_parser("score50")
    a = ap.parse_args(argv)
    {"sample": cmd_sample, "sheet150": cmd_sheet150, "gold150": cmd_gold150,
     "generate": cmd_generate, "sheet50": cmd_sheet50, "score50": cmd_score50}[a.command](a)  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
