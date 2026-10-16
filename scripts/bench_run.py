"""Run a local system on the frozen bench (C4.1 / C4.2): rules/v1, student or base.

    uv run python scripts/bench_run.py --system student            # Tasks A, C, D, G via Ollama
    uv run python scripts/bench_run.py --system base
    uv run python scripts/bench_run.py --system rules_v1 --processed <data/processed>

Every model call gets the stored prompt text from ``bench/v1/inputs/prompts.jsonl.gz`` (never a
re-rendered one) at temperature 0 with thinking off, through the product's Ollama backend.
``rules/v1`` is the pipeline: Task A values and Task B statuses from the summary + red-flag rules
(sections re-detected, as E14/E15 v2), Tasks C and G through the product chat path (guard first,
the retrieval abstain gate, then ``generate.respond`` with qwen3.5:2b, whose prompt is checked to
be the stored one). Answers are appended to ``bench/v1/answers/<system>/answers.jsonl`` (a rerun
skips prompts already answered); ``run.json`` records the model, its Ollama digest, the git sha and
timings. The bench must be frozen first.
"""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from finsight.bench import CHAT_BUDGET_CHARS, load  # noqa: E402
from finsight.core.schemas import Passage  # noqa: E402

BENCH = ROOT / "bench" / "v1"
MODELS = {
    "student": "finsight-student:q4",
    "base": "qwen3:4b-instruct-2507-q4_K_M",
    "rules_v1": "qwen3.5:2b",  # the product chat model (full profile)
}
NUM_CTX = 4096
OLLAMA = "http://localhost:11434"


def load_prompts(bench: Path = BENCH) -> list[dict[str, Any]]:
    """The frozen prompt records."""
    data = gzip.decompress((bench / "inputs" / "prompts.jsonl.gz").read_bytes()).decode("utf-8")
    return [json.loads(x) for x in data.splitlines() if x.strip()]


def passages(record: dict[str, Any]) -> list[Passage]:
    """The prompt's passages as ``Passage`` objects (boxes are not stored)."""
    return [Passage(**p, char_to_bbox=[]) for p in record["passages"]]


def _done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        json.loads(x)["prompt_id"]
        for x in path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    }


def drop_errors(path: Path) -> list[str]:
    """Remove rows whose call failed (server crash, timeout) so a rerun repeats them once.

    The removed rows go to ``errors.jsonl`` beside the answers, so every retry stays on record.
    """
    if not path.exists():
        return []
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    bad = [r for r in rows if r.get("error") and r.get("error") != "refusal"]
    if bad:
        for r in bad:
            _append(path.with_name("errors.jsonl"), r)
        keep = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows if r not in bad)
        path.write_text(keep, encoding="utf-8", newline="\n")
    return [r["prompt_id"] for r in bad]


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def ollama_digest(model: str) -> str | None:
    """The installed model's digest from ``/api/tags`` (``None`` if Ollama is not running)."""
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
            tags = json.loads(r.read())
    except OSError:
        return None
    return next((m.get("digest") for m in tags.get("models", []) if m["name"] == model), None)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ----------------------------------------------------------------------------- model systems
def run_model(system: str, prompts: list[dict[str, Any]], out: Path) -> int:
    from finsight.generate import OllamaBackend

    llm = OllamaBackend(model=MODELS[system], num_ctx=NUM_CTX, timeout=900.0)
    if not llm.is_available():
        print(f"{MODELS[system]} is not installed in Ollama (or Ollama is not running)")
        return 2
    done = _done(out)
    todo = [p for p in prompts if p["prompt_id"] not in done]
    print(f"{system}: {len(todo)} prompts to run ({len(done)} already answered)")
    for i, p in enumerate(todo, start=1):
        t0, error, text = time.perf_counter(), None, ""
        try:
            text = llm.generate(p["text"], max_tokens=p["max_tokens"], temperature=0.0)
        except Exception as exc:  # recorded, never retried silently
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
        _append(out, {
            "system": system, "prompt_id": p["prompt_id"], "task": p["task"],
            "ipo_id": p["ipo_id"], "text": text, "seconds": round(time.perf_counter() - t0, 2),
            "model": MODELS[system], "error": error, "utc": _now(),
        })  # fmt: skip
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}", flush=True)
    return 0


# ----------------------------------------------------------------------------- rules/v1
def _pred_json(pred: Any) -> dict[str, Any]:
    value = pred.value
    if isinstance(value, list):
        value = [str(v) for v in value]
    elif value is not None and not isinstance(value, bool | str):
        value = str(value)
    return {"status": pred.status, "value": value, "page": pred.page}


def _summary(processed: Path, ipo: str, doc: str) -> tuple[Any, Any, str]:
    """``extract_summary`` with freshly detected sections (as E14 v2), the X-Ray, the doc used."""
    from finsight.core.schemas import ParsedDoc, XRay
    from finsight.parse import find_sections
    from finsight.summary import extract_summary

    for which in dict.fromkeys((doc, "rhp")):
        suffix = "" if which == "rhp" else "_prospectus"
        parsed = processed / ipo / f"parsed{suffix}.json"
        if parsed.exists():
            d = ParsedDoc.model_validate_json(parsed.read_bytes())
            xray_path = processed / ipo / "xray.json"
            xray = XRay.model_validate_json(xray_path.read_bytes()) if xray_path.exists() else None
            return extract_summary(d, find_sections(d), ipo), xray, which
    return None, None, "missing"


def run_rules_a_b(processed: Path, out: Path) -> None:
    """Task A values and Task B statuses from the pipeline's summary and red-flag rules."""
    from summary_eval import Pred, predicted

    from finsight.redflags import evaluate, inputs_from_summary

    cfg = yaml.safe_load((BENCH / "pinned" / "redflags.yaml").read_text(encoding="utf-8"))
    items = [
        json.loads(x) for x in (BENCH / "items" / "task_a.jsonl").read_text("utf-8").splitlines()
    ]
    done = _done(out)
    cache: dict[tuple[str, str], tuple[Any, Any, str, float]] = {}
    for ipo in sorted({i["ipo_id"] for i in items}):
        for doc in sorted({i["doc"] for i in items if i["ipo_id"] == ipo}):
            pid = f"A:{ipo}:rules:{doc}"
            if pid in done:
                continue
            t0 = time.perf_counter()
            summary, xray, used = _summary(processed, ipo, doc)
            seconds = time.perf_counter() - t0
            cache[(ipo, doc)] = (summary, xray, used, seconds)
            fields: dict[str, Any] = {}
            inputs = inputs_from_summary(summary, xray) if summary is not None else None
            for it in (i for i in items if i["ipo_id"] == ipo and i["doc"] == doc):
                key, period = it["key"], it["period"]
                if summary is None:
                    pred = Pred("not_found")
                elif key in {"offer_price", "fresh_issue_amount", "ofs_amount"}:
                    attr = {"fresh_issue_amount": "fresh_amount"}.get(key, key)
                    money = getattr(inputs, attr)
                    ev = inputs.evidence.get(attr) if inputs else None  # type: ignore[union-attr]
                    pred = (
                        Pred("found", money.value_inr, ev.page if ev else None)
                        if money is not None
                        else Pred("not_found")
                    )
                else:
                    pred = predicted(summary, key, period)
                fields[f"{key}@{period}"] = _pred_json(pred)
            _append(out, {
                "system": "rules_v1", "prompt_id": pid, "task": "A", "ipo_id": ipo,
                "doc_used": used, "fields": fields, "seconds": round(seconds, 2),
                "model": "rules (finsight.summary)", "error": None, "utc": _now(),
            })  # fmt: skip
        pid = f"B:{ipo}:rules"
        if pid in done:
            continue
        summary, xray, used, seconds = cache.get((ipo, "rhp")) or (
            *_summary(processed, ipo, "rhp"),
            0.0,
        )
        t0 = time.perf_counter()
        statuses = {}
        if summary is not None:
            flags = evaluate(inputs_from_summary(summary, xray), cfg=cfg)
            statuses = {f.id: f.status for f in flags.flags}
        _append(out, {
            "system": "rules_v1", "prompt_id": pid, "task": "B", "ipo_id": ipo,
            "statuses": statuses, "redflags_version": str(cfg["version"]),
            "seconds": round(seconds + time.perf_counter() - t0, 2),
            "model": "rules (finsight.redflags)", "error": None, "utc": _now(),
        })  # fmt: skip
        print(f"  rules A/B {ipo}", flush=True)


def run_rules_chat(prompts: list[dict[str, Any]], out: Path) -> None:
    """Tasks C and G through the product chat path on the stored passages."""
    from finsight.generate import NOT_FOUND, OllamaBackend, respond
    from finsight.guard import check_question, refusal_text

    llm = OllamaBackend(model=MODELS["rules_v1"], num_ctx=2048, timeout=900.0)
    done = _done(out)
    todo = [p for p in prompts if p["task"] in "CG" and p["prompt_id"] not in done]
    print(f"rules_v1 chat: {len(todo)} prompts")
    for p in todo:
        lang = p["language"]
        t0 = time.perf_counter()
        guard = check_question(p["question"])
        row: dict[str, Any] = {"system": "rules_v1", "prompt_id": p["prompt_id"],
                               "task": p["task"], "ipo_id": p["ipo_id"],
                               "model": MODELS["rules_v1"], "error": None}  # fmt: skip
        if guard.blocked:
            reason = guard.reason or "advice_intent"
            row |= {"status": "refused", "stage": "question", "reason": reason,
                    "text": refusal_text(reason, lang), "blocked": True}  # fmt: skip
        elif (p.get("retrieval") or {}).get("abstain"):
            row |= {"status": "abstained", "stage": "retrieval", "text": NOT_FOUND[lang],
                    "blocked": False}  # fmt: skip
        else:
            ps = passages(p)
            try:
                r = respond(p["question"], lang, lambda ps=ps: ps, llm,
                            budget_chars=CHAT_BUDGET_CHARS, max_tokens=p["max_tokens"],
                            temperature=0.0)  # fmt: skip
                row |= {"status": r.status, "stage": r.stage, "reason": r.reason, "text": r.text,
                        "raw": r.raw, "blocked": False,
                        "prompt_identical": bool(r.prompt and r.prompt.text == p["text"])}  # fmt: skip
                if r.error:
                    row["error"] = r.error
            except Exception as exc:
                row |= {"status": "error", "text": "", "blocked": False,
                        "error": f"{type(exc).__name__}: {str(exc)[:200]}"}  # fmt: skip
        row |= {"seconds": round(time.perf_counter() - t0, 2), "utc": _now()}
        _append(out, row)


# ----------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--system", required=True, choices=sorted(MODELS))
    ap.add_argument("--tasks", default="ACDG", help="subset of A, C, D, G (B comes with A)")
    ap.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--limit", type=int, default=None, help="first N prompts (smoke runs)")
    ap.add_argument("--allow-unfrozen", action="store_true", help="smoke runs before the freeze")
    ap.add_argument("--retry-errors", action="store_true", help="rerun prompts whose call failed")
    a = ap.parse_args(argv)
    manifest = load(BENCH)
    if not manifest.frozen and not a.allow_unfrozen:
        ap.error("the bench is not frozen: run scripts/bench_build.py freeze first (C-ADR-06)")
    out_dir = (
        BENCH / "answers" / a.system if manifest.frozen else BENCH / "answers" / "_smoke" / a.system
    )
    out = out_dir / "answers.jsonl"
    prompts = [p for p in load_prompts() if p["task"] in a.tasks][: a.limit]
    retried = drop_errors(out) if a.retry_errors else []
    started = _now()
    t0 = time.perf_counter()
    if a.system == "rules_v1":
        if "A" in a.tasks:
            run_rules_a_b(a.processed, out)
        run_rules_chat(prompts, out)
        code = 0
    else:
        code = run_model(a.system, prompts, out)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    run = {
        "system": a.system,
        "model": MODELS[a.system],
        "ollama_digest": ollama_digest(MODELS[a.system]),
        "git_sha": sha.stdout.strip(),
        "bench_version": manifest.version,
        "bench_frozen": manifest.frozen,
        "tasks": a.tasks,
        "temperature": 0.0,
        "num_ctx": 2048 if a.system == "rules_v1" else NUM_CTX,
        "think": False,
        "hardware": "laptop: RTX 2050 4 GB, 16 GB RAM, Ollama",
        "started_utc": started,
        "ended_utc": _now(),
        "wall_seconds": round(time.perf_counter() - t0, 1),
        "single_run": True,
        "retried_after_error": retried,
    }
    runs = out_dir / "run.json"
    history = json.loads(runs.read_text(encoding="utf-8")) if runs.exists() else []
    runs.write_text(json.dumps([*history, run], indent=2) + "\n", encoding="utf-8", newline="\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
