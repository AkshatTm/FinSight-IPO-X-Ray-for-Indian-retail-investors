"""C1.3: the resumable batch runner (synthetic PDFs, fake processors, no real documents)."""

import hashlib
from datetime import date
from pathlib import Path

import pymupdf
import pytest
from make_fixture_pdf import build_offer_pdf, build_rhp_with_risks

from finsight.core.config import load_settings
from finsight.pipeline.batch import (
    DocResult,
    apply_results,
    cover_date,
    detect_exchange,
    load_state,
    looks_sme,
    process_one,
    run_batch,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Dated September 29, 2025. Please read", date(2025, 9, 29)),
        ("Dated: April 22, 2025", date(2025, 4, 22)),
        ("DATED - 3rd June, 2024", date(2024, 6, 3)),
        ("Dated this 14 March 2026", date(2026, 3, 14)),
        ("Dated: Jan 5, 2024", date(2024, 1, 5)),
        ("no date here", None),
    ],
)
def test_cover_date(text: str, expected: date | None) -> None:
    assert cover_date(text) == expected


def test_detect_exchange() -> None:
    both = "listed on BSE Limited and National Stock Exchange of India Limited"
    assert detect_exchange(both) == "both"
    assert detect_exchange("Designated Stock Exchange: NSE") == "NSE"
    assert detect_exchange("shares will be listed on BSE") == "BSE"
    assert detect_exchange("nothing") is None


def test_looks_sme() -> None:
    assert looks_sme("to be listed on the NSE Emerge platform of NSE")
    assert looks_sme("BSE SME")
    assert not looks_sme("BSE Limited and National Stock Exchange of India Limited")


def row(ipo: str, status: str = "downloaded", sha: str | None = None) -> dict[str, str]:
    return {
        "ipo_id": ipo, "company": ipo.title(), "exchange": "both", "doc_type": "rhp",
        "doc_date": "2025-09-30", "listing_date": "", "source_url": "https://x.test/" + ipo,
        "sha256": sha or hashlib.sha256(ipo.encode()).hexdigest(), "pages": "",
        "status": status, "reason": "",
    }  # fmt: skip


def fake(calls: list[str], bad: set[str] | None = None):
    def process(r: dict[str, str], pdf: Path, work: Path, settings: object) -> DocResult:
        calls.append(r["ipo_id"])
        if bad and r["ipo_id"] in bad:
            raise RuntimeError("boom")
        return DocResult(ipo_id=r["ipo_id"], status="parsed", pages=10, wall_s=1.0)

    return process


def quiet(msg: str) -> None:
    pass


def test_batch_is_resumable_and_isolates_failures(tmp_path: Path) -> None:
    rows = [row("a-2025"), row("b-2025"), row("c-2025", status="listed")]
    calls: list[str] = []
    state_path = tmp_path / "state.json"
    state = run_batch(
        rows, tmp_path, tmp_path / "w", None, state_path,
        process=fake(calls, bad={"a-2025"}), log=quiet,
    )  # fmt: skip
    assert calls == ["a-2025", "b-2025"]  # c-2025 was never downloaded
    assert state["a-2025"].status == "failed"
    assert state["a-2025"].reason.startswith("crashed: RuntimeError")
    assert state["b-2025"].status == "parsed"
    # a rerun skips finished documents ("failed" is final unless retried) and keeps the file
    again: list[str] = []
    run_batch(rows, tmp_path, tmp_path / "w", None, state_path, process=fake(again), log=quiet)
    assert again == []
    run_batch(
        rows, tmp_path, tmp_path / "w", None, state_path,
        retry_failed=True, process=fake(again), log=quiet,
    )  # fmt: skip
    assert again == ["a-2025"]
    assert load_state(state_path)["a-2025"].status == "parsed"


def test_limit_and_only(tmp_path: Path) -> None:
    rows = [row("a-2025"), row("b-2025"), row("c-2025")]
    calls: list[str] = []
    run_batch(
        rows, tmp_path, tmp_path, None, tmp_path / "s.json", limit=1, process=fake(calls), log=quiet
    )
    assert calls == ["a-2025"]
    run_batch(
        rows,
        tmp_path,
        tmp_path,
        None,
        tmp_path / "s2.json",
        only={"c-2025"},
        process=fake(calls),
        log=quiet,
    )
    assert calls[-1] == "c-2025"


def test_low_disk_stops_batch(tmp_path: Path) -> None:
    calls: list[str] = []
    run_batch(
        [row("a-2025")], tmp_path, tmp_path, None, tmp_path / "s.json",
        min_free_gb=10**9, process=fake(calls), log=quiet,
    )  # fmt: skip
    assert calls == []


def test_apply_results_updates_rows() -> None:
    rows = [row("a-2025"), row("b-2025"), row("c-2025")]
    state = {
        "a-2025": DocResult("a-2025", "parsed", pages=450, cover_date="2025-09-29", exchange="NSE"),
        "b-2025": DocResult("b-2025", "excluded", reason="SME issue"),
        "c-2025": DocResult("c-2025", "parsed", cover_date="2024-01-01"),  # far from posting date
    }
    assert apply_results(rows, state) == 3
    a, b, c = rows
    assert (a["status"], a["pages"], a["doc_date"], a["exchange"]) == (
        "parsed", "450", "2025-09-29", "NSE",
    )  # fmt: skip
    assert (b["status"], b["reason"]) == ("excluded", "SME issue")
    assert c["doc_date"] == "2025-09-30"  # implausible cover date is ignored


def test_manual_failed_rows_are_left_alone() -> None:
    r = row("m-2025", status="failed")
    r["reason"] = "manual: HTTP 404"
    assert apply_results([r], {"m-2025": DocResult("m-2025", "parsed")}) == 0


def _process(tmp_path: Path, pdf: Path, ipo: str = "acme-2025") -> DocResult:
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return process_one(row(ipo, sha=sha), pdf, tmp_path / "work", load_settings("dev_light"))


def test_process_one_parses_a_synthetic_rhp(tmp_path: Path) -> None:
    pdf = build_rhp_with_risks(tmp_path / "rhp.pdf")
    res = _process(tmp_path, pdf)
    assert res.status == "parsed", res.reason
    assert res.n_risks == 3
    assert "risk_factors" in res.sections
    assert res.cover_date == "2025-09-29"
    assert res.peak_rss_mb > 0
    assert res.output_bytes > 0
    assert set(res.timings_s) >= {"parsed", "sections", "risks_split"}
    store = tmp_path / "work" / "store" / "docs"
    assert not list(store.rglob("source.pdf"))  # the PDF copy is removed to save disk


def test_process_one_excludes_a_draft_and_a_scan(tmp_path: Path) -> None:
    drhp = _process(tmp_path, build_offer_pdf(tmp_path / "d.pdf", "drhp"), "drhp-2025")
    assert drhp.status == "excluded"
    assert "DRHP" in drhp.reason
    scan = _process(tmp_path, build_offer_pdf(tmp_path / "s.pdf", "scanned"), "scan-2025")
    assert scan.status == "excluded"
    assert "scanned" in scan.reason


def test_process_one_excludes_an_sme_cover(tmp_path: Path) -> None:
    pdf = tmp_path / "sme.pdf"
    build_rhp_with_risks(pdf)
    doc = pymupdf.open(pdf)
    doc[0].insert_text((72, 300), "To be listed on the NSE Emerge platform of NSE", fontsize=9)
    doc.saveIncr()
    doc.close()
    res = _process(tmp_path, pdf, "sme-2025")
    assert res.status == "excluded"
    assert "SME" in res.reason
