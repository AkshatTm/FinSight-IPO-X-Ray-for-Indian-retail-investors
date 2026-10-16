"""Frontier systems on the frozen bench (C4.3): paste bundles for the apps, or the Claude API.

Frontier models are evaluation only; nothing here is used by the product.

App route (C04 §5; Akshat runs it, memory and web search off, a new chat per bundle):

    uv run python scripts/bench_frontier.py export --system opus        # or chatgpt_go
    # paste each bench/v1/paste/<system>/<bundle>.md into a NEW chat; paste the whole reply into
    # bench/v1/paste/<system>/<bundle>.reply.md; fill bench/v1/paste/<system>/run.yaml
    uv run python scripts/bench_frontier.py import --system opus

API route (Claude only; the key comes from ANTHROPIC_API_KEY or an `ant auth login` profile, never
from this repo; the SDK is not a product dependency, hence ``--with``):

    uv run --with anthropic python scripts/bench_frontier.py api --system opus [--limit 3]

A bundle holds several frozen prompts, each unchanged, under ``=== TASK <id> ===`` fences; the
reply is split on its ``### <id>`` headings and anything missing is flagged, never guessed. The API
route sends each frozen prompt alone. Claude Opus 5.5 does not accept ``temperature`` and always
thinks, so the API run pins ``effort`` instead (recorded); refusal fallbacks are left off so every
answer comes from the named model.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bench_run import BENCH, _append, _done, _now, load_prompts  # noqa: E402

from finsight.bench import bundle, load, split_bundle  # noqa: E402

SYSTEMS = ("opus", "chatgpt_go")
BUNDLE_CHARS = 40_000  # one paste stays well inside both apps' message limits
API_MODEL = "claude-opus-5-5"
API_EFFORT = "medium"
PRICE_PER_MTOK = {"claude-opus-5-5": (4.00, 20.00)}  # USD in / out, Anthropic list price
RUN_TEMPLATE = {
    "app": "",  # "Claude.ai" / "ChatGPT"
    "plan": "",  # e.g. "Pro", "Go"
    "plan_price_inr_per_month": None,
    "model_string_shown": "",  # exactly as the app shows it
    "memory_off": None,
    "web_search_off": None,
    "input_condition": "frozen retrieved passages (bench v1), no PDF",
    "bundles": {},  # <bundle name>: {"start_utc": "", "end_utc": ""}
}


def bundles(prompts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """``{name: prompts}``: per IPO and task, split to stay under ``BUNDLE_CHARS``."""
    out: dict[str, list[dict[str, Any]]] = {}
    for p in prompts:
        base = f"{p['ipo_id']}__{p['task']}"
        part = 1
        while True:
            name = f"{base}__{part}"
            cur = out.setdefault(name, [])
            if not cur or sum(len(x["text"]) for x in cur) + len(p["text"]) <= BUNDLE_CHARS:
                cur.append(p)
                break
            part += 1
    return out


def cmd_export(a: argparse.Namespace) -> int:
    out = BENCH / "paste" / a.system
    out.mkdir(parents=True, exist_ok=True)
    groups = bundles(load_prompts())
    for name, ps in groups.items():
        (out / f"{name}.md").write_text(
            bundle([(p["prompt_id"], p["text"]) for p in ps]), encoding="utf-8", newline="\n"
        )
        reply = out / f"{name}.reply.md"
        if not reply.exists():
            reply.write_text("", encoding="utf-8")
    run = out / "run.yaml"
    if not run.exists():
        tmpl = RUN_TEMPLATE | {"bundles": {n: {"start_utc": "", "end_utc": ""} for n in groups}}
        run.write_text(yaml.safe_dump(tmpl, sort_keys=False), encoding="utf-8", newline="\n")
    print(f"{len(groups)} bundles in {out} (paste each into a new chat)")
    return 0


def cmd_import(a: argparse.Namespace) -> int:
    folder = BENCH / "paste" / a.system
    run = yaml.safe_load((folder / "run.yaml").read_text(encoding="utf-8")) or {}
    answers = BENCH / "answers" / a.system / "answers.jsonl"
    done = _done(answers)
    problems: list[str] = []
    n = 0
    for name, ps in bundles(load_prompts()).items():
        reply_path = folder / f"{name}.reply.md"
        reply = reply_path.read_text(encoding="utf-8") if reply_path.exists() else ""
        if not reply.strip():
            problems.append(f"{name}: no reply yet")
            continue
        parts, issues = split_bundle(reply, [p["prompt_id"] for p in ps])
        problems += [f"{name}: {x}" for x in issues]
        times = (run.get("bundles") or {}).get(name) or {}
        for p in ps:
            if p["prompt_id"] in done or p["prompt_id"] not in parts:
                continue
            _append(answers, {
                "system": a.system, "prompt_id": p["prompt_id"], "task": p["task"],
                "ipo_id": p["ipo_id"], "text": parts[p["prompt_id"]], "seconds": None,
                "bundle": name, "bundle_size": len(ps), "bundle_start_utc": times.get("start_utc"),
                "bundle_end_utc": times.get("end_utc"), "model": run.get("model_string_shown"),
                "error": None, "utc": _now(),
            })  # fmt: skip
            n += 1
    meta = BENCH / "answers" / a.system / "run.json"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(run | {"route": "app paste", "single_run": True}, indent=2,
                               default=str) + "\n", encoding="utf-8", newline="\n")  # fmt: skip
    print(f"imported {n} answers; {len(problems)} problems")
    for p in problems[:40]:
        print("  ", p)
    return 0


def cmd_api(a: argparse.Namespace) -> int:
    if a.system != "opus":
        print("only Claude has an API route; ChatGPT Go is an app plan (use export/import)")
        return 2
    try:
        import anthropic
    except ImportError:
        print("run with: uv run --with anthropic python scripts/bench_frontier.py api ...")
        return 2
    client = anthropic.Anthropic()  # key from the environment or an `ant auth login` profile
    answers = BENCH / "answers" / "opus_api" / "answers.jsonl"
    done = _done(answers)
    todo = [p for p in load_prompts() if p["prompt_id"] not in done][: a.limit]
    tokens_in = tokens_out = 0
    for i, p in enumerate(todo, start=1):
        t0, text, error, usage = time.perf_counter(), "", None, None
        try:
            msg = client.messages.create(
                model=API_MODEL,
                max_tokens=16000,  # room for thinking; the prompt itself asks for a short answer
                output_config={"effort": API_EFFORT},
                messages=[{"role": "user", "content": p["text"]}],
            )
            text = "".join(b.text for b in msg.content if b.type == "text")
            usage = {"input_tokens": msg.usage.input_tokens,
                     "output_tokens": msg.usage.output_tokens}  # fmt: skip
            tokens_in += msg.usage.input_tokens
            tokens_out += msg.usage.output_tokens
            if msg.stop_reason == "refusal":
                error = "refusal"
        except anthropic.APIError as exc:
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
        _append(answers, {
            "system": "opus_api", "prompt_id": p["prompt_id"], "task": p["task"],
            "ipo_id": p["ipo_id"], "text": text, "seconds": round(time.perf_counter() - t0, 2),
            "model": API_MODEL, "effort": API_EFFORT, "usage": usage, "error": error,
            "utc": _now(),
        })  # fmt: skip
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}", flush=True)
    price_in, price_out = PRICE_PER_MTOK[API_MODEL]
    meta = BENCH / "answers" / "opus_api" / "run.json"
    meta.write_text(json.dumps({
        "route": "Claude API", "model": API_MODEL, "effort": API_EFFORT,
        "temperature": "not accepted by this model", "fallbacks": "off",
        "input_tokens_this_run": tokens_in, "output_tokens_this_run": tokens_out,
        "usd_this_run": round(tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out, 4),
        "price_per_mtok_usd": [price_in, price_out], "ended_utc": _now(), "single_run": True,
    }, indent=2) + "\n", encoding="utf-8", newline="\n")  # fmt: skip
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("export", cmd_export), ("import", cmd_import), ("api", cmd_api)):
        p = sub.add_parser(name)
        p.add_argument("--system", required=True, choices=SYSTEMS)
        p.add_argument("--limit", type=int, default=None)
        p.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    if not load(BENCH).frozen:
        ap.error("the bench is not frozen yet (C-ADR-06)")
    return int(a.fn(a))


if __name__ == "__main__":
    raise SystemExit(main())
