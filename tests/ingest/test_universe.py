"""C1.1: SEBI listing parser, one-document-per-company logic and the committed universe CSV."""

from datetime import date
from pathlib import Path

import pytest

from finsight.ingest import list_demo_ipos
from finsight.ingest.universe import (
    SMID_FINAL,
    SMID_RHP,
    Entry,
    _decode,
    build_candidates,
    company_name,
    crawl,
    is_offer_document,
    name_key,
    parse_listing,
    parse_total,
)
from finsight.splits import load_universe

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "web"
SINCE = date(2024, 1, 1)


def entry(day: str, title: str, smid: int = SMID_RHP) -> Entry:
    return Entry(date.fromisoformat(day), title, f"https://example.test/{title}", smid)


def test_parse_listing_fixture() -> None:
    page = (FIX / "sebi_rhp_listing.html").read_text(encoding="utf-8")
    rows = parse_listing(page, SMID_RHP)
    assert len(rows) == 25
    assert rows[0].title == "Manipal Payment and Identity Solutions Limited - RHP"
    assert rows[0].posted == date(2026, 9, 4)
    assert rows[0].url.startswith("https://www.sebi.gov.in/filings/public-issues/")
    assert parse_total(page) == 1284
    assert any("Addendum" in r.title for r in rows)
    assert any("–" in r.title for r in rows)  # cp1252 en dash survived


def test_parse_final_listing_fixture() -> None:
    rows = parse_listing((FIX / "sebi_final_listing.html").read_text(encoding="utf-8"), SMID_FINAL)
    assert len(rows) == 25
    assert all(r.smid == SMID_FINAL for r in rows)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Rentomojo Limited - RHP", "Rentomojo Limited"),
        ("Pine Labs Limited-Prospectus", "Pine Labs Limited"),
        ("PNGS Reva Diamond Jewellery Limited RHP", "PNGS Reva Diamond Jewellery Limited"),
        ("Prospectus of Rashi Peripherals Limited", "Rashi Peripherals Limited"),
        ("Prospectus - Bajaj Housing Finance Limited", "Bajaj Housing Finance Limited"),
        ("Hexaware Technologies IPO", "Hexaware Technologies"),
        (
            "Bluestone Jewellery and Lifestyle Limited-IPO",
            "Bluestone Jewellery and Lifestyle Limited",
        ),
        ("Hexaware Technologies - Red Herring Prospectus", "Hexaware Technologies"),
        ("SYMBIOTEC PHARMALAB LIMITED – RHP", "SYMBIOTEC PHARMALAB LIMITED"),
    ],
)
def test_company_name(title: str, expected: str) -> None:
    assert company_name(title) == expected


def test_amendments_are_not_offer_documents() -> None:
    assert not is_offer_document(entry("2026-08-28", "Skyways Air Services Limited - Addendum II"))
    assert not is_offer_document(entry("2026-09-23", "Moneyview Limited - Corrigendum to RHP"))
    assert is_offer_document(entry("2026-09-21", "Moneyview Limited - RHP"))


def test_rhp_preferred_and_names_merged() -> None:
    entries = [
        entry("2026-09-04", "Manipal Payment and Identity Solutions Limited - RHP"),
        entry(
            "2026-09-21", "Manipal Payment & Identity Solutions Limited - Prospectus", SMID_FINAL
        ),
        entry("2026-09-22", "A One Steel Limited - RHP"),
        entry("2026-10-01", "A ONE Steels Limited - Prospectus", SMID_FINAL),
        entry("2026-09-23", "Moneyview Limited - Corrigendum to RHP"),
    ]
    out = build_candidates(entries, SINCE)
    assert [(c.company, c.doc_type) for c in out] == [
        ("Manipal Payment and Identity Solutions Limited", "rhp"),
        ("A One Steel Limited", "rhp"),
    ]
    assert out[0].ipo_id == "manipal-payment-and-identity-solutions-2026"


def test_prospectus_only_company_is_kept() -> None:
    out = build_candidates(
        [entry("2024-02-16", "Prospectus of Rashi Peripherals Limited", 12)], SINCE
    )
    assert [(c.ipo_id, c.doc_type) for c in out] == [("rashi-peripherals-2024", "prospectus")]


def test_company_first_filed_before_since_is_out() -> None:
    entries = [
        entry("2023-12-20", "Late Filer Limited - RHP"),
        entry("2024-01-05", "Late Filer Limited - Prospectus", SMID_FINAL),
    ]
    assert build_candidates(entries, SINCE) == []


def test_two_rhps_of_similar_names_stay_apart() -> None:
    entries = [
        entry("2025-03-01", "Alpha Steel Limited - RHP"),
        entry("2025-04-01", "Alpha Steels Limited - RHP"),
    ]
    assert len(build_candidates(entries, SINCE)) == 2


def test_same_name_same_year_gets_a_distinct_id() -> None:
    entries = [
        entry("2025-03-01", "Gamma Limited - RHP"),
        entry("2025-09-01", "Gamma Limited - RHP"),
    ]
    ids = [c.ipo_id for c in build_candidates(entries, SINCE)]
    assert len(ids) == len(set(ids))


def test_showcase_keeps_its_existing_id() -> None:
    entries = [entry("2025-10-20", "Billionbrains Garage Ventures Limited - RHP")]
    out = build_candidates(
        entries, SINCE, {name_key("Billionbrains Garage Ventures Limited"): "groww-2025"}
    )
    assert out[0].ipo_id == "groww-2025"


class FakeTransport:
    """Serves the fixture as page 1 and a generated older page for the AJAX calls."""

    def __init__(self) -> None:
        self.posts: list[dict[str, str]] = []

    def get(self, url: str) -> str:
        return (FIX / "sebi_rhp_listing.html").read_text(encoding="utf-8")

    def post(self, url: str, data: dict[str, str], referer: str) -> str:
        self.posts.append(data)
        row = (
            "<tr class='odd'><td>Jan 02, 2023</td><td><a href='https://x.test/old' "
            "title=\"t\" class='points'>Old Limited - RHP <br></a></a></td></tr>"
        )
        return f"<p>26 to 50 of 1284 records</p><table>{row}</table>"


def test_crawl_stops_once_entries_pass_since() -> None:
    t = FakeTransport()
    got = crawl(t, SMID_RHP, SINCE)
    assert len(t.posts) == 1  # the second page already reached 2023
    assert t.posts[0]["doDirect"] == "1"
    assert t.posts[0]["smid"] == "11"
    assert all(e.posted >= SINCE for e in got)
    assert len(got) == 25


def test_decode_falls_back_to_cp1252() -> None:
    assert _decode("A – B".encode("cp1252")) == "A – B"
    assert _decode("A – B".encode()) == "A – B"


def test_committed_universe_is_valid_and_has_showcase() -> None:
    rows = load_universe(ROOT / "configs" / "ipo_universe.csv")
    ids = {r.ipo_id for r in rows}
    assert {i.ipo_id for i in list_demo_ipos()} <= ids
    assert all(r.doc_date >= SINCE for r in rows)
    assert all("sebi.gov.in" in r.source_url for r in rows)
