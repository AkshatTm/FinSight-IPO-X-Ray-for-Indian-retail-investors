import time

import pytest

from finsight.core.ids import make_ipo_id, new_trace_id, parse_passage_id, passage_id


def test_trace_ids_are_26_char_ulids_sortable_by_time() -> None:
    first = new_trace_id()
    time.sleep(0.005)
    second = new_trace_id()
    assert len(first) == 26
    assert first.isalnum()
    assert first < second


@pytest.mark.parametrize(
    ("company", "year", "expected"),
    [
        ("Acme Industries Ltd", 2025, "acme-industries-2025"),
        ("HDB Financial Services Limited", 2025, "hdb-financial-services-2025"),
        ("LG Electronics India Ltd.", 2025, "lg-electronics-india-2025"),
        ("  Tata   Capital  Limited ", 2025, "tata-capital-2025"),
        ("Meesho Limited", 2025, "meesho-2025"),
        ("Ather Energy Limited", 2025, "ather-energy-2025"),
    ],
)
def test_make_ipo_id_slugs_company_and_year(company: str, year: int, expected: str) -> None:
    assert make_ipo_id(company, year) == expected


def test_rhp_passage_ids_use_the_documented_format() -> None:
    assert passage_id("acme-2025", "rhp", 12, 3) == "acme-2025:p12:c3"


def test_prospectus_passage_ids_do_not_collide_with_rhp() -> None:
    assert passage_id("acme-2025", "prospectus", 12, 3) == "acme-2025:prospectus:p12:c3"
    assert passage_id("acme-2025", "prospectus", 12, 3) != passage_id("acme-2025", "rhp", 12, 3)


@pytest.mark.parametrize("doc_type", ["rhp", "prospectus"])
def test_passage_id_round_trip(doc_type: str) -> None:
    pid = passage_id("acme-2025", doc_type, 67, 0)  # type: ignore[arg-type]
    assert parse_passage_id(pid) == ("acme-2025", doc_type, 67, 0)


@pytest.mark.parametrize("bad", ["", "acme", "acme:p12", "acme:x12:c0", "acme:p12:cx"])
def test_parse_passage_id_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError, match="passage id"):
        parse_passage_id(bad)
