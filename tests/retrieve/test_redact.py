"""Layer 2 of the privacy fix (ADR-048): residential addresses never reach the index."""

from finsight.core.schemas import Page, ParsedDoc, Table, TableCell, Word
from finsight.retrieve import build_chunks, find_personal_addresses, redact_prose, redact_table
from finsight.retrieve.redact import PLACEHOLDER, address_column_words

ADDRESS = "Flat 12, Maple Heights, Sector 22, Springfield 400001"


def test_explicit_residential_cue_is_redacted() -> None:
    text = f"Mr Rao is our Promoter. Residential address: {ADDRESS} Occupation: Business"
    out, _ = redact_prose(text, [])
    assert "Maple Heights" not in out
    assert PLACEHOLDER in out
    assert "Occupation: Business" in out  # the next field survives


def test_bare_address_label_in_director_particulars() -> None:
    text = f"DIN: 01234567 Date of Birth: 1 May 1970 Address : {ADDRESS} Nationality: Indian"
    out, _ = redact_prose(text, [])
    assert "Springfield" not in out
    assert "Nationality: Indian" in out


def test_label_without_a_colon_needs_a_field_label_after_it() -> None:
    boxed = f"Designation Whole-time Director Address {ADDRESS} Occupation Business Current term 5"
    assert "Springfield" not in redact_prose(boxed, [])[0]
    prose = "The DIN and occupation are given elsewhere. Send your address to the Bidder."
    assert redact_prose(prose, [])[0] == prose


def test_residing_at_sentence_is_redacted() -> None:
    text = f"She is our Promoter and is residing at {ADDRESS}. For her profile see page 9."
    out, _ = redact_prose(text, [])
    assert "Maple Heights" not in out
    assert "For her profile see page 9." in out


def test_business_addresses_stay() -> None:
    text = (
        "Registered Office address: Tower B, Plot 5, Industrial Area, Springfield 400001. "
        "Registrar to the Offer, address: Selenium Building, Hyderabad 500032. "
        "DIN occupation nationality are listed in the table."
    )
    assert redact_prose(text, [])[0] == text


def test_redaction_is_idempotent() -> None:
    text = f"Residential address: {ADDRESS} Occupation: Business"
    once, _ = redact_prose(text, [])
    assert find_personal_addresses(once) == []
    assert redact_prose(once, [])[0] == once


def test_spans_stay_aligned_after_a_redaction() -> None:
    text = f"Residential address: {ADDRESS} Occupation: Business"
    start = text.index("Occupation")
    spans = [(0, 11, 1, (0, 0, 1, 1)), (start, start + 10, 1, (5, 5, 6, 6))]
    out, new = redact_prose(text, spans)
    assert out[new[-1][0] : new[-1][1]] == "Occupation"
    assert new[0][:2] == (0, 11)


def cell(row: int, col: int, text: str) -> TableCell:
    return TableCell(
        row=row,
        col=col,
        text=text,
        page=1,
        bbox=(col * 100, row * 20, col * 100 + 90, row * 20 + 15),
    )


def table(rows: list[list[str]]) -> Table:
    cells = [cell(r, c, t) for r, row in enumerate(rows) for c, t in enumerate(row)]
    return Table(id="t", section_id="s", pages=[1], cells=cells)


def test_address_column_of_a_director_table_is_blanked() -> None:
    t = table(
        [
            ["Name", "DIN", "Residential address", "Occupation"],
            ["A Rao", "01234567", ADDRESS, "Business"],
            ["B Sen", "07654321", "House No 8, Lake Road, Pune", "Service"],
        ]
    )
    out = redact_table(t)
    texts = [c.text for c in out.cells]
    assert ADDRESS not in texts
    assert "House No 8, Lake Road, Pune" not in texts
    assert texts.count(PLACEHOLDER) == 2
    assert "A Rao" in texts
    assert "Business" in texts
    assert "Residential address" in texts


def test_registrar_table_keeps_its_addresses() -> None:
    t = table(
        [
            ["Name", "Address", "Telephone"],
            ["KFin Technologies Limited", "Selenium Building, Hyderabad 500032", "040 6716 2222"],
        ]
    )
    assert redact_table(t) == t


def w(text: str, x0: float, y0: float, x1: float | None = None) -> Word:
    return Word(text=text, bbox=(x0, y0, x1 or x0 + 30, y0 + 9), font_size=9, bold=False)


def test_geometry_removes_the_address_column_of_an_undetected_board_table() -> None:
    words = [
        w("Name", 50, 100), w("and", 90, 100), w("Designation", 120, 100), w("DIN", 220, 100),
        w("Address", 330, 100),
        w("A", 50, 130), w("Rao", 70, 130), w("08000001", 220, 130, 270),
        w("Flat", 330, 130), w("12,", 360, 130), w("Maple", 330, 142), w("Heights", 365, 142),
        w("B", 50, 170), w("Sen", 70, 170), w("08000002", 220, 170, 270),
        w("Lake", 330, 170), w("Road,", 360, 170), w("Pune", 330, 182),
        w("The", 50, 230), w("Company", 90, 230), w("appoints", 150, 230), w("auditors.", 330, 230),
    ]  # fmt: skip
    gone = {words[i].text for i in address_column_words(words)}
    assert {"Flat", "Maple", "Heights", "Lake", "Road,", "Pune"} <= gone
    assert not gone & {"Address", "A", "Rao", "08000001", "B", "Sen", "The", "Company"}
    assert "auditors." not in gone  # prose below the table is not part of it


def test_chunks_of_a_page_with_an_address_do_not_contain_it() -> None:
    words = [
        w("Residential", 10, 10), w("address:", 60, 10), w("Flat", 110, 10), w("12,", 140, 10),
        w("Maple", 170, 10), w("Heights", 200, 10), w("Occupation:", 240, 10),
        w("Business.", 300, 10), w("DIN", 10, 30), w("01234567.", 40, 30),
    ]  # fmt: skip
    page = Page(number=1, width=600, height=800, words=words, is_scanned=False,
                text=" ".join(x.text for x in words))  # fmt: skip
    pdoc = ParsedDoc(ipo_id="acme-2025", doc_type="rhp", source_path="x.pdf", n_pages=1,
                     pages=[page], sha256="0")  # type: ignore[arg-type]  # fmt: skip
    chunks = build_chunks(pdoc, [], [])
    joined = " ".join(c.text for c in chunks)
    assert "Maple" not in joined
    assert PLACEHOLDER in joined
    assert "Business." in joined


def test_continuation_page_without_a_header_is_redacted_by_din_rows() -> None:
    words = [
        w("A", 50, 120), w("Rao", 70, 120), w("Flat", 330, 120), w("12,", 360, 120),
        w("Independent", 50, 140), w("Director", 120, 140), w("Maple", 330, 140),
        w("DIN:", 50, 160), w("08000001", 90, 160, 140), w("Heights", 330, 160),
        w("Pune", 330, 180),
        w("The", 50, 240), w("Company", 90, 240), w("appoints", 150, 240),
    ]  # fmt: skip
    gone = {words[i].text for i in address_column_words(words)}
    assert {"Flat", "12,", "Maple", "Heights", "Pune"} <= gone
    assert not gone & {"A", "Rao", "Independent", "Director", "DIN:", "08000001", "The", "Company"}


def test_address_cells_start_left_of_the_address_header_word() -> None:
    words = [
        w("Name,", 50, 100), w("Designation", 90, 100), w("and", 160, 100), w("DIN", 190, 100),
        w("Address", 359, 100),
        w("A", 50, 130), w("Rao", 70, 130),
        w("DIN:", 50, 150), w("08000001", 90, 150, 140),
        w("Flat", 283, 130), w("12,", 330, 130), w("Maple", 283, 150), w("Heights", 330, 150),
        w("The", 50, 220), w("Company", 90, 220),
    ]  # fmt: skip
    gone = {words[i].text for i in address_column_words(words)}
    assert {"Flat", "12,", "Maple", "Heights"} <= gone
    assert not gone & {"A", "Rao", "DIN:", "08000001", "The", "Company"}
