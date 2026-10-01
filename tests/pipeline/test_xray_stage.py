from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from finsight.core.schemas import DocType, Page, ParsedDoc, Section
from finsight.extract import FineTunedExtractor, RawAnswer
from finsight.ingest.registry import DemoIpo, DocFile
from finsight.pipeline.layout import doc_outputs, xray_path
from finsight.pipeline.rules_stage import run_rules
from finsight.pipeline.xray_stage import (
    load_xray,
    run_qa,
    run_xray,
    write_xray_summary,
    xray_summary,
)

IPO = "urban-company-2025"
RHP = (
    "PROMOTERS OF OUR COMPANY: ABHIRAJ SINGH BHAL, RAGHAV CHANDRA AND VARUN KHAITAN "
    "COMPRISING A FRESH ISSUE OF [●] EQUITY SHARES AGGREGATING UP TO ₹ 4,720 MILLION "
    "AND AN OFFER FOR SALE OF [●] EQUITY SHARES AGGREGATING UP TO ₹ 14,280 MILLION"
)
PRO = (
    "INITIAL PUBLIC OFFERING AT A PRICE OF ₹103^ PER EQUITY SHARE AGGREGATING TO "
    "₹ 19,000^ MILLION COMPRISING A FRESH ISSUE"
)


def write_doc(processed: Path, doc: DocType, text: str) -> None:
    out = doc_outputs(processed, IPO, doc)
    out.parsed.parent.mkdir(parents=True, exist_ok=True)
    page = Page(number=1, width=595, height=842, words=[], text=text, is_scanned=False)
    parsed = ParsedDoc(
        ipo_id=IPO, doc_type=doc, source_path="x.pdf", n_pages=1, sha256="0", pages=[page]
    )
    out.parsed.write_text(parsed.model_dump_json(), encoding="utf-8")
    out.sections.write_bytes(TypeAdapter(list[Section]).dump_json([]))
    run_rules(processed, IPO, doc)


def ipo() -> DemoIpo:
    doc = DocFile(file=Path("x.pdf"), pages=1, sha256="0", dated="October 1, 2025")
    return DemoIpo(ipo_id=IPO, company="Urban Company", split="dev", rhp=doc, prospectus=doc)


@pytest.fixture
def processed(tmp_path: Path) -> Path:
    write_doc(tmp_path, "rhp", RHP)
    write_doc(tmp_path, "prospectus", PRO)
    return tmp_path


def test_run_xray_writes_one_xray_from_both_documents(processed: Path) -> None:
    now = datetime(2026, 10, 1, tzinfo=UTC)
    xray = run_xray(processed, ipo(), now)
    assert xray_path(processed, IPO).exists()
    assert load_xray(processed, IPO) == xray
    by_id = {f.field_id: f for f in xray.fields}
    assert by_id["fresh_issue_size"].verdict == "verified"
    assert by_id["offer_price"].chosen is not None
    assert by_id["offer_price"].chosen.doc_type == "prospectus"  # type: ignore[union-attr]
    assert by_id["total_issue_size"].checks[0].status == "verified"
    assert xray.derived["fresh_share_pct"] == "24.84"
    assert by_id["objects_of_offer"].chosen is None


def test_missing_key_sections_are_reported(processed: Path) -> None:
    xray = run_xray(processed, ipo())
    face = next(f for f in xray.fields if f.field_id == "face_value")
    assert face.reason_code == "section_not_found"  # no capital_structure in these fixtures


def test_run_xray_needs_the_rules_stage_first(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_xray(tmp_path, ipo())
    with pytest.raises(FileNotFoundError, match="--stage xray"):
        load_xray(tmp_path, IPO)


def test_qa_candidates_are_merged_when_present(processed: Path) -> None:
    def answers(question: str, contexts: list[str]) -> list[RawAnswer | None]:
        out: list[RawAnswer | None] = []
        for ctx in contexts:
            i = ctx.find("4,720")
            out.append(RawAnswer("4,720", 0.9, i, i + 5) if i >= 0 else None)
        return out

    run_qa(processed, IPO, "rhp", [FineTunedExtractor(13, answerer=answers, models_dir=processed)])
    assert doc_outputs(processed, IPO, "rhp").candidates_qa.exists()
    xray = run_xray(processed, ipo())
    fresh = next(f for f in xray.fields if f.field_id == "fresh_issue_size")
    assert {c.extractor for c in fresh.candidates} == {"rules", "qa_finetuned"}
    assert "agree" in fresh.reason  # both read ₹ 4,720 million on the same page


def test_summary_counts_verdicts_and_checks(processed: Path, tmp_path: Path) -> None:
    summary = xray_summary([run_xray(processed, ipo())])
    fields = summary["fields"]
    assert summary["n_ipos"] == 1
    assert fields["fresh_issue_size"]["verdict:verified"] == 1  # type: ignore[index]
    assert fields["fresh_issue_size"]["has_value"] == 1  # type: ignore[index]
    assert summary["consistency"] == {  # type: ignore[comparison-overlap]
        IPO: {"total_equals_fresh_plus_ofs": "verified/verified"}
    }
    target = tmp_path / "out" / "xray_summary.json"
    write_xray_summary(target, summary)
    assert target.read_text(encoding="utf-8").endswith("\n")
