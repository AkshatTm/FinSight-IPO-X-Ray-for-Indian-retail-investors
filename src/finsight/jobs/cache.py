"""Cache v2 (CC-04): the cache key, staleness, status, delete and re-analyse.

A stored analysis is valid for ``sha256(pdf) + pipeline_version + models_fingerprint``. The
file hash is the document id (``make_doc_id``); the other two are stored on the document row when
a job ends. Open a report made with another ``pipeline_version`` (bumped in ``configs/config.yaml``
when extraction, red-flag or risk-level logic changes) or other model weights and it is re-run.

``models_fingerprint`` hashes what the analysis used: the Ollama tag with its digest, the ONNX
classifier file, the reranker file and the bge-m3 snapshot. Weight files are hashed once and the
digest is remembered by size and modification time (``data/cache/weight_hashes.json``).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from finsight.core.config import Settings
from finsight.core.schemas import AnalysisStatus, DocRecord
from finsight.db import Database
from finsight.jobs import preflight as pf
from finsight.storage import Storage, doc_key

SOURCE = "source.pdf"
CacheState = Literal["fresh", "stale_version", "stale_models", "legacy"]


@dataclass(frozen=True)
class Fingerprint:
    """The models an analysis ran with. ``value`` is ``None`` when a required model cannot be
    identified right now (Ollama down): staleness cannot be judged then."""

    value: str | None
    components: dict[str, str | None]


def _file_sha(path: Path, cache_file: Path) -> str:
    stat = path.stat()
    key = str(path)
    try:
        known = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = {}
    entry = known.get(key)
    if entry and entry.get("size") == stat.st_size and entry.get("mtime_ns") == stat.st_mtime_ns:
        return str(entry["sha"])
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    known[key] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha": digest.hexdigest()}
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(known), encoding="utf-8")
    except OSError:
        pass  # the hash is still right; it is just recomputed next time
    return digest.hexdigest()


def models_fingerprint(settings: Settings, skip: Iterable[str] = ()) -> Fingerprint:
    """Fingerprint of the models the profile's stages use (empty when they are switched off).

    A model the user chose to analyse without counts as ``"skipped"``, so the same document is
    re-run once the model is back."""
    skipped = set(skip)
    cache_file = settings.paths.data_dir / "cache" / "weight_hashes.json"
    parts: dict[str, str | None] = {}
    for model in pf.required_models(settings):
        if model in skipped:
            parts[model] = "skipped"
        elif model == "ollama":
            digest = pf.ollama_digest(settings)
            parts[model] = f"{settings.simplify.model}@{digest}" if digest else None
        elif model == "classifier":
            onnx = pf.classifier_dir(settings) / "model.onnx"
            parts[model] = _file_sha(onnx, cache_file) if onnx.exists() else None
        elif model == "embeddings":
            shot = pf.hf_snapshot(pf.BGE_M3)
            parts[model] = f"{pf.BGE_M3}@{shot.name}" if shot else None
        elif model == "reranker":
            file = pf.reranker_file(settings)
            shot = pf.hf_snapshot(pf.BGE_RERANKER)
            if file is not None:
                parts[model] = _file_sha(file, cache_file)
            else:
                parts[model] = f"{pf.BGE_RERANKER}@{shot.name}" if shot else None
    if any(v is None for v in parts.values()):
        return Fingerprint(None, parts)
    blob = json.dumps(parts, sort_keys=True).encode()
    return Fingerprint(hashlib.sha256(blob).hexdigest(), parts)


def cache_key(sha256: str, pipeline_version: str, fingerprint: str) -> str:
    """The key an analysis is valid for: file hash, pipeline version and models fingerprint."""
    return hashlib.sha256(f"{sha256}|{pipeline_version}|{fingerprint}".encode()).hexdigest()


def cache_state(doc: DocRecord, settings: Settings, fingerprint: Fingerprint) -> CacheState:
    """Whether the stored analysis still matches the current pipeline and models."""
    if doc.pipeline_version is None or doc.fingerprint is None:
        return "legacy"
    if doc.pipeline_version != settings.pipeline_version:
        return "stale_version"
    if fingerprint.value is not None and fingerprint.value != doc.fingerprint:
        return "stale_models"
    return "fresh"


def analysis_status(
    job_status: str, failed_stages: list[str], skipped: list[str]
) -> tuple[AnalysisStatus, list[str]]:
    """``complete`` only when every stage ran and no model was skipped; the reasons otherwise."""
    if job_status == "failed":
        return "failed", [f"failed:{s}" for s in failed_stages] or ["failed"]
    reasons = [f"stage_failed:{s}" for s in failed_stages]
    reasons += [f"skipped_model:{m}" for m in skipped]
    return ("degraded" if reasons else "complete"), reasons


def wipe_artifacts(
    db: Database,
    storage: Storage,
    settings: Settings,
    doc_id: str,
    keep_source: bool = False,
) -> None:
    """Remove everything derived from a document: stored stage outputs, the published workspace
    (pages, words, tables, BM25 index, page images) and its simplification queue. The PDF goes
    too unless ``keep_source`` (a re-analysis needs it)."""
    source = None
    if keep_source and storage.exists(doc_key(doc_id, SOURCE)):
        source = storage.get_bytes(doc_key(doc_id, SOURCE))
    storage.delete_prefix(f"docs/{doc_id}/")
    if source is not None:
        storage.put_bytes(doc_key(doc_id, SOURCE), source, "application/pdf")
    db.clear_queue(doc_id)
    shutil.rmtree(settings.paths.processed_dir / doc_id, ignore_errors=True)


def delete_document(db: Database, storage: Storage, settings: Settings, doc_id: str) -> None:
    """Delete an analysis completely: files, indexes, page images, jobs and rows. The ``uploads``
    rows stay (the daily quota); uploading the same PDF again analyses it from scratch."""
    wipe_artifacts(db, storage, settings, doc_id)
    db.delete_doc_rows(doc_id)


def reset_for_reanalysis(
    db: Database,
    storage: Storage,
    settings: Settings,
    doc_id: str,
    skip: list[str] | None = None,
) -> str:
    """Clear the old analysis (keeping the PDF), mark the document ``processing`` and create the
    new job. Returns the job id; the caller launches it."""
    wipe_artifacts(db, storage, settings, doc_id, keep_source=True)
    db.update_doc(
        doc_id,
        status="processing",
        rejection=None,
        analysis_status=None,
        degraded_reasons=[],
        skipped_models=skip or [],
        pipeline_version=None,
        fingerprint=None,
    )
    job = db.create_job(doc_id)
    db.append_event(job.job_id, "stage", {"stage": "received", "status": "end"})
    return job.job_id
