"""C3.3: the stages that use the trained models, the workspace publishing and the rewrite drain."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from finsight.api.ipos import IpoStore
from finsight.core.schemas import DocRecord, Page, ParsedDoc
from finsight.db import Database
from finsight.jobs import SimplifyDrain, upload_stages
from finsight.jobs.model_stages import guess_company
from finsight.storage import LocalStorage, doc_key, put_json


def _doc(text_by_page: list[str]) -> ParsedDoc:
    pages = [
        Page(number=i, width=600, height=800, words=[], text=t, is_scanned=False)
        for i, t in enumerate(text_by_page, 1)
    ]
    return ParsedDoc(
        ipo_id="doc_x",
        doc_type="rhp",
        source_path="x.pdf",
        sha256="0" * 64,
        n_pages=len(pages),
        pages=pages,
    )


def test_company_comes_from_the_cover_not_from_the_exchange_or_a_banker() -> None:
    cover = (
        "RED HERRING PROSPECTUS\nNATIONAL STOCK EXCHANGE OF INDIA LIMITED\n"
        "ACME SOLAR HOLDINGS LIMITED\nAxis Capital Limited\nKFin Technologies Limited"
    )
    assert guess_company(_doc([cover])) == "Acme Solar Holdings Limited"
    assert guess_company(_doc(["no name here", "still none"])) is None


def test_the_model_stages_follow_the_scoring_order_and_can_be_switched_off() -> None:
    names = [s.name for s in upload_stages()]
    assert names[-4:] == ["risks_scored", "risk_level", "simplify", "index"]
    assert [s.name for s in upload_stages(models=False)] == names[:-4]
    by_name = {s.name: s for s in upload_stages()}
    assert by_name["risks_scored"].requires == ("risks_split",)
    assert by_name["index"].requires == ("sections",)


def test_a_published_upload_opens_like_a_showcase_ipo(tmp_path: Path) -> None:
    doc_id = "doc_0123456789abcdef"
    (tmp_path / doc_id).mkdir()
    meta = {"doc_id": doc_id, "company": "Acme Limited", "pages": 7}
    (tmp_path / doc_id / "upload.json").write_text(json.dumps(meta), encoding="utf-8")
    store = IpoStore(tmp_path, [])
    ipo = store.get(doc_id)
    assert (ipo.company, ipo.rhp.pages, ipo.rhp.doc_id) == ("Acme Limited", 7, doc_id)
    for bad in ("doc_0123456789abcdeg", "../doc_0123456789abcdef", "unknown-ipo"):
        with pytest.raises(Exception, match="No IPO"):
            store.get(bad)


class _Rewrite:
    status = "ready"

    def as_dict(self) -> dict[str, Any]:
        return {"simple": "Plain.", "simple_status": "ready"}


class _Simplifier:
    def rewrite(self, title: str, body: str) -> _Rewrite:
        return _Rewrite()


def test_the_drain_rewrites_queued_risks_and_retries_a_failed_one(tmp_path: Path) -> None:
    db = Database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    db.create_all()
    storage = LocalStorage(tmp_path / "store")
    doc_id = "doc_aaaaaaaaaaaaaaaa"
    db.insert_doc(DocRecord(doc_id=doc_id, sha256="a" * 64, created_at=datetime.now(UTC)))
    db.create_job(doc_id)
    risk = {"rid": "r1", "order": 1, "title": "T", "body": "B", "page_start": 1, "page_end": 1}
    put_json(storage, doc_key(doc_id, "risks.json"), [risk])
    db.enqueue(doc_id, ["r1"])
    db.take_next(doc_id)
    db.finish_item(doc_id, "r1", "failed")  # an earlier run failed (Ollama was down)
    assert db.waiting_rids(doc_id) == []
    db.bump(doc_id, "r1")  # a click puts it back at the front
    assert db.waiting_rids(doc_id) == ["r1"]
    drain = SimplifyDrain(db, storage, _Simplifier)
    assert drain.kick(doc_id)
    for _ in range(50):
        if not db.waiting_rids(doc_id) and not drain._active:
            break
        time.sleep(0.1)
    saved = json.loads(storage.get_bytes(doc_key(doc_id, "simplified.json")))
    assert saved["r1"]["simple_status"] == "ready"
    assert db.docs_with_queue() == []
