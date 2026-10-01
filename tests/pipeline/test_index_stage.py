from pathlib import Path

import numpy as np
from pydantic import TypeAdapter

from finsight.core.schemas import Page, ParsedDoc, Section, Table, TableCell, Word
from finsight.pipeline.index_stage import run_index
from finsight.pipeline.layout import doc_outputs
from finsight.retrieve import IpoIndex, Retriever, index_dir

IPO = "acme-2025"


def word(text: str, x: float, y: float) -> Word:
    return Word(text=text, bbox=(x, y, x + 20, y + 10), font_size=9, bold=False)


def write_doc(processed: Path, doc_type: str, text_words: list[str]) -> None:
    out = doc_outputs(processed, IPO, doc_type)  # type: ignore[arg-type]
    out.parsed.parent.mkdir(parents=True, exist_ok=True)
    words = [word(t, 10 + 25 * i, 10) for i, t in enumerate(text_words)]
    page = Page(number=1, width=600, height=800, words=words, text=" ".join(text_words),
                is_scanned=False)  # fmt: skip
    doc = ParsedDoc(ipo_id=IPO, doc_type=doc_type, source_path="x.pdf", n_pages=1,  # type: ignore[arg-type]
                    sha256="0", pages=[page])  # fmt: skip
    out.parsed.write_text(doc.model_dump_json(), encoding="utf-8")
    out.sections.write_bytes(TypeAdapter(list[Section]).dump_json([]))
    cell = TableCell(row=0, col=0, text="Face value 10", bbox=(10, 300, 200, 320), page=1)
    table = Table(id="t", section_id="s", pages=[1], header_scale=None, cells=[cell])
    out.tables.write_bytes(TypeAdapter(list[Table]).dump_json([table]))


class Ones:
    def embed(self, texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), 4), dtype=np.float32) / 2


def test_run_index_writes_both_documents_and_is_searchable(tmp_path: Path) -> None:
    write_doc(
        tmp_path,
        "rhp",
        ["The", "registrar", "to", "the", "offer", "is", "KFin", "Technologies", "."],
    )
    write_doc(
        tmp_path,
        "prospectus",
        ["Axis", "Capital", "is", "the", "book", "running", "lead", "manager", "."],
    )
    report = run_index(tmp_path, IPO)
    assert (report.passages, report.tables, report.dense) == (4, 2, False)  # 2 prose + 2 tables
    assert (index_dir(tmp_path, IPO) / "chunks.jsonl").exists()
    assert not (index_dir(tmp_path, IPO) / "dense.npy").exists()
    hit = Retriever(tmp_path).search("registrar kfin", IPO).hits[0].passage
    assert hit.id == f"{IPO}:p1:c0"
    prospectus_hit = Retriever(tmp_path).search("axis capital", IPO).hits[0].passage
    assert prospectus_hit.id == f"{IPO}:prospectus:p1:c0"


def test_run_index_with_embedder_writes_vectors(tmp_path: Path) -> None:
    write_doc(
        tmp_path,
        "rhp",
        ["The", "registrar", "to", "the", "offer", "is", "KFin", "Technologies", "."],
    )
    write_doc(
        tmp_path,
        "prospectus",
        ["Axis", "Capital", "is", "the", "book", "running", "lead", "manager", "."],
    )
    report = run_index(tmp_path, IPO, embedder=Ones())
    assert report.dense is True
    loaded = IpoIndex.load(index_dir(tmp_path, IPO))
    assert loaded.dense is not None
    assert loaded.dense.vectors.shape == (4, 4)
