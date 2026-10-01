"""The index stage: chunk both documents of an IPO and write ``index/`` (BM25 data + vectors).

``chunks.jsonl`` is always written; ``dense.npy`` only when an embedder is passed (bge-m3 needs
the ``ml`` group and the GPU: ``uv run --group ml python -m finsight.pipeline build-all
--stage index --dense``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from finsight.core.schemas import DocType, Passage
from finsight.pipeline.parse_stage import load_parsed
from finsight.pipeline.sections_stage import load_sections
from finsight.pipeline.tables_stage import load_tables
from finsight.retrieve import Embedder, IpoIndex, build_chunks, index_dir

DOCS: tuple[DocType, ...] = ("rhp", "prospectus")


@dataclass(frozen=True)
class IndexReport:
    ipo_id: str
    passages: int
    tables: int
    dense: bool


def run_index(
    processed_dir: Path,
    ipo_id: str,
    docs: tuple[DocType, ...] = DOCS,
    embedder: Embedder | None = None,
) -> IndexReport:
    passages: list[Passage] = []
    n_tables = 0
    for doc in docs:
        tables = load_tables(processed_dir, ipo_id, doc)
        n_tables += sum(bool(t.cells) for t in tables)
        passages += build_chunks(
            load_parsed(processed_dir, ipo_id, doc),
            load_sections(processed_dir, ipo_id, doc),
            tables,
        )
    IpoIndex.build(passages, embedder).save(index_dir(processed_dir, ipo_id))
    return IndexReport(
        ipo_id=ipo_id,
        passages=len(passages),
        tables=n_tables,
        dense=embedder is not None,
    )
