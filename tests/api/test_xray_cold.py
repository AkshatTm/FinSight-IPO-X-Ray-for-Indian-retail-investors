"""An X-Ray request must not open the parsed documents when the build stored what it needs.

Real-API bug (2 Oct): opening any IPO in the Library failed. The X-Ray route rebuilt every
fact's source sentence from the parsed document, ~70 MB of JSON per document (about 2.5 s each
to validate, holding the GIL), so for 5 to 9 s the whole API, health check included, stood still;
uvicorn's 5 s keep-alive then closed the sockets that Next's proxy was holding and the browser got
500s ("socket hang up"). The sentence is now stored with the box when the X-Ray is built.
"""

from pathlib import Path

import pytest

from finsight.api import ipos
from finsight.api.ipos import IpoStore
from finsight.core.schemas import Candidate, Page, ParsedDoc, Word
from finsight.extract import fill_boxes


def word(t: str, x: float) -> Word:
    return Word(text=t, bbox=(x, 100.0, x + 20.0, 110.0), font_size=10.0, bold=False)


WORDS = [word(t, 10 + 22 * i) for i, t in enumerate(["Fresh", "issue", "of", "₹26,260", "million"])]


def candidate(**extra: object) -> Candidate:
    return Candidate(field_id="fresh_issue_size", extractor="rules", doc_type="rhp",
                     raw="₹26,260 million", value=None, page=1, score=1.0, **extra)  # type: ignore[arg-type]  # fmt: skip


def parsed_doc() -> ParsedDoc:
    return ParsedDoc.model_construct(
        doc_type="rhp", pages=[Page.model_construct(number=1, words=WORDS)]
    )


def test_the_build_stores_box_and_sentence_together() -> None:
    (c,) = fill_boxes([candidate()], parsed_doc())
    assert c.bbox is not None
    assert c.sentence == "Fresh issue of ₹26,260 million"
    assert c.sentence_hit is not None
    assert c.sentence[slice(*c.sentence_hit)] == "₹26,260 million"


def test_a_stored_sentence_is_served_without_opening_the_parsed_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(path: str) -> None:
        raise AssertionError(f"parsed document opened: {path}")

    monkeypatch.setattr(ipos, "_load_parsed", forbidden)
    store = IpoStore(tmp_path, [])
    (stored,) = fill_boxes([candidate()], parsed_doc())
    got = store._sentence("x", stored, stored.bbox)
    assert got is not None
    assert got.text == "Fresh issue of ₹26,260 million"


def test_an_older_xray_without_a_stored_sentence_still_works_by_opening_the_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []

    def load(path: str) -> ParsedDoc:
        opened.append(path)
        return parsed_doc()

    monkeypatch.setattr(ipos, "_load_parsed", load)
    store = IpoStore(tmp_path, [])
    old = candidate(bbox=(32.0, 100.0, 76.0, 110.0))  # a box but no sentence (built before the fix)
    assert store._sentence("x", old, old.bbox) is not None
    assert len(opened) == 1


def test_a_built_xray_never_opens_the_parsed_documents_for_a_value_without_a_box(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(path: str) -> None:
        raise AssertionError(f"parsed document opened: {path}")

    monkeypatch.setattr(ipos, "_load_parsed", forbidden)
    store = IpoStore(tmp_path, [])
    unmatched = candidate()  # the build found no box for this value (a list, a table cell)
    assert store._bbox("x", unmatched, located=True) is None
    assert store._sentence("x", unmatched, None) is None


def test_an_older_xray_still_looks_for_the_box(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ipos, "_load_parsed", lambda path: parsed_doc())
    store = IpoStore(tmp_path, [])
    assert store._bbox("x", candidate(), located=False) is not None
