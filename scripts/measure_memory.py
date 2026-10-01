"""Measure what retrieval costs in RAM and VRAM on this laptop (02 section 12, ADR-040).

    uv run --group ml python scripts/measure_memory.py [--device cuda|cpu]

Loads, one after another, every demo IPO's index, the bge-m3 query encoder and the reranker, and
records this process's resident memory, the GPU memory PyTorch holds, and the system-wide RAM in
use, plus what a running Ollama takes (measured, not started). Run it with Ollama serving the
model you want to ship, so the numbers include everything that is resident at demo time.
Writes ``eval_results/memory.json``.
"""

from __future__ import annotations

import argparse
import json
import time

import psutil

from finsight.core.config import get_settings
from finsight.ingest.registry import list_demo_ipos
from finsight.retrieve import BgeM3Embedder, CrossEncoderReranker, Retriever

GB = 1024**3


def snapshot(label: str) -> dict[str, object]:
    import torch

    me = psutil.Process().memory_info().rss
    ollama = sum(
        p.info["memory_info"].rss
        for p in psutil.process_iter(["name", "memory_info"])
        if p.info["name"] and "ollama" in p.info["name"].lower() and p.info["memory_info"]
    )
    vram = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
    return {
        "step": label,
        "process_rss_gb": round(me / GB, 2),
        "torch_vram_gb": round(vram / GB, 2),
        "system_ram_used_gb": round(psutil.virtual_memory().used / GB, 2),
        "ollama_rss_gb": round(ollama / GB, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["cuda", "cpu"], default=None)
    args = parser.parse_args()
    processed = get_settings().paths.processed_dir
    rows = [snapshot("start")]
    retriever = Retriever(processed)
    for ipo in list_demo_ipos():
        retriever.index(ipo.ipo_id)
    rows.append(snapshot("10 IPO indexes loaded (chunks + vectors)"))
    retriever.embedder = BgeM3Embedder(device=args.device)
    rows.append(snapshot("+ bge-m3 query encoder"))
    retriever.reranker = CrossEncoderReranker(device=args.device)
    rows.append(snapshot("+ bge-reranker-v2-m3"))
    ipo_id = list_demo_ipos()[0].ipo_id
    started = time.perf_counter()
    result = retriever.search("What is the size of the fresh issue?", ipo_id)
    latency = time.perf_counter() - started
    started = time.perf_counter()
    retriever.search("Who is the registrar to the offer?", ipo_id)
    warm = time.perf_counter() - started
    rows.append(snapshot("after two searches"))
    report = {
        "device": retriever.embedder.device,
        "method": result.method,
        "first_search_s": round(latency, 2),
        "warm_search_s": round(warm, 2),
        "steps": rows,
    }
    out = get_settings().paths.eval_dir / "memory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
