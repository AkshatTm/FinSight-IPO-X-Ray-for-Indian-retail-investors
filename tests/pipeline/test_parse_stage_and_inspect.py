import json
from pathlib import Path

import pytest

from finsight.core.schemas import ParsedDoc
from finsight.pipeline import inspect as insp
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.parse_stage import load_parsed, run_parse


@pytest.fixture(scope="module")
def built(fixture_pdf: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, ParsedDoc]:
    processed = tmp_path_factory.mktemp("processed")
    run_parse(fixture_pdf, processed, "acme-2025", "rhp", images=True, dpi=40)
    return processed, load_parsed(processed, "acme-2025", "rhp")


def test_layout_separates_the_two_documents(tmp_path: Path) -> None:
    rhp, pro = doc_outputs(tmp_path, "a", "rhp"), doc_outputs(tmp_path, "a", "prospectus")
    assert (rhp.parsed.name, rhp.pages_dir.name) == ("parsed.json", "pages")
    assert (pro.parsed.name, pro.pages_dir.name) == ("parsed_prospectus.json", "pages_prospectus")


def test_run_parse_writes_json_and_images(built: tuple[Path, ParsedDoc]) -> None:
    processed, doc = built
    out = doc_outputs(processed, "acme-2025", "rhp")
    assert out.parsed.exists()
    assert sorted(p.name for p in out.pages_dir.iterdir()) == [f"{n}.webp" for n in (1, 2, 3, 4)]
    assert doc.n_pages == 4


def test_run_parse_reports_counts(fixture_pdf: Path, tmp_path: Path) -> None:
    report = run_parse(fixture_pdf, tmp_path, "acme-2025", "prospectus", images=False)
    assert (report.pages, report.scanned_pages, report.pages_with_printed_number) == (4, 1, 2)
    assert not doc_outputs(tmp_path, "acme-2025", "prospectus").pages_dir.exists()


def test_load_parsed_explains_a_missing_build(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="pipeline build --ipo nope"):
        load_parsed(tmp_path, "nope", "rhp")


def test_stats_page_and_grep(built: tuple[Path, ParsedDoc]) -> None:
    _, doc = built
    assert "pages=4" in insp.stats(doc)[0]
    assert insp.page_lines(doc, 1)[1] == "RED HERRING PROSPECTUS"
    assert insp.page_lines(doc, 9) == ["page 9 out of range 1..4"]
    hits = insp.grep(doc, r"₹\s*800")
    assert hits[0].startswith("p1: ")
    assert insp.grep(doc, "zzz") == ["no match for 'zzz'"]


def test_output_is_capped() -> None:
    lines = insp._cap([f"line {i} " + "x" * 500 for i in range(100)])
    assert len(lines) == insp.MAX_LINES
    assert all(len(ln) <= insp.MAX_WIDTH for ln in lines)
    assert lines[-1].endswith("more lines cut")


def test_write_samples_caps_and_truncates(built: tuple[Path, ParsedDoc], tmp_path: Path) -> None:
    _, doc = built
    out = tmp_path / "samples" / "s.jsonl"
    assert insp.write_samples(doc, r"\w+", out) == insp.MAX_SAMPLES
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == insp.MAX_SAMPLES
    assert all(len(r["text"]) <= insp.SAMPLE_CHARS for r in rows)
    assert rows[0]["doc"] == "rhp"
