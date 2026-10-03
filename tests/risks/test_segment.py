"""B2.1a: risk segmentation on synthetic pages (bold / numbered / mixed) and corpus text.
Golden tests on real fixture pages of 3 dev IPOs follow with the B0.4 fixture pack."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from finsight.core.schemas import BBox, Page, Word
from finsight.parse import parse_pdf
from finsight.risks.segment import (
    body_lines,
    first_sentence,
    page_lines,
    segment_pages,
    segment_text,
    to_risks,
)

W, H = 595.0, 842.0
LEFT = 72.0


class PageBuilder:
    """Lay out lines of (text, bold) runs on a synthetic page, 14 pt apart."""

    def __init__(self, number: int, header: str | None = "ACME LIMITED", footer: bool = True):
        self.number, self.words, self.y = number, [], 140.0
        if header:
            self._run([(header, False)], 40.0, LEFT, 8.0)
        if footer:
            self._run([(str(number), False)], 810.0, 290.0, 9.0)

    def _run(self, runs: list[tuple[str, bool]], y: float, x: float, size: float = 10.0) -> None:
        for text, bold in runs:
            for token in text.split():
                width = 5.0 * len(token)
                self.words.append(
                    Word(text=token, bbox=(x, y, x + width, y + size), font_size=size, bold=bold)
                )
                x += width + 3.0

    def line(self, *runs: tuple[str, bool], x: float = LEFT) -> PageBuilder:
        self._run(list(runs), self.y, x)
        self.y += 14.0
        return self

    def gap(self) -> PageBuilder:
        self.y += 14.0
        return self

    def page(self) -> Page:
        return Page(
            number=self.number, width=W, height=H, words=self.words, text="", is_scanned=False
        )


def b(text: str) -> tuple[str, bool]:
    return (text, True)


def r(text: str) -> tuple[str, bool]:
    return (text, False)


PREAMBLE = r("An investment in equity shares involves a high degree of risk. Read carefully.")


def bold_doc() -> list[Page]:
    p1 = (
        PageBuilder(10)
        .line(PREAMBLE)
        .line(b("Investors should read this whole section before deciding anything."))
        .line(r("This is the rest of the preamble paragraph."))
        .gap()
        .line(b("Internal Risks"))
        .gap()
        .line(b("We depend on a small number of customers for a large share"))
        .line(b("of our revenue."))
        .line(r("In Fiscal 2025, our top 10 customers contributed 61.2% of revenue."))
        .line(r("Losing any of them could affect us."))
        .gap()
        .line(b("Our promoters have pledged some of their shares with lenders."), r("As of"))
        .line(r("30 June 2025, 12% of promoter shares were pledged."))
    )
    p2 = (
        PageBuilder(11)
        .line(r("The lenders may sell these shares if we default."))
        .gap()
        .line(b("External Risks"))
        .gap()
        .line(b("Changes in interest rates in India could raise our costs."))
        .line(r("Our borrowings carry floating rates."))
    )
    return [p1.page(), p2.page(), PageBuilder(12).line(r("Closing text of the section.")).page()]


def test_bold_titles_groups_preamble_and_page_break_merge() -> None:
    spans = segment_pages(bold_doc())
    assert [s.title for s in spans] == [
        "We depend on a small number of customers for a large share of our revenue.",
        "Our promoters have pledged some of their shares with lenders.",
        "Changes in interest rates in India could raise our costs.",
    ]
    assert [s.group for s in spans] == ["Internal Risks", "Internal Risks", "External Risks"]
    first, pledge, rates = spans
    assert first.body == (
        "In Fiscal 2025, our top 10 customers contributed 61.2% of revenue. "
        "Losing any of them could affect us."
    )
    # A run-in title: the body starts on the title's own line, and continues on the next page.
    assert pledge.body.startswith("As of 30 June 2025, 12% of promoter shares were pledged.")
    assert "The lenders may sell these shares if we default." in pledge.body
    assert (pledge.page_start, pledge.page_end) == (10, 11)
    # Running header, page numbers and the bold preamble line never become risks or body text.
    assert "ACME" not in " ".join(s.body for s in spans)
    assert rates.body.endswith("Closing text of the section.")
    assert all(not s.numbered for s in spans)


def numbered_doc() -> list[Page]:
    p = (
        PageBuilder(20)
        .line(PREAMBLE)
        .gap()
        .line(r("1."), b("Our business depends on licences that may not be renewed."))
        .line(r("We hold 14 licences that expire within two years."))
        .gap()
        .line(b("2."), b("We have had negative cash flows from operating activities in the past"))
        .line(b("and may have them again."))
        .line(r("Net cash used in operating activities was ₹ 45.2 million in Fiscal 2024."))
    )
    return [p.page(), PageBuilder(21).page(), PageBuilder(22).page()]


def test_numbered_titles_without_group_headings() -> None:
    spans = segment_pages(numbered_doc())
    assert [s.title for s in spans] == [
        "Our business depends on licences that may not be renewed.",
        "We have had negative cash flows from operating activities in the past and may have "
        "them again.",
    ]
    assert all(s.numbered and s.confidence > 0.8 for s in spans)
    assert spans[1].body.startswith("Net cash used")


def mixed_doc() -> tuple[list[Page], dict[int, list[BBox]]]:
    p = (
        PageBuilder(30)
        .line(b("Risks Relating to the Offer"))
        .gap()
        .line(b("The price of our equity shares may be volatile after listing."))
        .line(r("The table below shows our past share issues."))
        .line(b("Date of allotment Number of shares Issue price"))  # bold table header
        .line(r("12 March 2024 1,000,000 10.00"))
        .gap()
        .line(b("Short bold line."))  # < 5 words: not a title
        .line(r("More body text."))
        .gap()
        .line(b("This bold sentence is indented and not a title."), r("x"), x=LEFT + 60)
        .gap()
        .line(b("Our"), r("title stops after one bold word so this is only body text."))
        .gap()
        .line(b("We may not pay dividends in the foreseeable future."))
        .line(r("Dividends depend on our profits."))
    )
    page = p.page()
    table = (LEFT - 2, 194.0, W - LEFT, 222.0)  # covers the header and the data row
    return [page, PageBuilder(31).page(), PageBuilder(32).page()], {30: [table]}


def test_mixed_tables_short_indented_and_one_word_bold_are_not_titles() -> None:
    pages, tables = mixed_doc()
    spans = segment_pages(pages, tables)
    assert [s.title for s in spans] == [
        "The price of our equity shares may be volatile after listing.",
        "We may not pay dividends in the foreseeable future.",
    ]
    assert spans[0].group == "Risks Relating to the Offer"
    first = spans[0].body
    assert "Date of allotment" not in first
    assert "Short bold line. More body text." in first
    assert "This bold sentence is indented" in first
    assert "title stops after one bold word" in first


def test_without_table_boxes_a_bold_table_header_would_start_a_risk() -> None:
    pages, _ = mixed_doc()
    assert len(segment_pages(pages)) == 3  # why the table boxes matter


def test_a_long_bold_paragraph_without_a_full_stop_is_not_a_title() -> None:
    p = PageBuilder(40).line(b("Internal Risks"))
    for _ in range(4):
        p.line(b("bold words that keep going on and on across lines"))
    p.line(r("regular text"))
    assert segment_pages([p.page(), PageBuilder(41).page(), PageBuilder(42).page()]) == []


def test_lines_group_words_by_height_and_sort_left_to_right() -> None:
    page = Page(
        number=1, width=W, height=H, text="", is_scanned=False,
        words=[
            Word(text="b", bbox=(120, 100, 130, 110), font_size=10, bold=False),
            Word(text="a", bbox=(72, 101, 80, 111), font_size=10, bold=True),
            Word(text="c", bbox=(72, 130, 80, 140), font_size=10, bold=False),
        ],
    )  # fmt: skip
    assert [ln.text for ln in page_lines(page)] == ["a b", "c"]
    assert [ln.text for ln in body_lines([page])] == ["a b", "c"]


def test_real_pdf_bold_flags_reach_the_segmenter(tmp_path: Path) -> None:
    pdf = pymupdf.open()
    for n in range(3):
        page = pdf.new_page(width=W, height=H)
        page.insert_text((LEFT, 40), "ACME LIMITED", fontsize=8, fontname="helv")
        if n == 0:
            page.insert_text((LEFT, 150), "Internal Risks", fontsize=10, fontname="hebo")
            page.insert_text(
                (LEFT, 180), "We have a limited operating history as a company.", fontname="hebo",
                fontsize=10,
            )  # fmt: skip
            page.insert_text((LEFT, 194), "We started in 2021.", fontsize=10, fontname="helv")
        page.insert_text((290, 810), str(n + 1), fontsize=9, fontname="helv")
    path = tmp_path / "rf.pdf"
    pdf.save(path)
    parsed = parse_pdf(path, "acme", "rhp")
    spans = segment_pages(parsed.pages)
    assert [(s.title, s.body, s.group) for s in spans] == [
        (
            "We have a limited operating history as a company.",
            "We started in 2021.",
            "Internal Risks",
        )
    ]


CORPUS = """RISK FACTORS

An investment in equity shares involves a high degree of risk. Prospective investors
should consider the risks below.

Internal Risks

1. We depend on a few suppliers for our key raw material. In Fiscal 2025 our top
supplier provided 48% of purchases.
Any disruption could hurt production.

2. Our Promoters, Directors and Group Companies are involved in legal proceedings. Rs. 12.5
million is involved in these cases.

The table shows:
1. Civil cases 4

External Risks

3. Changes in Indian tax laws may affect our profits. The Finance Act changes rates often.
"""


def test_corpus_text_numbered_titles_groups_and_preamble() -> None:
    spans = segment_text(CORPUS)
    assert [s.title for s in spans] == [
        "We depend on a few suppliers for our key raw material.",
        "Our Promoters, Directors and Group Companies are involved in legal proceedings.",
        "Changes in Indian tax laws may affect our profits.",
    ]
    assert [s.group for s in spans] == ["Internal Risks", "Internal Risks", "External Risks"]
    assert spans[0].body == (
        "In Fiscal 2025 our top supplier provided 48% of purchases. "
        "Any disruption could hurt production."
    )
    # "1. Civil cases 4" does not follow 2, so it stays in the body.
    assert "1. Civil cases 4" in spans[1].body
    assert spans[1].body.startswith("Rs. 12.5 million")


def test_first_sentence_skips_abbreviations() -> None:
    assert first_sentence("We owe Rs. 5 crore to M/s. Acme Pvt. Ltd. on demand. It is due.") == (
        "We owe Rs. 5 crore to M/s. Acme Pvt. Ltd. on demand.",
        "It is due.",
    )


def test_to_risks_numbers_in_order() -> None:
    risks = to_risks(segment_pages(bold_doc()))
    assert [(x.rid, x.order) for x in risks] == [("r1", 1), ("r2", 2), ("r3", 3)]
    assert risks[1].page_end == 11


def test_split_stage_reads_the_risk_factors_section_and_writes_risks_json(tmp_path: Path) -> None:
    from finsight.core.config import get_settings
    from finsight.core.schemas import ParsedDoc, Section, Table, TableCell
    from finsight.db import Database
    from finsight.jobs import JobContext
    from finsight.pipeline.risks_stage import risks_split, split_risks, table_boxes
    from finsight.storage import LocalStorage, get_json

    pages, boxes = mixed_doc()
    cover = Page(number=1, width=W, height=H, words=[], text="", is_scanned=False)
    parsed = ParsedDoc(
        ipo_id="acme", doc_type="rhp", source_path="x.pdf", n_pages=32, pages=[cover, *pages],
        sha256="0" * 64,
    )  # fmt: skip
    cells = [
        TableCell(row=0, col=0, text="Date", bbox=(LEFT - 2, 194.0, 200.0, 206.0), page=30),
        TableCell(row=1, col=1, text="10.00", bbox=(300.0, 210.0, W - LEFT, 222.0), page=30),
    ]
    tables = [Table(id="t1", section_id="risk_factors", pages=[30], cells=cells)]
    assert table_boxes(tables) == boxes
    sections = [
        Section(id="risk_factors", title="RISK FACTORS", start_page=30, end_page=32,
                method="toc", confidence=1.0),
    ]  # fmt: skip
    assert len(split_risks(parsed, sections, tables)) == 2
    assert split_risks(parsed, []) == []

    storage = LocalStorage(tmp_path)
    ctx = JobContext(
        doc_id="doc_0123456789abcdef", job_id="j1", db=Database("sqlite://"), storage=storage,
        settings=get_settings(),
        scratch={"parsed": parsed, "sections": sections, "tables": tables},
    )  # fmt: skip
    assert risks_split(ctx) == {"n_risks": 2}
    saved = get_json(storage, ctx.key("risks.json"))
    assert [r["rid"] for r in saved] == ["r1", "r2"]


def test_split_stage_withholds_residential_addresses() -> None:
    from finsight.core.schemas import ParsedDoc, Section
    from finsight.pipeline.risks_stage import split_risks

    p = (
        PageBuilder(5)
        .line(b("Internal Risks"))
        .line(b("Our Promoter is involved in a pending criminal proceeding."))
        .line(
            r("The complaint names Mr. A. Kumar, residential address: 12 Lake Road, Pune 411001.")
        )
    )
    parsed = ParsedDoc(
        ipo_id="acme", doc_type="rhp", source_path="x.pdf", n_pages=7, sha256="0" * 64,
        pages=[p.page(), PageBuilder(6).page(), PageBuilder(7).page()],
    )  # fmt: skip
    section = Section(
        id="risk_factors", title="RISK FACTORS", start_page=5, end_page=7, method="toc",
        confidence=1.0,
    )  # fmt: skip
    (risk,) = split_risks(parsed, [section])
    assert "Lake Road" not in risk.body
    assert "[withheld for privacy]" in risk.body
