import io
from pathlib import Path

from PIL import Image

from finsight.api.ipos import _thumbnail
from finsight.core.schemas import Candidate, ParsedDoc, Word
from finsight.extract import fill_boxes, sentence_around


def word(t: str, x: float, y: float = 100.0, w: float = 20.0) -> Word:
    return Word(text=t, bbox=(x, y, x + w, y + 10.0), font_size=10.0, bold=False)


LINE = [
    word(t, 10 + 22 * i)
    for i, t in enumerate(["Fresh", "issue", "of", "up", "to", "₹26,260", "million", "by", "us"])
]
OTHER_LINE = [word("Next", 10, 112.0), word("line", 40, 112.0)]


def test_sentence_marks_the_value_inside_the_line() -> None:
    x0 = LINE[5].bbox[0]
    box = (x0, 100.0, LINE[6].bbox[2], 110.0)
    found = sentence_around([*LINE, *OTHER_LINE], box)
    assert found is not None
    text, (a, b) = found
    assert text == "Fresh issue of up to ₹26,260 million by us"
    assert text[a:b] == "₹26,260 million"  # the neighbouring line is not pulled in


def test_sentence_is_none_when_the_box_catches_nothing() -> None:
    assert sentence_around(LINE, (500.0, 300.0, 520.0, 310.0)) is None


def test_long_lines_keep_ten_words_each_side() -> None:
    words = [word(f"w{i}", 5 * i, w=4.0) for i in range(60)]
    box = (words[30].bbox[0], 100.0, words[30].bbox[2], 110.0)
    found = sentence_around(words, box)
    assert found is not None
    text, (a, b) = found
    assert text.split()[0] == "w20"
    assert text.split()[-1] == "w40"
    assert text[a:b] == "w30"


def test_fill_boxes_keeps_a_stored_box_and_finds_a_missing_one() -> None:
    doc = ParsedDoc.model_construct(
        doc_type="rhp",
        pages=[type("P", (), {"words": LINE})()],  # type: ignore[arg-type]
    )
    found = Candidate(field_id="f", extractor="rules", doc_type="rhp", raw="₹26,260 million",
                      value=None, page=1, score=1.0)  # fmt: skip
    stored = found.model_copy(update={"bbox": (1.0, 2.0, 3.0, 4.0)})
    other_doc = found.model_copy(update={"doc_type": "prospectus"})
    out = fill_boxes([found, stored, other_doc], doc)
    assert out[0].bbox is not None
    assert out[1].bbox == (1.0, 2.0, 3.0, 4.0)
    assert out[2].bbox is None  # a candidate from the other document is not matched here


def test_thumbnail_is_smaller_and_never_enlarged(tmp_path: Path) -> None:
    path = tmp_path / "1.webp"
    Image.new("RGB", (800, 1000), "white").save(path, format="WEBP")
    small = Image.open(io.BytesIO(_thumbnail(str(path), 160)))
    assert small.size == (160, 200)
    big = Image.open(io.BytesIO(_thumbnail(str(path), 1200)))
    assert big.size == (800, 1000)
