"""The BiLSTM-CRF extractor with a fake tagger (no weights), and the tokenizer contract."""

import json
import re
from pathlib import Path

import pytest

from finsight.core.schemas import Money, Page, ParsedDoc
from finsight.extract import BiLSTMCRFExtractor, tokenize
from finsight.extract import get_field as deployed_field
from finsight.extract.bilstm_crf import TaggedSpan, Tagger
from finsight.extract.tokens import TOKEN_PATTERN

TEXT = "The Fresh Issue is up to ₹ 26,260 million by the Company and nothing else."


def field(field_id: str):  # type: ignore[no-untyped-def]
    return deployed_field(field_id).model_copy(
        update={"extractor": "rules", "fallback": "bilstm_crf"}
    )


def doc(pages: list[str]) -> ParsedDoc:
    return ParsedDoc(
        ipo_id="urban-company-2025", doc_type="rhp", source_path="x.pdf", n_pages=len(pages),
        sha256="0", pages=[
            Page(number=i, width=595, height=842, words=[], text=t, is_scanned=False)
            for i, t in enumerate(pages, 1)
        ],
    )  # type: ignore[arg-type]  # fmt: skip


def tagger(calls: list[list[str]] | None = None) -> Tagger:
    def tag(texts: list[str]) -> list[list[TaggedSpan]]:
        if calls is not None:
            calls.append(texts)
        out = []
        for text in texts:
            i = text.find("₹ 26,260 million")
            out.append(
                [TaggedSpan("fresh_issue_size", i, i + len("₹ 26,260 million"), 0.8, 3)]
                if i >= 0 else []
            )  # fmt: skip
        return out

    return tag


def test_a_tagged_span_becomes_a_typed_candidate_with_its_page() -> None:
    ex = BiLSTMCRFExtractor(13, tagger=tagger())
    found = ex.extract(doc(["nothing here", TEXT]), [], [], field("fresh_issue_size"))
    assert [c.page for c in found] == [2]
    assert found[0].extractor == "bilstm_crf"
    assert found[0].raw == "₹ 26,260 million"
    assert isinstance(found[0].value, Money)
    assert found[0].value.value_inr is not None
    assert found[0].score == pytest.approx(0.8)


def test_other_fields_take_their_own_spans_and_text_is_tagged_once() -> None:
    calls: list[list[str]] = []
    ex = BiLSTMCRFExtractor(13, tagger=tagger(calls))
    d = doc([TEXT])
    assert ex.extract(d, [], [], field("registrar")) == []  # tagged, but not as a registrar
    assert ex.extract(d, [], [], field("fresh_issue_size"))
    assert ex.extract(d, [], [], field("fresh_issue_size"))
    assert sum(len(c) for c in calls) == 1  # the passage was tagged one time for all fields


def test_missing_weights_say_how_to_fetch_them(tmp_path: Path) -> None:
    ex = BiLSTMCRFExtractor(42, models_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="fetch bilstm-42"):
        ex.extract(doc([TEXT]), [], [], field("fresh_issue_size"))


def test_tokenizer_keeps_numbers_whole_and_offsets_exact() -> None:
    toks = tokenize(TEXT)
    assert ("26,260", TEXT.index("26,260"), TEXT.index("26,260") + 6) in toks
    assert all(TEXT[s:e] == t for t, s, e in toks)


def test_the_notebook_tokenizes_like_the_package() -> None:
    nb = json.loads(
        (Path(__file__).resolve().parents[2] / "notebooks" / "02_bilstm_crf.ipynb").read_text(
            "utf-8"
        )
    )
    source = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    match = re.search(r'TOKEN = re\.compile\(r"(.*)"\)', source)
    assert match is not None
    assert match.group(1) == TOKEN_PATTERN
