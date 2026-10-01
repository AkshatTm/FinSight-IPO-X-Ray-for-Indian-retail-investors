from finsight.core.ids import parse_passage_id
from finsight.core.schemas import Page, ParsedDoc, Section, Table, TableCell, Word
from finsight.retrieve.chunk import HARD_MAX_CHARS, TARGET_CHARS, build_chunks, section_for_page


def word(text: str, x: float, y: float) -> Word:
    return Word(text=text, bbox=(x, y, x + 10, y + 10), font_size=9, bold=False)


def page(number: int, words: list[Word], text: str = "") -> Page:
    return Page(
        number=number, width=600, height=800, words=words, is_scanned=False,
        text=text or " ".join(w.text for w in words),
    )  # fmt: skip


def doc(pages: list[Page], doc_type: str = "rhp") -> ParsedDoc:
    return ParsedDoc(
        ipo_id="acme-2025", doc_type=doc_type, source_path="x.pdf", n_pages=len(pages),
        pages=pages, sha256="0",
    )  # type: ignore[arg-type]  # fmt: skip


def cell(row: int, col: int, text: str, page_no: int = 1, y: float = 100) -> TableCell:
    return TableCell(
        row=row, col=col, text=text, page=page_no,
        bbox=(10 + col * 100, y + row * 20, 100 + col * 100, y + row * 20 + 15),
    )  # fmt: skip


def sentence_words(n_sentences: int, y: float = 10) -> list[Word]:
    words: list[Word] = []
    for s in range(n_sentences):
        for i in range(12):
            words.append(word(f"w{s}x{i}" + ("." if i == 11 else ""), 10 + i, y))
    return words


def test_section_for_page_picks_most_specific() -> None:
    sections = [
        Section(id="summary", title="S", start_page=1, end_page=40, method="toc", confidence=1),
        Section(id="objects", title="O", start_page=10, end_page=12, method="toc", confidence=1),
    ]
    assert section_for_page(11, sections) == "objects"
    assert section_for_page(30, sections) == "summary"
    assert section_for_page(99, sections) == "unsectioned"


def test_short_page_is_one_passage_with_spans_for_every_word() -> None:
    words = [
        word("The", 10, 10),
        word("registrar", 30, 10),
        word("is", 80, 10),
        word("KFin.", 100, 10),
    ]
    out = build_chunks(doc([page(3, words)]), [], [])
    assert len(out) == 1
    p = out[0]
    assert p.id == "acme-2025:p3:c0"
    assert p.page_start == p.page_end == 3
    assert p.text == "The registrar is KFin."
    assert len(p.char_to_bbox) == 4
    start, end, pg, box = p.char_to_bbox[3]
    assert p.text[start:end] == "KFin."
    assert pg == 3
    assert box == words[3].bbox


def test_prospectus_ids_carry_the_document() -> None:
    out = build_chunks(doc([page(2, sentence_words(1))], "prospectus"), [], [])
    assert parse_passage_id(out[0].id) == ("acme-2025", "prospectus", 2, 0)


def test_long_page_is_cut_at_sentence_ends() -> None:
    out = build_chunks(doc([page(1, sentence_words(60))]), [], [])
    assert len(out) > 1
    assert [p.id for p in out] == [f"acme-2025:p1:c{k}" for k in range(len(out))]
    for p in out[:-1]:
        assert TARGET_CHARS - 1 <= len(p.text) <= HARD_MAX_CHARS
        assert p.text.endswith(".")


def test_endless_sentence_is_cut_at_the_hard_limit() -> None:
    words = [word(f"w{i}", 10, 10) for i in range(2000)]  # no sentence end at all
    out = build_chunks(doc([page(1, words)]), [], [])
    assert len(out) > 1
    assert all(len(p.text) <= HARD_MAX_CHARS for p in out)


def test_table_is_one_passage_and_its_words_leave_the_prose() -> None:
    prose = [word("Utilisation", 10, 10), word("of", 70, 10), word("proceeds.", 90, 10)]
    in_table = [word("General", 12, 102), word("corporate", 40, 102), word("500", 112, 102)]
    cells = [
        cell(0, 0, "Purpose"), cell(0, 1, "Amount"),
        cell(1, 0, "General corporate"), cell(1, 1, "500"),
    ]  # fmt: skip
    table = Table(
        id="t1", section_id="objects", pages=[1], header_scale="₹ in million", cells=cells
    )
    out = build_chunks(doc([page(1, prose + in_table)]), [], [table])
    assert len(out) == 2
    prose_p, table_p = out
    assert prose_p.text == "Utilisation of proceeds."  # table words removed
    assert table_p.id == "acme-2025:p1:c1"
    assert table_p.section_id == "objects"
    assert table_p.text == ("[Table, ₹ in million]\nPurpose | Amount\nGeneral corporate | 500")
    start, end, _, _ = table_p.char_to_bbox[-1]
    assert table_p.text[start:end] == "500"


def test_table_larger_than_a_chunk_is_never_split() -> None:
    cells = [cell(r, c, "x" * 40, y=10) for r in range(30) for c in range(3)]
    table = Table(id="t", section_id="s", pages=[1], header_scale=None, cells=cells)
    out = build_chunks(doc([page(1, [])]), [], [table])
    assert len(out) == 1
    assert len(out[0].text) > TARGET_CHARS


def test_multi_page_table_is_one_passage_over_both_pages() -> None:
    cells = [cell(0, 0, "A", 4), cell(1, 0, "B", 4), cell(0, 0, "C", 5), cell(1, 0, "D", 5)]
    table = Table(id="t", section_id="s", pages=[4, 5], header_scale=None, cells=cells)
    out = build_chunks(doc([page(n, []) for n in range(1, 6)]), [], [table])
    assert len(out) == 1
    assert (out[0].page_start, out[0].page_end, out[0].id) == (4, 5, "acme-2025:p4:c0")
    assert out[0].text.splitlines() == ["A", "B", "C", "D"]


def test_scanned_page_falls_back_to_text_without_spans() -> None:
    p = Page(number=1, width=1, height=1, words=[], is_scanned=True,
             text="Registrar to the Offer is KFin Technologies Limited.")  # fmt: skip
    out = build_chunks(doc([p]), [], [])
    assert len(out) == 1
    assert out[0].char_to_bbox == []


def test_tiny_fragments_are_dropped() -> None:
    assert build_chunks(doc([page(1, [word("12", 10, 10)])]), [], []) == []
