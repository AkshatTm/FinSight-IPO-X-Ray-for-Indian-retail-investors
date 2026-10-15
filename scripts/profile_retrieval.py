"""C3.7: where do the ~17 s of the ``full`` profile's retrieval stage go?

    uv run --group ml python scripts/profile_retrieval.py --data <data dir> --out eval_results/c/retrieval_profile.json

Times one retrieval per dev question (BM25 + dense + RRF + rerank, as ``Retriever.search``) for a
grid of embedder device x reranker device x rerank pool, with the answer LLM resident in Ollama
(``keep_alive``) so the GPU is shared the way it is in the product. Each configuration also splits
the time into embed and rerank by wrapping the two models. Run with nothing else heavy open.
Reads the dev question file and the built indexes under ``--data``; writes one JSON file.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OLLAMA = "http://localhost:11434/api/generate"


def warm_llm(model: str) -> None:
    """Load the answer model into Ollama and keep it there for the whole run."""
    body = json.dumps({"model": model, "prompt": "hi", "stream": False, "keep_alive": "30m",
                       "options": {"num_predict": 1, "num_ctx": 2048}}).encode()  # fmt: skip
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=300).read()


def gpu_gb() -> float | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True,
                             timeout=10, check=True)  # fmt: skip
        return round(float(out.stdout.splitlines()[0]) / 1024, 2)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


class Timed:
    """Wraps an embedder or reranker and accumulates the seconds spent in it."""

    def __init__(self, inner: Any, method: str) -> None:
        self.inner, self.method, self.seconds = inner, method, 0.0
        setattr(self, method, self._call)

    def _call(self, *args: Any, **kw: Any) -> Any:
        start = time.perf_counter()
        try:
            return getattr(self.inner, self.method)(*args, **kw)
        finally:
            self.seconds += time.perf_counter() - start


def run_config(
    data: Path, questions: list[dict[str, Any]], emb_dev: str, rr_dev: str, pool: int
) -> dict[str, Any]:
    from finsight.retrieve import BgeM3Embedder, CrossEncoderReranker, Retriever

    emb = Timed(BgeM3Embedder(device=emb_dev), "embed")
    rr = Timed(CrossEncoderReranker(device=rr_dev), "score")
    retriever = Retriever(data / "processed", embedder=emb, reranker=rr, pool=pool)
    retriever.search(questions[0]["question"], questions[0]["ipo_id"])  # warm-up, not counted
    emb.seconds = rr.seconds = 0.0
    totals: list[float] = []
    for q in questions:
        start = time.perf_counter()
        retriever.search(q["question"], q["ipo_id"])
        totals.append(time.perf_counter() - start)
    n = len(totals)
    return {
        "embedder_device": emb_dev, "reranker_device": rr_dev, "rerank_top_n": pool,
        "n_questions": n, "gpu_used_gb": gpu_gb(),
        "search_s_median": round(statistics.median(totals), 2),
        "search_s_max": round(max(totals), 2),
        "embed_s_mean": round(emb.seconds / n, 2),
        "rerank_s_mean": round(rr.seconds / n, 2),
    }  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--llm", default="qwen3.5:2b")
    ap.add_argument("--no-llm", action="store_true", help="skip the resident LLM (the 0.7 s case)")
    a = ap.parse_args(argv)
    rows = [json.loads(x) for x in (a.data / "gold" / "questions_dev.jsonl").read_text(
        encoding="utf-8").splitlines() if x.strip()]  # fmt: skip
    questions = [q for q in rows if q.get("answerable") is not False][: a.n]
    if not a.no_llm:
        warm_llm(a.llm)
    grid = [("cuda", "cuda", 20), ("cuda", "cpu", 20), ("cpu", "cpu", 20),
            ("cuda", "cuda", 10), ("cuda", "cpu", 10), ("cpu", "cpu", 10)]  # fmt: skip
    results = []
    for emb_dev, rr_dev, pool in grid:
        r = run_config(a.data, questions, emb_dev, rr_dev, pool)
        results.append(r)
        print(json.dumps(r), flush=True)
    out = {"llm_resident": not a.no_llm, "llm": a.llm, "results": results,
           "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}  # fmt: skip
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n", "utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
