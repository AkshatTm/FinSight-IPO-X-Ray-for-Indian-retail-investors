"""End-to-end smoke test on the running local app: upload a PDF, wait for the pipeline, check
every panel's API, ask three chat questions. Prints timings.

    uv run python scripts/smoke_local.py [--pdf PATH] [--api http://127.0.0.1:8000] [--fresh]

Start the app first (``uv run poe app``). The default PDF is an offer document that is neither
one of the 10 gold IPOs nor in the test / bench slices. ``--fresh`` forgets an earlier analysis
of the same file so the whole pipeline runs again. Exit status 0 only when every check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "data" / "raw" / "offer_docs" / "seshaasai-technologies-2025.pdf"
QUESTIONS = [
    ("fact", "How much money is the company raising through the fresh issue?"),
    ("red-flag", "Are there any red flags about debt or what the promoters paid?"),
    ("advice", "Should I apply for this IPO?"),
]
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    """Record and print one check."""
    results.append((name, ok, detail))
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)


def get(client: httpx.Client, path: str, **kw: Any) -> Any:
    """GET JSON; ``None`` on an error status."""
    r = client.get(path, **kw)
    return r.json() if r.status_code == 200 else None


def upload(client: httpx.Client, pdf: Path) -> tuple[str, float]:
    """Init, send and complete the upload; return the doc id and the seconds it took."""
    data = pdf.read_bytes()
    t0 = time.perf_counter()
    init = client.post(
        "/api/uploads/init",
        json={
            "filename": pdf.name,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
    )
    init.raise_for_status()
    body = init.json()
    doc_id = body["doc_id"]
    if body["status"] == "exists":
        print(f"  already analysed ({doc_id}); use --fresh to run the pipeline again")
        return doc_id, time.perf_counter() - t0
    sent = client.request(
        body.get("upload_method") or "POST",
        body["upload_url"],
        content=data,
        headers={"content-type": "application/pdf"},
    )
    sent.raise_for_status()
    client.post(f"/api/uploads/{doc_id}/complete").raise_for_status()
    return doc_id, time.perf_counter() - t0


def follow_job(client: httpx.Client, doc_id: str, limit_s: float) -> dict[str, float]:
    """Read the job's event stream; seconds from start to the end of each stage."""
    t0 = time.perf_counter()
    ends: dict[str, float] = {}
    event = ""
    with client.stream("GET", f"/api/docs/{doc_id}/events", timeout=limit_s) as r:
        for line in r.iter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and event == "stage":
                d = json.loads(line.split(":", 1)[1])
                if d["status"] in ("end", "failed"):
                    ends[d["stage"] + ("" if d["status"] == "end" else " (failed)")] = round(
                        time.perf_counter() - t0, 1
                    )
            elif line.startswith("data:") and event == "done":
                break
    return ends


def ask(client: httpx.Client, ipo_id: str, question: str) -> dict[str, Any]:
    """One chat question; the event names, answer text, verdict marks and timings."""
    t0 = time.perf_counter()
    out: dict[str, Any] = {"events": [], "first_token_s": None, "answer": "", "verdicts": []}
    event = ""
    with client.stream(
        "POST", "/api/chat", json={"ipo_id": ipo_id, "question": question}, timeout=300
    ) as r:
        for line in r.iter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
                out["events"].append(event)
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1])
                if event == "token" and out["first_token_s"] is None:
                    out["first_token_s"] = round(time.perf_counter() - t0, 1)
                if event == "answer":
                    out["answer"] = data.get("text", "")
                if event == "verdict":
                    out["verdicts"].append(data.get("verdict") or data.get("status"))
                if event == "guard":
                    out["guard"] = data
                if event == "error":
                    out["error"] = data
    out["total_s"] = round(time.perf_counter() - t0, 1)
    return out


def main() -> int:
    """Run the smoke test."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--limit-s", type=float, default=1800)
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    client = httpx.Client(base_url=a.api, timeout=60)
    t_all = time.perf_counter()

    print("health")
    health = get(client, "/api/health")
    check("API answers", health is not None)
    if health is None:
        return 1
    check(
        "Ollama model loaded or loadable", health["status"] in ("ok", "warming"), health["status"]
    )

    print(f"upload {a.pdf.name}")
    sha = hashlib.sha256(a.pdf.read_bytes()).hexdigest()
    doc_id = "doc_" + sha[:16]
    if a.fresh:
        subprocess.run(
            ["uv", "run", "python", "-m", "finsight.jobs", "forget", doc_id], cwd=ROOT, check=False
        )
    doc_id, t_upload = upload(client, a.pdf)
    print(f"  uploaded in {t_upload:.1f}s -> {doc_id}")
    stages = follow_job(client, doc_id, a.limit_s)
    detail = get(client, f"/api/docs/{doc_id}") or {}
    status = detail.get("doc", {}).get("status")
    check("pipeline finished", status in ("ready", "partial"), f"status={status}")
    prev = 0.0
    for name, t in stages.items():
        print(f"    {name:<22} done at {t:>7.1f}s (+{t - prev:.1f}s)")
        prev = t
    failed = [s for s in stages if "failed" in s]
    check("no failed stage", not failed, ", ".join(failed))
    t_pipeline = prev

    print("panels")
    doc = detail.get("doc", {})
    check(
        "doc: company and pages",
        bool(doc.get("company")) and bool(doc.get("pages")),
        f"{doc.get('company')}, {doc.get('pages')} pages",
    )
    report = get(client, f"/api/docs/{doc_id}/report")
    check("report overview", report is not None)
    flags = get(client, f"/api/docs/{doc_id}/redflags")
    check(
        "red flags (13)",
        bool(flags) and len(flags["flags"]) == 13,
        ", ".join(f"{f['id']}={f['status']}" for f in (flags or {"flags": []})["flags"]),
    )
    risks = get(client, f"/api/docs/{doc_id}/risks")
    n = risks["n_total"] if risks else 0
    scored = [r for r in (risks or {"risks": []})["risks"] if r.get("category")]
    check(
        "risks listed and categorised", n > 0 and len(scored) == len(risks["risks"]), f"{n} risks"
    )
    check(
        "novelty present",
        any(r.get("novelty") is not None for r in (risks or {"risks": []})["risks"]),
    )
    level = get(client, f"/api/docs/{doc_id}/risk-level")
    check(
        "risk level with reasons",
        bool(level) and bool(level.get("level")),
        f"{(level or {}).get('level')}, {len((level or {}).get('reasons', []))} reasons",
    )
    compare = get(client, f"/api/docs/{doc_id}/compare")
    check("compare", compare is not None)
    xray = get(client, f"/api/ipos/{doc_id}/xray")
    with_value = [f for f in (xray or {"fields": []})["fields"] if f.get("value")]
    check(
        "facts (X-Ray)",
        len(with_value) > 0,
        f"{len(with_value)} of {len((xray or {'fields': []})['fields'])} fields",
    )
    detail_ipo = get(client, f"/api/ipos/{doc_id}")
    check("document detail and sections", bool(detail_ipo) and bool(detail_ipo["sections"]))
    page = client.get(f"/api/ipos/{doc_id}/pages/1")
    check("page image", page.status_code == 200 and len(page.content) > 1000)
    words = get(client, f"/api/ipos/{doc_id}/pages/1/words")
    check("page words", bool(words) and bool(words["words"]))
    chips = get(client, f"/api/ipos/{doc_id}/suggested-questions")
    check("suggested questions", bool(chips))

    print("plain-English rewrites (student, background)")
    t0 = time.perf_counter()
    ready = 0
    first = ((get(client, f"/api/docs/{doc_id}/risks") or {"risks": []})["risks"] or [{}])[0]
    if first.get("rid"):  # the click path: "Explain in plain English" moves it to the front
        client.post(f"/api/docs/{doc_id}/risks/{first['rid']}/simplify")
    while time.perf_counter() - t0 < 240:
        page_risks = (get(client, f"/api/docs/{doc_id}/risks") or {"risks": []})["risks"]
        ready = sum(r["simple_status"] == "ready" for r in page_risks)
        if ready >= 1:
            break
        time.sleep(5)
    check("first rewrite arrived", ready >= 1, f"after {time.perf_counter() - t0:.0f}s")

    print("chat")
    for kind, q in QUESTIONS:
        r = ask(client, doc_id, q)
        short = (r["answer"] or json.dumps(r.get("guard", r.get("error", "")), ensure_ascii=False))[
            :160
        ]
        print(
            f"    ({kind}) {q}\n      -> {short!r}\n      first token {r['first_token_s']}s, total {r['total_s']}s, events {sorted(set(r['events']))}"
        )
        if kind == "advice":
            check("advice question refused", "guard" in r and r["guard"].get("blocked") is True)
        elif kind == "fact":
            check("fact answered with citations", bool(r["answer"]) and "error" not in r)
        else:
            check("red-flag question answered", bool(r["answer"]) and "error" not in r)

    bad = [n for n, ok, _ in results if not ok]
    print(f"\npipeline {t_pipeline:.0f}s, whole smoke test {time.perf_counter() - t_all:.0f}s")
    print(
        f"{len(results) - len(bad)}/{len(results)} checks passed"
        + (f"; failed: {bad}" if bad else "")
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
