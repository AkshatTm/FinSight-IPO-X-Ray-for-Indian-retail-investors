"""Read-only IPO data for the API: list, detail, X-Ray, pages, word boxes, suggested questions.

Everything is read from ``data/processed/<ipo_id>/`` (what ``pipeline build`` wrote) and the
committed configs. Nothing here runs a model. Heavy files (``parsed.json``: every word of every
page) are cached, two at a time.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from finsight.api.errors import ApiError
from finsight.api.models import (
    ApiCandidate,
    Companion,
    FieldCheck,
    IpoDetail,
    IpoSummary,
    PageSize,
    PageWord,
    PageWords,
    SectionInfo,
    SuggestedQuestion,
    XRayField,
    XRayResponse,
)
from finsight.core.config import project_root
from finsight.core.schemas import Candidate, DocType, FieldResult, FieldSpec, ParsedDoc, XRay
from finsight.ingest.registry import DemoIpo, list_demo_ipos
from finsight.pipeline.layout import doc_outputs, xray_path

RENDER_DPI = 110  # parse/page_images.py: pixels * 72 / 110 = PDF points


def _config(name: str) -> Any:
    return yaml.safe_load((project_root() / "configs" / name).read_text(encoding="utf-8"))


class IpoStore:
    """The demo IPOs and their processed files."""

    def __init__(self, processed_dir: Path, fields: list[FieldSpec]) -> None:
        self.processed_dir = processed_dir
        self.fields = {f.id: f for f in fields}
        self._ipos: dict[str, DemoIpo] = {i.ipo_id: i for i in list_demo_ipos()}
        meta = _config("ipo_meta.yaml")["ipos"]
        self._meta: dict[str, dict[str, Any]] = meta

    # ---------------------------------------------------------------- lookup
    def get(self, ipo_id: str) -> DemoIpo:
        ipo = self._ipos.get(ipo_id)
        if ipo is None:
            raise ApiError(
                404,
                "ipo_not_found",
                f"No IPO with id '{ipo_id}'.",
                hint="Check /api/ipos for valid ids.",
            )
        return ipo

    def _xray(self, ipo_id: str) -> XRay | None:
        return _load_xray(str(xray_path(self.processed_dir, ipo_id)))

    # ------------------------------------------------------------------ list
    def list_ipos(
        self, q: str | None, sector: str | None, year: int | None, sort: str
    ) -> list[IpoSummary]:
        rows = [self._summary(i) for i in self._ipos.values()]
        if q:
            needle = q.casefold()
            rows = [r for r in rows if needle in f"{r.company} {r.sector or ''}".casefold()]
        if sector:
            rows = [r for r in rows if (r.sector or "").casefold() == sector.casefold()]
        if year:
            rows = [r for r in rows if r.listing_date and r.listing_date.year == year]
        if sort == "issue_size":
            rows.sort(key=lambda r: Decimal(r.issue_size_inr or "0"), reverse=True)
        else:
            rows.sort(key=lambda r: r.listing_date or date.min, reverse=True)
        return rows

    def _summary(self, ipo: DemoIpo) -> IpoSummary:
        xray = self._xray(ipo.ipo_id)
        meta = self._meta.get(ipo.ipo_id, {})
        return IpoSummary(
            id=ipo.ipo_id,
            company=ipo.company,
            sector=meta.get("sector"),
            listing_date=meta.get("listing_date"),
            rhp_pages=ipo.rhp.pages,
            issue_size_inr=_money_inr(xray, "total_issue_size"),
            fresh_inr=_money_inr(xray, "fresh_issue_size"),
            ofs_inr=_money_inr(xray, "ofs_amount"),
            xray_status="ready" if xray else "missing",
        )

    # ---------------------------------------------------------------- detail
    def detail(self, ipo_id: str) -> IpoDetail:
        ipo = self.get(ipo_id)
        sections: list[SectionInfo] = []
        docs: tuple[DocType, ...] = ("rhp", "prospectus")
        for doc in docs:
            for s in _load_sections(str(doc_outputs(self.processed_dir, ipo_id, doc).sections)):
                sections.append(
                    SectionInfo(
                        id=s["id"],
                        doc=doc,
                        title=s["title"],
                        start_page=s["start_page"],
                        end_page=s["end_page"],
                    )
                )
        return IpoDetail(
            id=ipo_id,
            company=ipo.company,
            rhp_pages=ipo.rhp.pages,
            prospectus_pages=ipo.prospectus.pages,
            page_size=self._page_size(ipo_id),
            sections=sections,
        )

    def _page_size(self, ipo_id: str) -> PageSize:
        path = doc_outputs(self.processed_dir, ipo_id, "rhp").pages_dir / "1.webp"
        if not path.exists():
            return PageSize(width=612.0, height=792.0)
        with Image.open(path) as image:
            w, h = image.size
        return PageSize(width=round(w * 72 / RENDER_DPI, 1), height=round(h * 72 / RENDER_DPI, 1))

    # ----------------------------------------------------------------- pages
    def page_path(self, ipo_id: str, n: int, doc: DocType) -> Path:
        ipo = self.get(ipo_id)
        total = (ipo.rhp if doc == "rhp" else ipo.prospectus).pages
        path = doc_outputs(self.processed_dir, ipo_id, doc).pages_dir / f"{n}.webp"
        if not 1 <= n <= total or not path.exists():
            raise ApiError(
                404,
                "page_out_of_range",
                f"Page {n} is not in the {doc} ({total} pages).",
                hint=f"Pages run from 1 to {total}.",
            )
        return path

    def words(self, ipo_id: str, n: int, doc: DocType) -> PageWords:
        self.page_path(ipo_id, n, doc)  # validates the id and the page number
        parsed = _load_parsed(str(doc_outputs(self.processed_dir, ipo_id, doc).parsed))
        if parsed is None or not 1 <= n <= len(parsed.pages):
            raise ApiError(404, "page_out_of_range", f"No words for page {n}.")
        page = parsed.pages[n - 1]
        return PageWords(
            page=page.number,
            width=page.width,
            height=page.height,
            words=[PageWord(t=w.text, b=w.bbox) for w in page.words],
        )

    # ----------------------------------------------------------------- xray
    def xray(self, ipo_id: str) -> XRayResponse:
        self.get(ipo_id)
        xray = self._xray(ipo_id)
        if xray is None:
            raise ApiError(
                404,
                "ipo_not_found",
                f"The X-Ray for '{ipo_id}' has not been built.",
                hint="Run `uv run python -m finsight.pipeline build --ipo " + ipo_id + "`.",
            )
        return XRayResponse(
            ipo_id=xray.ipo_id,
            company=xray.company,
            built_at=xray.built_at,
            fields=[self._field(f) for f in xray.fields],
            derived=xray.derived,
        )

    def _field(self, f: FieldResult) -> XRayField:
        spec = self.fields.get(f.field_id)
        c = f.chosen
        other = [x for x in f.candidates if c is not None and x.doc_type != c.doc_type]
        companion = _companion(other)
        return XRayField(
            field_id=f.field_id,
            label_en=spec.label_en if spec else f.field_id,
            label_hi=spec.label_hi if spec else f.field_id,
            type=spec.type if spec else "text",
            value=c.value if c else None,
            doc=c.doc_type if c else (spec.doc if spec else "rhp"),
            page=c.page if c else 0,
            printed_page=c.printed_page if c else None,
            bbox=c.bbox if c else None,
            extractor=c.extractor if c else "none",
            score=c.score if c else 0.0,
            verdict=f.verdict,
            reason_code=f.reason_code,
            reason=f.reason,
            companion=companion,
            checks=[FieldCheck(check=k.check, status=k.status, reason=k.reason) for k in f.checks],
            candidates=[
                ApiCandidate(
                    extractor=x.extractor,
                    doc=x.doc_type,
                    raw=x.raw,
                    value=x.value,
                    page=x.page,
                    score=x.score,
                )
                for x in f.candidates
            ],
        )

    # --------------------------------------------------- suggested questions
    def suggested(self, ipo_id: str) -> list[SuggestedQuestion]:
        self.get(ipo_id)
        fresh = _money_inr(self._xray(ipo_id), "fresh_issue_size")
        out: list[SuggestedQuestion] = []
        for q in _config("suggested_questions.yaml")["questions"]:
            text: str = q["text"]
            if "{fresh_lakh}" in text:
                number = _crore_number(fresh)
                if number is None:
                    continue
                text = text.replace("{fresh_lakh}", number)
            out.append(SuggestedQuestion(text=text, language=q["language"], kind=q["kind"]))
        return out


# ---------------------------------------------------------------------- helpers
def _companion(other: list[Candidate]) -> Companion | None:
    """The best candidate from the other document that has a real value (RHP ``[●]`` beside the
    Prospectus number)."""
    real = [x for x in other if x.value is not None and x.value.kind != "placeholder"]
    pool = real or other
    if not pool:
        return None
    best = max(pool, key=lambda x: x.score)
    return Companion(doc=best.doc_type, page=best.page, value=best.value)


def _money_inr(xray: XRay | None, field_id: str) -> str | None:
    """A field's amount in rupees: the RHP value, or the Prospectus one when the RHP is blank."""
    if xray is None:
        return None
    f = next((x for x in xray.fields if x.field_id == field_id), None)
    if f is None or f.chosen is None:
        return None
    candidates = [f.chosen, *[x for x in f.candidates if x.doc_type != f.chosen.doc_type]]
    for c in candidates:
        v = c.value
        if v is not None and v.kind == "money" and v.value_inr is not None:
            return str(v.value_inr)
    return None


def _crore_number(inr: str | None) -> str | None:
    """ "26260000000.00" -> "2,626": the rupee amount in crore, as a number only."""
    if inr is None:
        return None
    try:
        crore = Decimal(inr) / Decimal(10_000_000)
    except InvalidOperation:
        return None
    return f"{int(crore):,}"


@lru_cache(maxsize=16)
def _load_xray(path: str) -> XRay | None:
    p = Path(path)
    if not p.exists():
        return None
    return XRay.model_validate_json(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=2)
def _load_parsed(path: str) -> ParsedDoc | None:
    p = Path(path)
    if not p.exists():
        return None
    return ParsedDoc.model_validate_json(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=32)
def _load_sections(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    sections: list[dict[str, Any]] = json.loads(p.read_text(encoding="utf-8"))
    return sections
