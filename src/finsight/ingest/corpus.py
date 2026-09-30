"""Training corpus from the Ghosh et al. IPO dataset (ADR-016, 05 section 1.3).

Reads the pagewise text zip, keeps the RHP- and final-Prospectus-derived texts (judged by the
cover, not the file name), drops DRHP / unreadable / demo / gold-v2 texts, tags sections with
the P1.2 detector, and writes one ``data/processed/corpus/<ipo_id>.json`` per IPO.

    uv run python -m finsight.ingest.corpus build   # writes the corpus + corpus_stats.json

Only allow-listed Excel columns are read (never outcomes, listing-day or broker columns).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from finsight.core.config import get_settings
from finsight.core.schemas import Page, ParsedDoc, Section
from finsight.ingest.exclusion import excluded_names, is_excluded
from finsight.ingest.recon import _rows, classify_cover, flatten_text, normalize_company
from finsight.parse import KEY_SECTIONS, find_sections, read_printed_page

ZIP_NAME = Path("texts_extracted_from_pdfs") / "ipo_mainline_txts_extracted.zip"
EXCEL_NAME = "ipo_mainline_final_data_v18.xlsx"
MIN_PAGES = 10  # a real offer document is hundreds of pages; fewer means a broken extraction
FOOTER_LINES = 3

_PAGE_KEY = re.compile(r"^Page_(\d+)$")
DocKind = Literal["rhp", "prospectus"]


class CorpusPage(BaseModel):
    number: int  # 1-indexed
    text: str


class CorpusDoc(BaseModel):
    ipo_id: str
    mapping_key: str
    company: str
    close_year: int | None
    doc_kind: DocKind
    source_file: str
    n_pages: int
    pages: list[CorpusPage]
    sections: list[Section]
    key_sections_found: bool


@dataclass
class BuildReport:
    written: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    excluded: dict[str, str] = field(default_factory=dict)  # ipo_id -> matching excluded name

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1


def ipo_slug(company: str, close_year: str | int | None) -> str:
    """``("Edserv Softsystems Limited IPO", "2009")`` -> ``"edserv-softsystems-2009"``."""
    name = re.sub(r"[^a-z0-9]+", "-", normalize_company(company)).strip("-")
    return f"{name}-{close_year}" if close_year else name


def _lines(page: Any) -> str:
    """Text of one page. Real pages are ``[text_lines, fonts, ...]``; simple ones are strings."""
    if isinstance(page, list) and page and isinstance(page[0], list):
        items = [x for x in page[0] if isinstance(x, str) and x != "image"]
        text = "\n".join(items)
    else:
        return flatten_text(page)
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def page_texts(obj: dict[str, Any]) -> list[tuple[int, str]]:
    """``[(page_number, text)]`` ordered by page; ``Page_0`` is page 1."""
    numbered = sorted((int(m[1]), v) for k, v in obj.items() if (m := _PAGE_KEY.match(k)))
    return [(n + 1, _lines(v)) for n, v in numbered]


def _parsed(ipo_id: str, kind: DocKind, source: str, pages: list[tuple[int, str]]) -> ParsedDoc:
    """A text-only ``ParsedDoc`` (no boxes or fonts) so the P1.2 detector can tag sections."""
    built = [
        Page(
            number=n, width=0.0, height=0.0, words=[], text=text, is_scanned=False,
            printed_page=read_printed_page(text.splitlines()[-FOOTER_LINES:]),
        )
        for n, text in pages
    ]  # fmt: skip
    return ParsedDoc(ipo_id=ipo_id, doc_type=kind, source_path=source, n_pages=len(built),
                     pages=built, sha256="")  # fmt: skip


def load_corpus_doc(path: Path) -> CorpusDoc:
    return CorpusDoc.model_validate_json(path.read_text(encoding="utf-8"))


def build_corpus(raw_dir: Path, out_dir: Path, excluded: list[str]) -> BuildReport:
    """Write one corpus JSON per usable IPO to ``out_dir`` (``raw_dir`` = data/raw/ipo_dataset)."""
    header, rows = _rows(raw_dir / EXCEL_NAME)
    col = {name: i for i, name in enumerate(header)}
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.json"):  # a rebuild replaces the corpus, never mixes runs
        stale.unlink()
    report = BuildReport()
    used: set[str] = set()

    def cell(row: tuple[Any, ...], name: str) -> str:
        value = row[col[name]] if name in col else None
        return "" if value is None else str(value).strip()

    with zipfile.ZipFile(raw_dir / ZIP_NAME) as z:
        entries = {i.filename.rsplit("/", 1)[-1]: i for i in z.infolist()}
        for row in rows:
            issuer, short = cell(row, "Issuer Company"), cell(row, "Company Name")
            company = re.sub(r"\s+IPO\s*$", "", issuer or short, flags=re.IGNORECASE).strip()
            year, key = cell(row, "Close Year"), cell(row, "mapping_key")
            slug = ipo_slug(issuer or short, year)
            hit = is_excluded(issuer or short, excluded) or (
                is_excluded(short, excluded) if short else None
            )
            if hit:
                report.excluded[slug] = hit
                continue
            entry = entries.get(cell(row, "Text_extracted_JSON"))
            if entry is None:
                report.skip("missing_text")
                continue
            obj = json.loads(z.read(entry))
            pages = page_texts(obj)
            kind = classify_cover(flatten_text(obj.get("Page_0")))
            if kind in ("drhp", "unknown"):
                report.skip(kind)
                continue
            if len(pages) < MIN_PAGES:
                report.skip("too_short")
                continue
            if slug in used:
                slug = f"{slug}-{key}"
            used.add(slug)
            doc = _parsed(slug, kind, entry.filename, pages)
            sections = find_sections(doc)
            corpus = CorpusDoc(
                ipo_id=slug, mapping_key=key, company=company,
                close_year=int(year) if year.isdigit() else None, doc_kind=kind,
                source_file=entry.filename, n_pages=len(pages),
                pages=[CorpusPage(number=n, text=t) for n, t in pages], sections=sections,
                key_sections_found=set(KEY_SECTIONS) <= {s.id for s in sections},
            )  # fmt: skip
            (out_dir / f"{slug}.json").write_text(
                corpus.model_dump_json(), encoding="utf-8", newline="\n"
            )
            report.written += 1
    return report


def corpus_stats(docs: list[CorpusDoc], report: BuildReport) -> dict[str, object]:
    """Counts for ``eval_results/corpus_stats.json`` (per kind, per year, key-section coverage)."""
    by_kind: dict[str, dict[str, int]] = {}
    for kind in ("rhp", "prospectus"):
        mine = [d for d in docs if d.doc_kind == kind]
        by_kind[kind] = {"n": len(mine), "key_sections": sum(d.key_sections_found for d in mine)}
    pages = sorted(d.n_pages for d in docs)
    return {
        "n_ipos": len(docs),
        "by_doc_kind": {k: v["n"] for k, v in sorted(by_kind.items()) if v["n"]},
        "by_close_year": dict(sorted(Counter(str(d.close_year) for d in docs).items())),
        "key_sections_found": f"{sum(d.key_sections_found for d in docs)}/{len(docs)}",
        "key_sections_found_by_kind": {
            k: f"{v['key_sections']}/{v['n']}" for k, v in by_kind.items()
        },
        "one_text_per_ipo": len({d.mapping_key for d in docs}) == len(docs),
        "pages_p50": int(statistics.median(pages)) if pages else 0,
        "skipped": dict(sorted(report.skipped.items())),
        "excluded": dict(sorted(report.excluded.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the training corpus (P1.5)")
    parser.add_argument("command", choices=["build"])
    parser.parse_args(argv)
    settings = get_settings()
    out_dir = settings.paths.processed_dir / "corpus"
    report = build_corpus(settings.paths.raw_dir / "ipo_dataset", out_dir, excluded_names())
    docs = [load_corpus_doc(p) for p in sorted(out_dir.glob("*.json"))]
    stats = corpus_stats(docs, report)
    target = settings.paths.eval_dir / "corpus_stats.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(stats, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
