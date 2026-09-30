import json
from pathlib import Path

from finsight.core.schemas import Section
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.parse_stage import run_parse
from finsight.pipeline.sections_stage import (
    load_sections,
    run_sections,
    section_matrix,
    write_matrix,
)


def _s(sid: str, start: int) -> Section:
    return Section(id=sid, title=sid, start_page=start, end_page=start, method="toc", confidence=1)


def test_run_sections_writes_and_reloads(fixture_pdf: Path, tmp_path: Path) -> None:
    run_parse(fixture_pdf, tmp_path, "acme-2025", "prospectus", images=False)
    sections = run_sections(tmp_path, "acme-2025", "prospectus")
    out = doc_outputs(tmp_path, "acme-2025", "prospectus").sections
    assert out.name == "sections_prospectus.json"
    assert load_sections(tmp_path, "acme-2025", "prospectus") == sections
    assert sections[0].id == "cover"


def test_section_matrix_counts_documents_with_all_key_sections(tmp_path: Path) -> None:
    starts = {"cover": 1, "the_offer": 5, "capital_structure": 7, "objects_of_the_offer": 9}
    full = [_s(sid, start) for sid, start in starts.items()]
    matrix = section_matrix({("a-2025", "rhp"): full, ("b-2025", "rhp"): full[:2]})
    assert matrix["all_key_found"] == {"rhp": "1/2", "prospectus": "0/0"}
    docs = matrix["documents"]
    assert isinstance(docs, dict)
    assert docs["b-2025:rhp"]["key"]["objects_of_the_offer"] is None
    out = tmp_path / "sections.json"
    write_matrix(out, matrix)
    assert json.loads(out.read_text(encoding="utf-8"))["all_key_found"]["rhp"] == "1/2"
