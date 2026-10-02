"""E10 (P5.7): how long does one question take, and how much memory does it need?

    uv run python -m finsight.evaluate.latency --profile dev_light [--n 20]
    uv run python -m finsight.evaluate.latency --profile full

Runs the first ``n`` answerable dev questions (English and Hindi as they come, Hinglish asked from
the English page) through the chat orchestrator, one at a time, and records per question the time
to the first streamed token, the time per stage and the total. Memory is sampled after every
question: this process, a running Ollama, the whole system, and the GPU (``nvidia-smi``). Run one
profile at a time with nothing else heavy open, Ollama serving, and stop Ollama afterwards.
``eval_results/latency.json`` holds one entry per profile; a rerun replaces that profile's entry.
This is a laptop number (RTX 2050, 4 GB): the deployed CPU Space will be slower.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finsight.evaluate.answers import answer_language, load_questions

GB = 1024**3


def summarise_times(values: list[float]) -> dict[str, float | None]:
    """Median, 90th percentile and maximum in milliseconds (``None`` when there is no value)."""
    if not values:
        return {"median": None, "p90": None, "max": None}
    ordered = sorted(values)
    p90 = ordered[min(len(ordered) - 1, round(0.9 * (len(ordered) - 1)))]
    return {"median": round(statistics.median(ordered), 1), "p90": round(p90, 1),
            "max": round(ordered[-1], 1)}  # fmt: skip


def time_turn(events: Iterable[tuple[str, Any]], clock: Any = time.perf_counter) -> dict[str, Any]:
    """Wall time to the first token and in total for one event stream, plus its outcome."""
    start = clock()
    first: float | None = None
    outcome, timings = "answered", {}
    for name, ev in events:
        if name == "token" and first is None:
            first = (clock() - start) * 1000
        elif name == "abstain":
            outcome = "abstained"
        elif name == "guard":
            outcome = "refused"
        elif name == "error":
            outcome = "error"
        elif name == "final":
            timings = dict(getattr(ev, "timings_ms", {}) or {})
    return {"outcome": outcome, "first_token_ms": first,
            "total_ms": (clock() - start) * 1000, "stages_ms": timings}  # fmt: skip


def gpu_used_gb() -> float | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True, timeout=10,
        )  # fmt: skip
        return round(float(out.stdout.splitlines()[0]) / 1024, 2)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def memory_snapshot() -> dict[str, float | None]:
    import psutil

    ollama = sum(
        p.info["memory_info"].rss
        for p in psutil.process_iter(["name", "memory_info"])
        if p.info["name"] and "ollama" in p.info["name"].lower() and p.info["memory_info"]
    )
    return {
        "process_rss_gb": round(psutil.Process().memory_info().rss / GB, 2),
        "ollama_rss_gb": round(ollama / GB, 2),
        "system_ram_used_gb": round(psutil.virtual_memory().used / GB, 2),
        "gpu_used_gb": gpu_used_gb(),
    }


def peak(snapshots: list[dict[str, float | None]]) -> dict[str, float | None]:
    keys = snapshots[0].keys() if snapshots else []
    return {k: max((s[k] for s in snapshots if s[k] is not None), default=None) for k in keys}


def per_stage(turns: list[dict[str, Any]], stage: str) -> list[float]:
    return [t["stages_ms"][stage] for t in turns if stage in t["stages_ms"]]


def summarise(turns: list[dict[str, Any]], memory: list[dict[str, float | None]]) -> dict[str, Any]:
    answered = [t for t in turns if t["outcome"] == "answered"]
    stages = sorted({s for t in turns for s in t["stages_ms"]})
    outcomes = {t["outcome"] for t in turns}
    firsts = [t["first_token_ms"] for t in answered if t["first_token_ms"]]
    return {
        "n_questions": len(turns),
        "outcomes": {o: sum(t["outcome"] == o for t in turns) for o in sorted(outcomes)},
        "first_token_ms": summarise_times(firsts),
        "total_ms": summarise_times([t["total_ms"] for t in answered]),
        "stage_median_ms": {
            s: summarise_times(per_stage(answered, s))["median"] for s in stages
        },
        "first_question_total_ms": turns[0]["total_ms"] if turns else None,
        "memory_peak": peak(memory),
        "memory_before": memory[0] if memory else None,
    }  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.evaluate.latency")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args(argv)

    from finsight.chat.orchestrator import ChatOrchestrator
    from finsight.core.config import load_settings

    settings = load_settings(args.profile)
    chat = ChatOrchestrator.from_settings(args.profile)
    questions = [
        q for q in load_questions(settings.paths.data_dir / "gold", "dev", None)
        if q.get("answerable") is not False
    ][: args.n]  # fmt: skip
    memory = [memory_snapshot()]
    turns = []
    for q in questions:
        turns.append(time_turn(chat.events(q["ipo_id"], q["question"], answer_language(q))))
        memory.append(memory_snapshot())
        t = turns[-1]
        first, total = t["first_token_ms"], t["total_ms"]
        print(
            f"{len(turns)}: {t['outcome']} first token {first} ms, total {total:.0f} ms", flush=True
        )
    entry = {
        "profile": args.profile,
        "llm": {"backend": settings.llm.backend, "model": settings.llm.model},
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        **summarise(turns, memory),
    }
    out = Path(settings.paths.eval_dir) / "latency.json"
    merged = json.loads(out.read_text("utf-8")) if out.exists() else {}
    merged[args.profile] = entry
    out.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + chr(10), "utf-8",
                   newline=chr(10))  # fmt: skip
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
