import json
import zipfile
from pathlib import Path

import openpyxl
import pytest

from finsight.ingest.corpus import (
    CorpusDoc,
    build_corpus,
    corpus_stats,
    ipo_slug,
    load_corpus_doc,
    page_texts,
)

RHP_COVER = "ACME LIMITED RED HERRING PROSPECTUS Please read Section 32 of the Companies Act"
PRO_COVER = "ACME LIMITED PROSPECTUS Dated March 1, 2019"
DRHP_COVER = "ACME LIMITED DRAFT RED HERRING PROSPECTUS Dated January 1, 2019"

TOC = "\n".join(
    [
        "TABLE OF CONTENTS",
        "THE OFFER ........................ 4",
        "CAPITAL STRUCTURE ................ 6",
        "OBJECTS OF THE OFFER .............. 8",
    ]
)

Row = tuple[str, str, str, str, str, dict[str, object]]


def _pages(cover: str, n: int = 12) -> dict[str, object]:
    pages: dict[str, object] = {"Page_0": [cover], "Page_1": [TOC], "Page_2": ["filler"]}
    pages["Page_3"] = ["THE OFFER\nThe offer is 100 shares"]
    pages["Page_4"] = ["CAPITAL STRUCTURE\nAuthorised capital 100 crore"]
    pages["Page_5"] = ["more capital"]
    pages["Page_6"] = ["OBJECTS OF THE OFFER\nNet proceeds"]
    for i in range(7, n):
        pages[f"Page_{i}"] = [f"body {i}"]
    return pages


def _make(tmp_path: Path, rows: list[Row]) -> Path:
    """rows: (mapping_key, issuer, company, year, json_name, pages). Returns the raw dir."""
    raw = tmp_path / "ipo_dataset"
    (raw / "texts_extracted_from_pdfs").mkdir(parents=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "data_ordered"
    ws.append(
        ["mapping_key", "Issuer Company", "Company Name", "Close Year", "Text_extracted_JSON",
         "Success_Flag"]
    )  # fmt: skip
    zip_path = raw / "texts_extracted_from_pdfs" / "ipo_mainline_txts_extracted.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for key, issuer, company, year, name, pages in rows:
            ws.append([key, issuer, company, year, f" {name}", "SECRET"])
            z.writestr(f"ipo_mainline_txts_extracted/{name}", json.dumps(pages))
    wb.save(raw / "ipo_mainline_final_data_v18.xlsx")
    return raw


def test_ipo_slug() -> None:
    assert ipo_slug("Edserv Softsystems Limited IPO", "2009") == "edserv-softsystems-2009"
    assert ipo_slug("Mahindra Holidays & Resorts India Ltd.", "2009") == (
        "mahindra-holidays-resorts-india-2009"
    )


def test_page_texts_orders_pages_numerically() -> None:
    obj = {"Page_10": ["ten"], "Page_2": ["two"], "Page_0": ["zero", ["nested"]]}
    assert page_texts(obj) == [(1, "zero nested"), (3, "two"), (11, "ten")]


def test_page_texts_reads_the_real_layout() -> None:
    page = [["image", "  ACME   LIMITED \n", "\n", "Line two\n"], ["fonts"], [""], [], []]
    assert page_texts({"Page_0": page}) == [(1, "ACME LIMITED\nLine two")]


def test_build_corpus_keeps_rhp_and_prospectus_and_drops_the_rest(tmp_path: Path) -> None:
    raw = _make(
        tmp_path,
        [
            ("1", "Acme Limited IPO", "acme ltd", "2019", "1_RHP.json", _pages(RHP_COVER)),
            ("2", "Beta Limited IPO", "beta ltd", "2018", "2.json", _pages(PRO_COVER)),
            ("3", "Gamma Limited IPO", "gamma", "2017", "3_DRHP.json", _pages(DRHP_COVER)),
            ("4", "Delta Limited IPO", "delta", "2016", "4.json", _pages("garbled text")),
            ("5", "Short Limited IPO", "short", "2015", "5.json", {"Page_0": [PRO_COVER]}),
        ],
    )
    out = tmp_path / "corpus"
    report = build_corpus(raw, out, excluded=[])
    assert sorted(p.name for p in out.glob("*.json")) == ["acme-2019.json", "beta-2018.json"]
    assert report.written == 2
    assert report.skipped == {"drhp": 1, "unknown": 1, "too_short": 1}
    doc = load_corpus_doc(out / "acme-2019.json")
    assert (doc.doc_kind, doc.company, doc.close_year, doc.mapping_key) == (
        "rhp", "Acme Limited", 2019, "1",
    )  # fmt: skip
    assert doc.n_pages == 12
    assert doc.pages[0].number == 1
    text = (out / "acme-2019.json").read_text(encoding="utf-8")
    assert "SECRET" not in text
    assert "Success_Flag" not in text


def test_sections_are_tagged_from_the_toc(tmp_path: Path) -> None:
    raw = _make(
        tmp_path, [("1", "Acme Limited IPO", "acme", "2019", "1_RHP.json", _pages(RHP_COVER))]
    )
    out = tmp_path / "corpus"
    build_corpus(raw, out, excluded=[])
    doc = load_corpus_doc(out / "acme-2019.json")
    by_id = {s.id: s for s in doc.sections}
    assert {"cover", "the_offer", "capital_structure", "objects_of_the_offer"} <= set(by_id)
    assert doc.key_sections_found is True
    assert "CAPITAL STRUCTURE" in doc.pages[by_id["capital_structure"].start_page - 1].text


def test_excluded_companies_are_not_written(tmp_path: Path) -> None:
    raw = _make(
        tmp_path,
        [
            ("1", "Urban Company Limited IPO", "urban", "2019", "1_RHP.json", _pages(RHP_COVER)),
            ("2", "Beta Limited IPO", "beta", "2018", "2.json", _pages(PRO_COVER)),
        ],
    )
    out = tmp_path / "corpus"
    report = build_corpus(raw, out, excluded=["Urban Company Limited"])
    assert [p.name for p in out.glob("*.json")] == ["beta-2018.json"]
    assert report.excluded == {"urban-company-2019": "Urban Company Limited"}


def test_slug_collisions_get_the_mapping_key(tmp_path: Path) -> None:
    raw = _make(
        tmp_path,
        [
            ("7", "Same Limited IPO", "same", "2019", "7_RHP.json", _pages(RHP_COVER)),
            ("8", "Same Limited IPO", "same", "2019", "8_RHP.json", _pages(PRO_COVER)),
        ],
    )
    out = tmp_path / "corpus"
    build_corpus(raw, out, excluded=[])
    assert sorted(p.name for p in out.glob("*.json")) == ["same-2019-8.json", "same-2019.json"]


def test_corpus_stats(tmp_path: Path) -> None:
    raw = _make(
        tmp_path,
        [
            ("1", "Acme Limited IPO", "acme", "2019", "1_RHP.json", _pages(RHP_COVER)),
            ("2", "Beta Limited IPO", "beta", "2018", "2.json", _pages(PRO_COVER)),
        ],
    )
    out = tmp_path / "corpus"
    report = build_corpus(raw, out, excluded=[])
    docs: list[CorpusDoc] = [load_corpus_doc(p) for p in sorted(out.glob("*.json"))]
    stats = corpus_stats(docs, report)
    assert stats["n_ipos"] == 2
    assert stats["by_doc_kind"] == {"prospectus": 1, "rhp": 1}
    assert stats["by_close_year"] == {"2018": 1, "2019": 1}
    assert stats["key_sections_found"] == "2/2"
    assert stats["skipped"] == {}


@pytest.mark.skipif(
    not Path("data/processed/corpus").exists(), reason="corpus not built (P1.5 hand-work)"
)
def test_real_corpus_has_no_demo_or_gold_ipo() -> None:
    from finsight.ingest.exclusion import excluded_names, is_excluded

    names = excluded_names(Path("data/gold/excluded_ipos.txt"))
    for path in Path("data/processed/corpus").glob("*.json"):
        doc = load_corpus_doc(path)
        assert is_excluded(doc.company, names) is None, doc.ipo_id
