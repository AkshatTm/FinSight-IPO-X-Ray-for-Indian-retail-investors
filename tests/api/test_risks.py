"""B2.2a: the risks endpoints (B06 §3) on local storage with a hand-made risks.json."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from finsight.api import routes_risks
from finsight.api.app import create_app
from finsight.api.uploads_state import UploadState, get_upload_state
from finsight.core.config import load_settings
from finsight.core.schemas import DocRecord, Risk
from finsight.db import Database
from finsight.jobs import InlineLauncher
from finsight.storage import LocalStorage, doc_key, put_json

DOC = "doc_" + "a" * 16


def risk(i: int, **kw: object) -> Risk:
    base: dict[str, object] = dict(
        rid=f"r{i}",
        order=i,
        title=f"Risk {i}",
        body=f"Body {i}.",
        page_start=10 + i,
        page_end=10 + i,
    )
    return Risk.model_validate({**base, **kw})


RISKS = [
    risk(1, category="debt_liquidity", importance=0.4, novelty=0.5),
    risk(2, category="legal_litigation", importance=0.9, novelty=0.05, body="Court " * 400),
    risk(3, category="debt_liquidity", importance=None, novelty=None),
    risk(4, category="operations", importance=0.7, novelty=0.08, title="Plant fire"),
]


@pytest.fixture
def state(tmp_path: Path) -> UploadState:
    db = Database(f"sqlite:///{(tmp_path / 'r.db').as_posix()}")
    db.create_all()
    storage = LocalStorage(tmp_path / "store")
    db.insert_doc(
        DocRecord(
            doc_id=DOC,
            sha256="a" * 64,
            created_at=datetime.now(UTC),
            status="ready",
            company="Acme Ltd",
        )
    )
    put_json(storage, doc_key(DOC, "risks.json"), [r.model_dump(mode="json") for r in RISKS])
    put_json(
        storage,
        doc_key(DOC, "simplified.json"),
        {"r4": {"simple": "A fire stopped a plant.", "simple_status": "ready"}},
    )
    return UploadState(load_settings("dev_light"), db, storage, InlineLauncher(lambda d, j: None))


@pytest.fixture
def client(state: UploadState) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_upload_state] = lambda: state
    routes_risks.simplify_limit.hits.clear()
    with TestClient(app) as test_client:
        yield test_client


def rids(body: dict) -> list[str]:  # type: ignore[type-arg]
    return [r["rid"] for r in body["risks"]]


def test_default_sort_is_importance_then_document_order(client: TestClient) -> None:
    body = client.get(f"/api/docs/{DOC}/risks").json()
    assert body["n_total"] == 4
    assert rids(body) == ["r2", "r4", "r1", "r3"]
    assert body["groups"][0] == {"category": "debt_liquidity", "count": 2}
    assert len(body["risks"][0]["body"]) == 1200  # truncated in the list
    assert body["risks"][1]["simple"] == "A fire stopped a plant."
    assert body["risks"][1]["simple_status"] == "ready"


@pytest.mark.parametrize(
    ("query", "want"),
    [
        ("sort=order", ["r1", "r2", "r3", "r4"]),
        ("sort=category", ["r1", "r3", "r2", "r4"]),
        ("category=debt_liquidity", ["r1", "r3"]),
        ("unusual_only=true", ["r2", "r4"]),
        ("q=FIRE", ["r4"]),
        ("q=stopped", ["r4"]),  # the plain-English text is searched too
        ("category=operations&unusual_only=true", ["r4"]),
    ],
)
def test_sort_and_filters(client: TestClient, query: str, want: list[str]) -> None:
    body = client.get(f"/api/docs/{DOC}/risks?{query}").json()
    assert rids(body) == want
    assert body["n_total"] == 4


def test_single_risk_has_the_full_body(client: TestClient) -> None:
    body = client.get(f"/api/docs/{DOC}/risks/r2").json()
    assert len(body["body"]) == len("Court " * 400)
    assert body["nearest_examples"] == []
    missing = client.get(f"/api/docs/{DOC}/risks/r9")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "risk_not_found"


def test_missing_doc_and_missing_risks_file(client: TestClient, state: UploadState) -> None:
    assert client.get("/api/docs/doc_nope/risks").json()["error"]["code"] == "doc_not_found"
    other = "doc_" + "b" * 16
    state.db.insert_doc(DocRecord(doc_id=other, sha256="b" * 64, created_at=datetime.now(UTC)))
    r = client.get(f"/api/docs/{other}/risks")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_available"


def test_simplify_queues_bumps_and_skips_explained_risks(
    client: TestClient, state: UploadState
) -> None:
    state.db.enqueue(DOC, ["r1", "r2"])
    r = client.post(f"/api/docs/{DOC}/risks/r3/simplify").json()
    assert r == {"rid": "r3", "simple_status": "pending", "position": 0}
    assert state.db.queue(DOC) == ["r3", "r1", "r2"]
    done = client.post(f"/api/docs/{DOC}/risks/r4/simplify").json()
    assert done == {"rid": "r4", "simple_status": "ready", "position": -1}
    assert client.post(f"/api/docs/{DOC}/risks/r9/simplify").status_code == 404
    assert state.db.take_next(DOC) == "r3"  # running: still "Explaining…" in the list
    assert client.get(f"/api/docs/{DOC}/risks").json()["queued"] == ["r3", "r1", "r2"]


def test_simplify_is_rate_limited_per_ip(client: TestClient) -> None:
    for _ in range(routes_risks.SIMPLIFY_PER_MINUTE):
        assert client.post(f"/api/docs/{DOC}/risks/r1/simplify").status_code == 200
    r = client.post(f"/api/docs/{DOC}/risks/r1/simplify")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


def test_rate_limit_window_slides() -> None:
    limit = routes_risks._RateLimit(2)
    assert limit.allow("ip", 0.0)
    assert limit.allow("ip", 1.0)
    assert not limit.allow("ip", 59.0)
    assert limit.allow("ip", 60.5)
    assert limit.allow("other", 59.0)


def test_risk_level_endpoint_follows_the_behind_click_switch(
    client: TestClient, state: UploadState, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finsight.risklevel import build, load_config

    assert client.get(f"/api/docs/{DOC}/risk-level").json()["error"]["code"] == "not_available"
    build(state.storage, DOC)
    body = client.get(f"/api/docs/{DOC}/risk-level").json()
    assert body["level"] in ("low", "medium", "high")
    assert body["provisional"] is True
    assert body["disclaimer_key"] == "risklevel.disclaimer"
    assert body["behind_click"] is False
    hidden = {**load_config(), "behind_click": True}
    monkeypatch.setattr(routes_risks, "risklevel_config", lambda: hidden)
    assert client.get(f"/api/docs/{DOC}/risk-level").json()["behind_click"] is True


def test_compare_endpoint(client: TestClient, state: UploadState) -> None:
    from decimal import Decimal

    from finsight.compare import build
    from finsight.core.schemas import Peer

    assert client.get(f"/api/docs/{DOC}/compare").json()["error"]["code"] == "not_available"
    peers = [
        Peer(name="Acme", eps=Decimal("10"), is_issuer=True),
        Peer(name="Beta", pe=Decimal("40")),
    ]
    build(state.storage, DOC, peers, {"ofs_share": 0.5}, offer_price=Decimal("200"))
    body = client.get(f"/api/docs/{DOC}/compare").json()
    assert body["peers"][0]["pe"] == "20.00"
    assert body["peer_median_pe"] == "40"
    assert {p["metric"] for p in body["percentiles"]} == {"ofs_share", "pe"}
    assert body["provisional"] is True
    assert client.get("/api/docs/doc_0000000000000000/compare").status_code == 404


def test_redflags_endpoint(client: TestClient, state: UploadState) -> None:
    assert client.get(f"/api/docs/{DOC}/redflags").json()["error"]["code"] == "not_available"
    flag = {
        "id": "RF04",
        "title": "Who gets the IPO money",
        "status": "concern",
        "points": 2,
        "sentence": "85.0% of the money goes to existing shareholders who are selling, "
        "not to the company.",
    }
    put_json(
        state.storage,
        doc_key(DOC, "redflags.json"),
        {"flags": [flag], "thresholds_version": "b01-v1"},
    )
    body = client.get(f"/api/docs/{DOC}/redflags").json()
    assert body["flags"][0]["id"] == "RF04"
    assert body["flags"][0]["evidence"] == []
    assert body["financial_company"] is False


@pytest.mark.parametrize(
    ("hops", "header", "expected"),
    [
        (0, "1.1.1.1, 9.9.9.9", "peer"),  # default: the header is ignored
        (1, "6.6.6.6, 1.1.1.1", "1.1.1.1"),  # spoofed left part is never used
        (2, "6.6.6.6, 1.1.1.1, 9.9.9.9", "1.1.1.1"),
        (2, "9.9.9.9", "peer"),  # fewer entries than proxies: fall back to the socket peer
    ],
)
def test_client_ip_trusts_only_the_configured_proxy_hops(
    hops: int, header: str, expected: str
) -> None:
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", header.encode())],
        "client": ("peer", 1234),
    }
    assert routes_risks.client_ip(Request(scope), hops) == expected
