"""Write the real-section fixture pack for cloud sessions (B-ADR-15, B11 section 3).

Local only: reads ``data/processed/`` (parsed.json, corpus) and ``data/raw/`` (PDFs, for tables),
writes ``tests/fixtures/real/``. Never writes a PDF or weights. Gzip JSON, <= 5 MB per file,
<= 20 MB in total (checked at the end).

    uv run python scripts/export_fixtures.py            # all 10 IPOs + corpus + samples
    uv run python scripts/export_fixtures.py --ipo ather-energy-2025 --skip-corpus
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finsight.core.schemas import Page, ParsedDoc, Section  # noqa: E402
from finsight.parse.sections import find_sections, find_subsection_pages  # noqa: E402
from finsight.parse.tables import pymupdf_backend  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "real"
PROCESSED = ROOT / "data" / "processed"
MAX_FILE_MB = 5
MAX_TOTAL_MB = 20

# Pages kept per section (from the section start); None = the whole section.
RHP_PAGES: dict[str, int | None] = {
    "cover": 4,
    "summary": None,
    "the_offer": None,
    "summary_financial_information": None,
    "capital_structure": 15,
    "objects_of_the_offer": 20,
    "basis_for_offer_price": None,
    "risk_factors": None,
    "financial_indebtedness": 4,
    "outstanding_litigation": 12,
}
PROSPECTUS_PAGES: dict[str, int | None] = {
    "cover": 4,
    "the_offer": None,
    "basis_for_offer_price": None,
}
# Sections whose pages also get pre-extracted tables (risk text has none worth keeping).
TABLE_SECTIONS = {
    "the_offer", "summary_financial_information", "capital_structure",
    "objects_of_the_offer", "basis_for_offer_price", "financial_indebtedness",
    "outstanding_litigation", "restated_financial_information", "summary",
}  # fmt: skip
MAX_TABLE_PAGES = 90
CORPUS_N = 20
CORPUS_MAX_PAGES = 140


def _dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(path, "wb", mtime=0) as fh:  # mtime=0: byte-identical re-runs
        fh.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    print(f"  {path.relative_to(ROOT)}  {path.stat().st_size / 1e6:.2f} MB")


def _page_dict(page: Page) -> dict[str, Any]:
    return {
        "number": page.number,
        "printed_page": page.printed_page,
        "width": round(page.width, 1),
        "height": round(page.height, 1),
        "text": page.text,
        # [text, x0, y0, x1, y1, font_size, bold]
        "words": [
            [w.text, *(round(v, 1) for v in w.bbox), round(w.font_size, 1), int(w.bold)]
            for w in page.words
        ],
    }


def _select(
    sections: list[Section], subsections: dict[str, list[int]], caps: dict[str, int | None]
) -> tuple[dict[str, list[int]], dict[str, str]]:
    """label -> pages kept; page -> label of the first label that claims it (for tables)."""
    kept: dict[str, list[int]] = {}
    for sec in sections:
        if sec.id in caps:
            cap = caps[sec.id]
            last = sec.end_page if cap is None else min(sec.end_page, sec.start_page + cap - 1)
            kept[sec.id] = list(range(sec.start_page, last + 1))
    for label, pages in subsections.items():
        kept[label] = pages
        if pages and "restated_financial_information" not in kept:
            kept["restated_financial_information"] = []
    return kept, {}


def _tables(pdf: Path, doc: ParsedDoc, kept: dict[str, list[int]]) -> list[dict[str, Any]]:
    wanted: dict[int, str] = {}
    for label, pages in kept.items():
        if label in TABLE_SECTIONS or label in ("cash_flows", "auditors_report"):
            for n in pages:
                wanted.setdefault(n, "restated_financial_information"
                                  if label in ("cash_flows", "auditors_report") else label)  # fmt: skip
    pages = sorted(wanted)[:MAX_TABLE_PAGES]
    per_page: dict[int, int] = {}
    tables = []
    for n, cells in pymupdf_backend(pdf, pages):
        k = per_page.get(n, 0)
        per_page[n] = k + 1
        tables.append(
            {
                "id": f"{doc.doc_type}:{wanted[n]}:p{n}:t{k}",
                "section_id": wanted[n],
                "pages": [n],
                "cells": [[c.row, c.col, c.text, *(round(v, 1) for v in c.bbox)] for c in cells],
            }
        )
    return tables


def export_doc(ipo_id: str, doc_type: str, source: str, pdf: Path) -> None:
    parsed = PROCESSED / ipo_id / ("parsed.json" if doc_type == "rhp" else "parsed_prospectus.json")
    doc = ParsedDoc.model_validate_json(parsed.read_text(encoding="utf-8"))
    sections = find_sections(doc)  # re-run: the finder now knows the financial sections
    sub = find_subsection_pages(doc, sections) if doc_type == "rhp" else {}
    kept, _ = _select(sections, sub, RHP_PAGES if doc_type == "rhp" else PROSPECTUS_PAGES)
    numbers = sorted({n for pages in kept.values() for n in pages})
    payload = {
        "ipo_id": ipo_id,
        "doc_type": doc_type,
        "source": source,
        "n_pages": doc.n_pages,
        "sha256": doc.sha256,
        "sections": [s.model_dump() for s in sections],
        "kept": kept,
        "pages": [_page_dict(doc.pages[n - 1]) for n in numbers],
        "tables": _tables(pdf, doc, kept) if pdf.exists() else [],
    }
    _dump(OUT / ipo_id / f"{doc_type}.pages.json.gz", payload)


# ------------------------------------------------------------------------- corpus
def _risk_text(path: Path) -> tuple[str, str] | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    sec = next((s for s in data.get("sections", []) if s["id"] == "risk_factors"), None)
    if sec is None or data.get("doc_kind") != "rhp":
        return None
    pages = [p for p in data["pages"] if sec["start_page"] <= p["number"] <= sec["end_page"]]
    if not 5 <= len(pages) <= CORPUS_MAX_PAGES:
        return None
    text = "\n\f\n".join(p["text"] for p in pages)
    return str(data.get("close_year", "")), text


def export_corpus() -> None:
    by_year: dict[str, list[Path]] = {}
    for path in sorted((PROCESSED / "corpus").glob("*.json")):
        m = re.search(r"-(\d{4})\.json$", path.name)
        if m:
            by_year.setdefault(m.group(1), []).append(path)
    pools = {y: iter(files) for y, files in sorted(by_year.items())}
    chosen: list[tuple[Path, str]] = []
    while len(chosen) < CORPUS_N and pools:
        for year in list(pools):  # round-robin over years -> stratified, deterministic
            for path in pools[year]:
                got = _risk_text(path)
                if got:
                    chosen.append((path, got[1]))
                    break
            else:
                del pools[year]
            if len(chosen) >= CORPUS_N:
                break
    index = []
    for path, text in chosen:
        name = path.stem
        out = OUT / "corpus_risk_factors" / f"{name}.txt.gz"
        out.parent.mkdir(parents=True, exist_ok=True)
        with gzip.GzipFile(out, "wb", mtime=0) as fh:
            fh.write(text.encode("utf-8"))
        index.append({"ipo_id": name, "year": name[-4:], "chars": len(text)})
    (OUT / "corpus_risk_factors" / "index.json").write_text(
        json.dumps(index, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"  corpus_risk_factors: {len(index)} files, years {sorted({i['year'] for i in index})}")


# ------------------------------------------------------------------------- samples, fake set
def export_samples(ipos: list[str]) -> None:
    for ipo_id in ipos[:2]:
        d = PROCESSED / ipo_id
        parsed = json.loads((d / "parsed.json").read_text(encoding="utf-8"))
        parsed["pages"] = parsed["pages"][:12]  # cover + TOC: shape sample, not the document
        parsed["_note"] = (
            "truncated to the first 12 pages; full pages are in <ipo>/rhp.pages.json.gz"
        )
        _dump(OUT / "samples" / f"parsed_{ipo_id}.json.gz", parsed)
        xray = d / "xray.json"
        if xray.exists():
            _dump(OUT / "samples" / f"xray_{ipo_id}.json.gz", json.loads(xray.read_text("utf-8")))


FAKE_RISKS = [
    (
        "operations",
        "We depend on a single manufacturing facility",
        "All of our output comes from one plant. A fire or long outage would stop sales.",
        "One factory makes everything the company sells. If it shuts down for long, sales stop.",
    ),
    (
        "financial",
        "We have incurred losses in recent years",
        "We reported net losses in each of the last three fiscal years and may not become profitable.",
        "The company lost money in each of the last three years and may keep losing money.",
    ),
    (
        "regulatory",
        "Our licences may not be renewed",
        "Our operations need licences that are renewed periodically; renewal is not assured.",
        "The company needs licences to operate. They must be renewed, and renewal is not guaranteed.",
    ),
    (
        "customers_suppliers",
        "A few customers account for most of our revenue",
        "Our top five customers contributed 71% of revenue from operations.",
        "Five customers bring in 71% of revenue. Losing one would hurt.",
    ),
    (
        "legal_litigation",
        "We are party to legal proceedings",
        "Outstanding proceedings against us involve an aggregate amount of ₹ 120 million.",
        "The company faces court cases involving about ₹ 120 million in total.",
    ),
    (
        "promoters_governance",
        "Our promoters will keep control after the offer",
        "After the Offer our promoters will hold 58% and can influence shareholder votes.",
        "The promoters will still own 58% and can sway most shareholder decisions.",
    ),
    (
        "market_macro",
        "The offer price may not reflect the market value",
        "The price was set by book building and may differ from the price at which shares trade.",
        "The offer price is set by bidding; the share may later trade at a very different price.",
    ),
    (
        "operations",
        "We depend on key managerial personnel",
        "Our senior management team has been with us for years and is hard to replace.",
        "A few senior people run the business and would be hard to replace.",
    ),
]


def export_fake_training() -> None:
    path = OUT / "fake_training" / "risks_20.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(20):
        cat, title, body, simple = FAKE_RISKS[i % len(FAKE_RISKS)]
        rows.append({"rid": f"fake:{i:02d}", "title": title, "body": body, "category": cat,
                     "simple": simple, "label_source": "synthetic"})  # fmt: skip
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", "utf-8", newline="\n"
    )
    print(f"  {path.relative_to(ROOT)}  {len(rows)} rows (synthetic, not real risks)")


def check_sizes() -> None:
    total = 0.0
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            mb = p.stat().st_size / 1e6
            total += mb
            if p.suffix == ".pdf" or mb > MAX_FILE_MB:
                raise SystemExit(f"fixture rule broken: {p} ({mb:.1f} MB)")
    print(f"pack size: {total:.2f} MB (limit {MAX_TOTAL_MB} MB)")
    if total > MAX_TOTAL_MB:
        raise SystemExit("pack is over the total limit")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ipo", action="append", help="only these IPO ids")
    ap.add_argument("--skip-corpus", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "configs" / "demo_ipos.yaml").read_text(encoding="utf-8"))
    ipos = [i["ipo_id"] for i in cfg["ipos"] if not args.ipo or i["ipo_id"] in args.ipo]
    for ipo_id in ipos:
        print(ipo_id)
        entry = next(i for i in cfg["ipos"] if i["ipo_id"] == ipo_id)
        for kind in ("rhp", "prospectus"):
            export_doc(ipo_id, kind, entry[kind]["doc_id"], ROOT / entry[kind]["file"])
    if not args.skip_corpus:
        export_corpus()
        shutil_copy = ROOT / "eval_results" / "corpus_stats.json"
        (OUT / "corpus_stats.json").write_bytes(shutil_copy.read_bytes())
    export_samples(ipos)
    export_fake_training()
    check_sizes()


if __name__ == "__main__":
    main()
