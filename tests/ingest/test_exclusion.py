from pathlib import Path

import pytest

from finsight.ingest.exclusion import (
    excluded_names,
    is_excluded,
    load_gold_names,
    matches,
)


@pytest.mark.parametrize(
    ("corpus", "excluded", "hit"),
    [
        ("Urban Company Limited IPO", "Urban Company", True),
        ("urban company ltd.", "Urban Company Limited", True),
        ("Ather Energy Ltd", "Ather Energy Limited", True),
        ("Hexaware Technologies Limited", "Hexaware Technologies", True),
        ("LG Electronics India Limited", "LG Electronics India", True),
        ("Meesho Ltd", "Meesho Limited", True),
        ("Urbancompany Ltd", "Urban Company Limited", True),  # spacing typo
        ("Tata Capital Housing Finance", "Tata Capital Limited", False),  # different company
        ("Tata Motors Limited", "Tata Capital Limited", False),
        ("Groww Innovations", "Groww", True),  # extra word, one name inside the other
        ("Lenskart Solutions", "Lenskart", True),
        ("Ola Electric", "Ather Energy", False),
        ("Global Health", "Groww", False),
    ],
)
def test_matches(corpus: str, excluded: str, hit: bool) -> None:
    assert matches(corpus, excluded) is hit


def test_short_names_need_a_whole_word_not_a_substring() -> None:
    assert matches("Groww Innovations", "Groww")
    assert not matches("Growwell Industries", "Groww")


def test_load_gold_names_skips_comments_and_blanks(tmp_path: Path) -> None:
    f = tmp_path / "excluded_ipos.txt"
    f.write_text("# gold v2\n\nSwiggy Limited\n  Hyundai Motor India  \n# end\n", encoding="utf-8")
    assert load_gold_names(f) == ["Swiggy Limited", "Hyundai Motor India"]
    assert load_gold_names(tmp_path / "missing.txt") == []


def test_excluded_names_include_demo_and_gold(tmp_path: Path) -> None:
    f = tmp_path / "excluded_ipos.txt"
    f.write_text("Swiggy Limited\n", encoding="utf-8")
    names = excluded_names(f)
    assert "Swiggy Limited" in names
    assert any("Urban Company" in n for n in names)  # demo set from configs/demo_ipos.yaml
    assert len(names) >= 11


def test_is_excluded_reports_which_name_matched() -> None:
    names = ["Swiggy Limited", "Urban Company Limited"]
    assert is_excluded("Swiggy Ltd IPO", names) == "Swiggy Limited"
    assert is_excluded("Infosys", names) is None
