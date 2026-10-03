"""Load the real-section fixture pack (B-ADR-15) as the project's own models.

Used by cloud sessions and tests instead of the PDFs. ``load_doc`` returns a ``ParsedDoc``
holding only the exported pages (page ``number`` is the real PDF page, so ``pages[k]`` is *not*
page ``k + 1``; use ``page_map``), its sections, and the pre-extracted tables.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from finsight.core.schemas import Page, ParsedDoc, Section, Table, TableCell, Word

ROOT = Path(__file__).resolve().parent


def _read(path: Path) -> Any:
    with gzip.open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def ipo_ids() -> list[str]:
    return sorted(p.name for p in ROOT.iterdir() if (p / "rhp.pages.json.gz").exists())


def raw(ipo_id: str, doc_type: str = "rhp") -> dict[str, Any]:
    return _read(ROOT / ipo_id / f"{doc_type}.pages.json.gz")


def _page(d: dict[str, Any]) -> Page:
    words = [
        Word(text=w[0], bbox=(w[1], w[2], w[3], w[4]), font_size=w[5], bold=bool(w[6]))
        for w in d["words"]
    ]
    return Page(number=d["number"], printed_page=d["printed_page"], width=d["width"],
                height=d["height"], words=words, text=d["text"], is_scanned=False)  # fmt: skip


def load_doc(ipo_id: str, doc_type: str = "rhp") -> ParsedDoc:
    d = raw(ipo_id, doc_type)
    return ParsedDoc(ipo_id=ipo_id, doc_type=doc_type, source_path="fixture", n_pages=d["n_pages"],
                     pages=[_page(p) for p in d["pages"]], sha256=d["sha256"])  # fmt: skip


def load_sections(ipo_id: str, doc_type: str = "rhp") -> list[Section]:
    return [Section(**s) for s in raw(ipo_id, doc_type)["sections"]]


def kept_pages(ipo_id: str, doc_type: str = "rhp") -> dict[str, list[int]]:
    """Label (section id, ``cash_flows``, ``auditors_report``) -> exported PDF pages."""
    return raw(ipo_id, doc_type)["kept"]


def page_map(doc: ParsedDoc) -> dict[int, Page]:
    return {p.number: p for p in doc.pages}


def load_tables(ipo_id: str, doc_type: str = "rhp") -> list[Table]:
    out = []
    for t in raw(ipo_id, doc_type)["tables"]:
        cells = [
            TableCell(
                row=c[0], col=c[1], text=c[2], bbox=(c[3], c[4], c[5], c[6]), page=t["pages"][0]
            )
            for c in t["cells"]
        ]
        out.append(Table(id=t["id"], section_id=t["section_id"], pages=t["pages"],
                         header_scale=None, cells=cells))  # fmt: skip
    return out


def corpus_risk_factors() -> dict[str, str]:
    """ipo_id -> Risk Factors text of 20 corpus IPOs (pages joined by form feed)."""
    out = {}
    for p in sorted((ROOT / "corpus_risk_factors").glob("*.txt.gz")):
        with gzip.open(p, "rb") as fh:
            out[p.name.removesuffix(".txt.gz")] = fh.read().decode("utf-8")
    return out


def corpus_stats() -> dict[str, Any]:
    return json.loads((ROOT / "corpus_stats.json").read_text(encoding="utf-8"))


def fake_risks() -> list[dict[str, str]]:
    path = ROOT / "fake_training" / "risks_20.jsonl"
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln]


# Which exported page labels each red-flag check reads (README table; B05 section 5.4).
RF_SOURCES: dict[str, tuple[str, ...]] = {
    "RF01": ("summary_financial_information",),
    "RF02": ("cash_flows", "summary_financial_information"),
    "RF03": ("summary_financial_information",),
    "RF04": ("the_offer", "objects_of_the_offer"),
    "RF05": ("basis_for_offer_price",),
    "RF06": ("capital_structure",),
    "RF07": ("objects_of_the_offer",),
    "RF08": ("outstanding_litigation", "summary"),
    "RF09": ("summary_financial_information", "restated_financial_information"),
    "RF10": ("risk_factors", "summary"),
    "RF11": ("basis_for_offer_price",),
    "RF12": ("auditors_report", "summary_financial_information"),
    "RF13": ("capital_structure",),
}


def rf_coverage() -> dict[str, list[str]]:
    """Check -> IPO ids whose RHP export has >= 1 page for the check's sources."""
    out: dict[str, list[str]] = {rf: [] for rf in RF_SOURCES}
    for ipo in ipo_ids():
        kept = kept_pages(ipo)
        for rf, labels in RF_SOURCES.items():
            if any(kept.get(label) for label in labels):
                out[rf].append(ipo)
    return out
