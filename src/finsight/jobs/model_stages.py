"""The upload stages that use the trained models and publish the workspace (C3.3, B02 §3.1).

``risks_scored``: category (ONNX classifier, CPU), novelty against the rolling reference window
(bge-m3, one load, freed at once), seriousness and importance. ``risk_level``: points from the
red flags and the rare serious risks, placed among the reference IPOs. ``simplify``: queues the
top-N risks for the student (the API process drains the queue in the background). ``index``:
writes the document in the layout of the showcase IPOs under ``data/processed/<doc_id>/`` (pages,
words, sections, tables, X-Ray facts, BM25 index), so the facts, document and chat views work for
an upload exactly as for a showcase IPO.

Models load one stage at a time and are released before the next stage starts (16 GB laptop).
"""

from __future__ import annotations

import gc
import json
import re
from datetime import date
from typing import Any

from finsight.core.logging import get_logger
from finsight.core.schemas import ParsedDoc, Risk
from finsight.jobs.pipeline import (
    PARSED,
    SECTIONS,
    XRAY,
    _parsed_doc,
    _sections,
    _with_pdf,
)
from finsight.jobs.runner import JobContext, Stage
from finsight.parse import extract_tables, pymupdf_backend
from finsight.parse.page_images import render_pages
from finsight.pipeline import RISKS, RISKS_FILE
from finsight.pipeline.index_stage import run_index
from finsight.pipeline.layout import doc_outputs, xray_path
from finsight.risklevel import RISKLEVEL_FILE
from finsight.risklevel import build as build_risk_level
from finsight.risks import (
    OnnxClassifier,
    add_features,
    load_bank,
    predict,
    ranked_rids,
    risks_config,
    score_risks,
)
from finsight.risks.teacher_data import original_text
from finsight.splits import load_splits, reference_bank
from finsight.storage import get_json, put_json

logger = get_logger("finsight.jobs.model_stages")

SCORED = "risks_scored.json"
INDEX_MARKER = "index.json"
UPLOAD_META = "upload.json"
TABLE_SECTIONS = (
    "objects_of_the_offer",
    "the_offer",
    "capital_structure",
    "basis_for_offer_price",
)
_COMPANY = re.compile(
    r"^\s*([A-Z][A-Za-z0-9&.,'()\- ]{2,70}?\s(?:LIMITED|Limited|LTD\.?|Ltd\.?))\s*$"
)
_NOT_THE_ISSUER = re.compile(
    r"EXCHANGE|SECURITIES|REGISTRAR|REGISTRARS|CAPITAL|SEBI|BOARD OF|LINK INTIME|KFIN|MUFG|"
    r"BSE|NSE|CREDIT|ADVISORS|PARTNERS|BANK|ASSOCIATES|PRIVATE|PVT",
    re.IGNORECASE,
)


def guess_company(parsed: ParsedDoc) -> str | None:
    """The issuer's name from the cover page: the first "… Limited" line that is not an
    exchange, registrar or banker. ``None`` when nothing on the first pages looks like one."""
    for page in parsed.pages[:3]:
        for line in page.text.splitlines():
            m = _COMPANY.match(line)
            if m and not _NOT_THE_ISSUER.search(m.group(1)):
                return " ".join(m.group(1).split()).title().replace(" Limited", " Limited")
    return None


def _company(ctx: JobContext) -> str:
    doc = ctx.db.get_doc(ctx.doc_id)
    if doc is not None and doc.company:
        return doc.company
    name = guess_company(_parsed_doc(ctx))
    if name:
        ctx.db.update_doc(ctx.doc_id, company=name)
    return name or ""


def _release_gpu() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def _embedder() -> Any | None:
    """bge-m3 on the GPU, or the CPU when that fails; ``None`` when it cannot load at all."""
    try:
        from finsight.retrieve import BgeM3Embedder
    except ImportError:
        return None
    for device in ("cuda", "cpu"):
        try:
            return BgeM3Embedder(device=device)
        except Exception as err:  # no GPU, out of memory, no weights: try the next one
            logger.warning("bge-m3 on %s failed: %s", device, type(err).__name__)
    return None


def _load_risks(ctx: JobContext) -> list[Risk]:
    return RISKS.validate_python(get_json(ctx.storage, ctx.key(RISKS_FILE)))


def _risks_scored(ctx: JobContext) -> dict[str, Any]:
    cfg = risks_config()
    risks = _load_risks(ctx)
    company = _company(ctx)
    if not risks:
        put_json(ctx.storage, ctx.key(SCORED), {"n_risks": 0})
        return {"n_risks": 0}

    texts = [original_text({"title": r.title, "body": r.body}) for r in risks]
    classifier = OnnxClassifier(ctx.settings.paths.models_dir / "risk_classifier" / "onnx")
    labelled = predict(classifier, texts)
    del classifier
    gc.collect()
    risks = [
        r.model_copy(update={"category": c, "category_conf": round(p, 4)})
        for r, (c, p) in zip(risks, labelled, strict=True)
    ]

    bank_path = ctx.settings.paths.data_dir / "processed" / "bank" / "risk_bank.parquet"
    bank = embedder = None
    novelty_on = False
    if bank_path.exists():
        embedder = _embedder()
        if embedder is not None:
            splits = load_splits(ctx.settings.root / "configs" / "splits.yaml")
            bank = reference_bank(
                load_bank(bank_path, years=None),
                splits,
                date.today(),
                kind="product",
                exclude_company=company or None,
            )
    try:
        risks = add_features(
            risks,
            company,
            bank=bank if len(bank or []) else None,
            embedder=embedder,
            tau=float(cfg["novelty"]["tau"]),
            nearest=int(cfg["novelty"]["nearest"]),
            flag_min_hedges=int(cfg["hedging"]["flag_min_hedges"]),
        )
        novelty_on = any(r.novelty is not None for r in risks)
    finally:
        del embedder
        _release_gpu()
    risks = score_risks(risks)
    put_json(ctx.storage, ctx.key(RISKS_FILE), RISKS.dump_python(risks, mode="json"))
    result = {
        "n_risks": len(risks),
        "novelty": novelty_on,
        "reference_ipos": len(set(bank.ipo_ids or [])) if bank is not None else 0,
        "high": sum(r.seriousness == "high" for r in risks),
    }
    put_json(ctx.storage, ctx.key(SCORED), result)
    return result


def _risk_level(ctx: JobContext) -> dict[str, Any]:
    scores = ctx.settings.paths.data_dir / "processed" / "risk_bank" / "reference_scores.csv"
    level = build_risk_level(ctx.storage, ctx.doc_id, company=_company(ctx), scores_path=scores)
    return {"level": level.level, "score": level.score, "forced_by": level.forced_by}


def _simplify(ctx: JobContext) -> dict[str, Any]:
    """Queue the top-N risks by importance; the API's background worker rewrites them."""
    from finsight.jobs.simplify_worker import auto_enqueue

    picked = auto_enqueue(
        ctx.db, ctx.doc_id, ranked_rids(_load_risks(ctx)), ctx.settings.simplify.auto_top_n
    )
    return {"queued": len(picked)}


def _index(ctx: JobContext) -> dict[str, Any]:
    """Publish the document in the showcase layout and build its BM25 index."""
    processed = ctx.settings.paths.processed_dir
    out = doc_outputs(processed, ctx.doc_id, "rhp")
    out.parsed.parent.mkdir(parents=True, exist_ok=True)
    parsed, sections = _parsed_doc(ctx), _sections(ctx)
    out.parsed.write_bytes(ctx.storage.get_bytes(ctx.key(PARSED)))
    out.sections.write_bytes(ctx.storage.get_bytes(ctx.key(SECTIONS)))
    tables = _with_pdf(
        ctx,
        lambda path: extract_tables(
            path, parsed, sections, backend=pymupdf_backend, section_ids=TABLE_SECTIONS
        ),
    )
    from pydantic import TypeAdapter

    from finsight.core.schemas import Table

    out.tables.write_bytes(TypeAdapter(list[Table]).dump_json(tables, indent=1))
    if ctx.storage.exists(ctx.key(XRAY)):
        xray_path(processed, ctx.doc_id).write_bytes(ctx.storage.get_bytes(ctx.key(XRAY)))
    _with_pdf(ctx, lambda path: render_pages(path, out.pages_dir))
    report = run_index(processed, ctx.doc_id, docs=("rhp",))
    doc = ctx.db.get_doc(ctx.doc_id)
    meta = {
        "doc_id": ctx.doc_id,
        "company": (doc.company if doc and doc.company else None) or "Your document",
        "doc_type": doc.doc_type if doc else None,
        "pages": parsed.n_pages,
    }
    (out.parsed.parent / UPLOAD_META).write_text(json.dumps(meta), encoding="utf-8")
    result = {"passages": report.passages, "tables": report.tables, "pages": parsed.n_pages}
    put_json(ctx.storage, ctx.key(INDEX_MARKER), result)
    return result


def model_stages() -> list[Stage]:
    """The stages after ``risks_split``: score, level, simplify queue, workspace and index."""
    return [
        Stage("risks_scored", _risks_scored, output=SCORED, requires=("risks_split",)),
        Stage(
            "risk_level",
            _risk_level,
            output=RISKLEVEL_FILE,
            requires=("redflags",),
        ),
        Stage("simplify", _simplify, requires=("risks_scored",)),
        Stage("index", _index, output=INDEX_MARKER, requires=("sections",)),
    ]


__all__ = ["guess_company", "model_stages"]
