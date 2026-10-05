"""Resumable batch run of the upload stages over the downloaded universe (C1.3).

One document at a time (16 GB RAM, Ollama stopped), through ``validated → detected → parsed →
sections → risks_split`` with the same stage functions the upload worker uses. Each document's
outcome goes to a state file at once, so a crash or a stop loses nothing; a rerun skips finished
documents. Per document it records stage timings, peak RAM and output bytes. Afterwards
``apply_results`` writes ``status`` / ``pages`` / ``doc_date`` / ``exchange`` back to
``configs/ipo_universe.csv``.

Documents that are not usable are ``excluded`` with a reason (draft document, scan, SME cover,
rejected by validation); documents whose parse or risk split broke are ``failed`` so the failure
can be fixed with a regression test.

``finsight.jobs`` imports ``finsight.pipeline``, so it is imported inside the functions here.
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import psutil

SME_COVER = re.compile(
    r"\bNSE\s+EMERGE\b|\bEMERGE\s+platform\b|\bBSE\s+SME\b|\bSME\s+(?:platform|exchange)\b",
    re.I,
)
_DATED = re.compile(
    r"(?i:\bdated\b)\s*[:\-]?\s*(?:this\s+)?"
    r"((?:[A-Z][a-z]{2,8}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})|"
    r"(?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]{2,8}\.?,?\s+\d{4}))",
)
_DATE_FORMATS = ("%B %d, %Y", "%B %d,%Y", "%B %d %Y", "%d %B %Y", "%d %B, %Y", "%b %d, %Y")
COVER_PAGES = 6
FINAL = frozenset({"parsed", "failed", "excluded"})


def cover_date(text: str) -> date | None:
    """The first ``Dated: <date>`` on the cover pages, or ``None``."""
    for m in _DATED.finditer(text):
        raw = re.sub(r"(\d)(?:st|nd|rd|th)", r"\1", m.group(1)).replace(".", "").strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def detect_exchange(text: str) -> str | None:
    """``NSE``, ``BSE`` or ``both`` from the cover text; ``None`` when neither is named."""
    bse = bool(re.search(r"\bBSE\b|BSE Limited|Bombay Stock Exchange", text))
    nse = bool(re.search(r"\bNSE\b|National Stock Exchange", text))
    if bse and nse:
        return "both"
    return "BSE" if bse else "NSE" if nse else None


def looks_sme(text: str) -> bool:
    """True when the cover names an SME platform (C-ADR-09: SME issues are out of scope)."""
    return bool(SME_COVER.search(text))


@dataclass
class DocResult:
    """The outcome for one document."""

    ipo_id: str
    status: str  # parsed | failed | excluded
    reason: str = ""
    pages: int | None = None
    doc_type: str | None = None
    job_status: str = ""
    failed_stages: list[str] = field(default_factory=list)
    n_risks: int | None = None
    sections: list[str] = field(default_factory=list)
    timings_s: dict[str, float] = field(default_factory=dict)
    wall_s: float = 0.0
    peak_rss_mb: float = 0.0
    output_bytes: int = 0
    cover_date: str | None = None
    exchange: str | None = None
    finished_utc: str = ""


class RamSampler:
    """Samples this process's resident memory in a thread; ``peak_mb`` after ``stop()``."""

    def __init__(self, interval: float = 0.25) -> None:
        self._proc = psutil.Process()
        self._interval = interval
        self._stop = threading.Event()
        self.peak = 0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.peak = max(self.peak, self._proc.memory_info().rss)
            self._stop.wait(self._interval)

    def start(self) -> RamSampler:
        self._thread.start()
        return self

    def stop(self) -> float:
        self._stop.set()
        self._thread.join()
        self.peak = max(self.peak, self._proc.memory_info().rss)
        return round(self.peak / 1024**2, 1)


def _dir_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


def process_one(
    row: dict[str, str],
    pdf: Path,
    work_dir: Path,
    settings: Any,
    keep_source: bool = False,
) -> DocResult:
    """Run the upload stages on one downloaded PDF and classify the outcome."""
    from finsight.core.ids import make_doc_id
    from finsight.core.schemas import DocRecord, ParsedDoc
    from finsight.db import Database
    from finsight.jobs import JobContext, run_job, upload_stages
    from finsight.storage import LocalStorage, doc_key

    ipo_id = row["ipo_id"]
    sha = row["sha256"]
    doc_id = make_doc_id(sha)
    storage = LocalStorage(work_dir / "store")
    db = Database(f"sqlite:///{(work_dir / 'batch.db').as_posix()}")
    db.create_all()
    if db.get_doc(doc_id) is None:
        db.insert_doc(
            DocRecord(
                doc_id=doc_id, sha256=sha, company=row["company"], created_at=datetime.now(UTC)
            )
        )
    storage.put_bytes(doc_key(doc_id, "source.pdf"), pdf.read_bytes())
    job = db.create_job(doc_id)
    ctx = JobContext(doc_id, job.job_id, db, storage, settings)
    sampler = RamSampler().start()
    t0 = time.perf_counter()
    try:
        result = run_job(ctx, upload_stages())
    finally:
        peak = sampler.stop()
    wall = round(time.perf_counter() - t0, 1)
    out_dir = storage.root / "docs" / doc_id
    res = DocResult(
        ipo_id=ipo_id,
        status="failed",
        job_status=result.status,
        failed_stages=list(result.failed_stages),
        wall_s=wall,
        peak_rss_mb=peak,
        finished_utc=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    stored = db.get_job(job.job_id)
    if stored is not None:
        res.timings_s = dict((stored.progress or {}).get("timings_s", {}))
    doc = db.get_doc(doc_id)
    if doc is not None:
        res.pages, res.doc_type = doc.pages, doc.doc_type
    if result.rejection is not None:
        res.status, res.reason = "excluded", f"rejected by validation: {result.rejection}"
    elif res.doc_type == "drhp":
        res.status, res.reason = "excluded", "draft offer document (DRHP), not an RHP/Prospectus"
    elif "parsed" in result.failed_stages or "validated" in result.failed_stages:
        res.reason = f"stage failed: {','.join(result.failed_stages)}"
    else:
        parsed = ParsedDoc.model_validate_json(storage.get_bytes(doc_key(doc_id, "parsed.json")))
        cover = "\n".join(p.text for p in parsed.pages[:COVER_PAGES])
        d = cover_date(cover)
        res.cover_date = d.isoformat() if d else None
        res.exchange = detect_exchange(cover)
        if looks_sme(cover):
            res.status, res.reason = "excluded", "SME issue (cover names an SME platform; C-ADR-09)"
        else:
            sections_key = doc_key(doc_id, "sections.json")
            if storage.exists(sections_key):
                res.sections = [s["id"] for s in json.loads(storage.get_bytes(sections_key))]
            risks_key = doc_key(doc_id, "risks.json")
            if storage.exists(risks_key):
                res.n_risks = len(json.loads(storage.get_bytes(risks_key)))
            if "risk_factors" not in res.sections:
                res.reason = "no Risk Factors section found"
            elif not res.n_risks:
                res.reason = "Risk Factors found but no risks split"
            elif result.failed_stages:
                res.reason = f"stage failed: {','.join(result.failed_stages)}"
            else:
                res.status = "parsed"
    if not keep_source:
        storage.path(doc_key(doc_id, "source.pdf")).unlink(missing_ok=True)
    res.output_bytes = _dir_bytes(out_dir)
    return res


def load_state(path: Path) -> dict[str, DocResult]:
    """Finished results by ``ipo_id`` (empty when the file does not exist)."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {k: DocResult(**v) for k, v in raw.items()}


def save_state(path: Path, state: dict[str, DocResult]) -> None:
    """Atomically write the state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({k: asdict(v) for k, v in state.items()}, indent=1), encoding="utf-8")
    tmp.replace(path)


def run_batch(
    rows: list[dict[str, str]],
    pdf_dir: Path,
    work_dir: Path,
    settings: Any,
    state_path: Path,
    only: set[str] | None = None,
    limit: int | None = None,
    retry_failed: bool = False,
    min_free_gb: float = 15.0,
    log: Callable[[str], None] = print,
    process: Callable[..., DocResult] = process_one,
) -> dict[str, DocResult]:
    """Process every ``downloaded`` row not finished yet, one at a time; resumable.

    Stops (and says so) when free disk drops below ``min_free_gb``. ``retry_failed`` re-runs
    documents whose earlier result was ``failed`` (after a fix).
    """
    import shutil

    state = load_state(state_path)
    done = 0
    for row in rows:
        ipo = row["ipo_id"]
        if row["status"] != "downloaded" or (only and ipo not in only):
            continue
        prev = state.get(ipo)
        if prev and prev.status in FINAL and not (retry_failed and prev.status == "failed"):
            continue
        if limit is not None and done >= limit:
            break
        work_dir.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(work_dir).free < min_free_gb * 1024**3:
            log(f"STOP: free disk below {min_free_gb:g} GB")
            break
        pdf = pdf_dir / f"{ipo}.pdf"
        try:
            res = process(row, pdf, work_dir, settings)
        except Exception as err:  # one document must never stop the batch
            res = DocResult(
                ipo_id=ipo,
                status="failed",
                reason=f"crashed: {type(err).__name__}: {err}"[:300],
                finished_utc=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        state[ipo] = res
        save_state(state_path, state)
        done += 1
        log(
            f"{res.status:8} {ipo} pages={res.pages} risks={res.n_risks} "
            f"{res.wall_s:.0f}s {res.peak_rss_mb:.0f}MB {res.reason}"
        )
    return state


def apply_results(
    rows: list[dict[str, str]], state: dict[str, DocResult], window_days: int = 45
) -> int:
    """Write outcomes into the universe rows (in place); returns how many rows changed.

    The cover date replaces the SEBI posting date when it lies within ``window_days`` of it.
    """
    changed = 0
    for row in rows:
        res = state.get(row["ipo_id"])
        if res is None or row["status"] not in ("downloaded", "parsed", "failed", "excluded"):
            continue
        if row["status"] == "failed" and row["reason"].startswith("manual:"):
            continue
        before = dict(row)
        row["status"], row["reason"] = res.status, res.reason if res.status != "parsed" else ""
        if res.pages:
            row["pages"] = str(res.pages)
        if res.cover_date:
            posted = date.fromisoformat(row["doc_date"])
            cover = date.fromisoformat(res.cover_date)
            if abs(cover - posted) <= timedelta(days=window_days):
                row["doc_date"] = res.cover_date
        if res.exchange:
            row["exchange"] = res.exchange
        changed += row != before
    return changed
