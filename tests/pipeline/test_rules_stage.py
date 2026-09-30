import json
from pathlib import Path

from pydantic import TypeAdapter

from finsight.core.schemas import Money, Page, ParsedDoc, Section
from finsight.extract import field_ids
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.rules_stage import load_candidates, rules_summary, run_rules

IPO = "urban-company-2025"
COVER = (
    "PROMOTERS OF OUR COMPANY: ABHIRAJ SINGH BHAL, RAGHAV CHANDRA AND VARUN KHAITAN "
    "EQUITY SHARES OF FACE VALUE OF ₹1 EACH COMPRISING A FRESH ISSUE OF [●] EQUITY SHARES "
    "AGGREGATING UP TO ₹ 4,720 MILLION"
)


def write_inputs(processed: Path) -> None:
    out = doc_outputs(processed, IPO, "rhp")
    out.parsed.parent.mkdir(parents=True)
    page = Page(number=1, width=595, height=842, words=[], text=COVER, is_scanned=False)
    doc = ParsedDoc(
        ipo_id=IPO, doc_type="rhp", source_path="x.pdf", n_pages=1, sha256="0", pages=[page]
    )
    out.parsed.write_text(doc.model_dump_json(), encoding="utf-8")
    sections = TypeAdapter(list[Section]).dump_json([])
    out.sections.write_bytes(sections)


def test_run_rules_writes_and_reloads_candidates(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    found = run_rules(tmp_path, IPO, "rhp")
    assert list(found) == field_ids()
    money = found["fresh_issue_size"][0].value
    assert isinstance(money, Money)
    assert money.value_inr == 4_720_000_000
    assert found["objects_of_offer"] == []  # no tables file: the table extractor finds nothing
    assert load_candidates(tmp_path, IPO, "rhp")["promoters"][0].page == 1
    assert doc_outputs(tmp_path, IPO, "rhp").candidates.name == "candidates_rules.json"
    assert doc_outputs(tmp_path, IPO, "prospectus").candidates.name == (
        "candidates_rules_prospectus.json"
    )


def test_summary_counts_documents_with_a_candidate_per_field(tmp_path: Path) -> None:
    write_inputs(tmp_path)
    summary = rules_summary({(IPO, "rhp"): run_rules(tmp_path, IPO, "rhp")})
    coverage = summary["documents_with_a_candidate_per_field"]
    assert coverage["rhp"]["fresh_issue_size"] == 1  # type: ignore[index]
    assert coverage["rhp"]["registrar"] == 0  # type: ignore[index]
    docs = summary["documents"]
    assert docs[f"{IPO}:rhp"]["fresh_issue_size"]["page"] == 1  # type: ignore[index]
    json.dumps(summary)  # serialisable
