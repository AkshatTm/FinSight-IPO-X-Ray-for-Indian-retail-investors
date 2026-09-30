import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from finsight.api.app import create_app
from finsight.api.events import EVENT_MODELS

ROOT = Path(__file__).resolve().parents[2]

# Every endpoint in 06_API_CONTRACT.md (method, path).
ROUTES = [
    ("GET", "/api/health"),
    ("GET", "/api/ipos"),
    ("GET", "/api/ipos/{id}"),
    ("GET", "/api/ipos/{id}/xray"),
    ("GET", "/api/ipos/{id}/pages/{n}"),
    ("GET", "/api/ipos/{id}/pages/{n}/words"),
    ("GET", "/api/ipos/{id}/suggested-questions"),
    ("POST", "/api/chat"),
    ("POST", "/api/voice"),
    ("GET", "/api/traces/{trace_id}"),
    ("GET", "/api/lab/ladder"),
    ("GET", "/api/lab/fields"),
    ("GET", "/api/lab/verifier"),
    ("GET", "/api/lab/weaklabels"),
    ("GET", "/api/lab/frontier"),
    ("GET", "/api/glossary"),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def spec() -> dict:  # type: ignore[type-arg]
    return create_app().openapi()


@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_every_contract_route_is_in_openapi(spec: dict, method: str, path: str) -> None:  # type: ignore[type-arg]
    assert method.lower() in spec["paths"][path]


def test_no_route_outside_the_contract(spec: dict) -> None:  # type: ignore[type-arg]
    documented = {path for _, path in ROUTES}
    assert set(spec["paths"]) == documented


@pytest.mark.parametrize(
    ("method", "url", "kwargs"),
    [
        ("GET", "/api/health", {}),
        ("GET", "/api/ipos", {}),
        ("GET", "/api/ipos/acme-2025", {}),
        ("GET", "/api/ipos/acme-2025/xray", {}),
        ("GET", "/api/ipos/acme-2025/pages/1", {}),
        ("GET", "/api/ipos/acme-2025/pages/1/words", {}),
        ("GET", "/api/ipos/acme-2025/suggested-questions", {}),
        ("POST", "/api/chat", {"json": {"ipo_id": "a", "question": "q", "language": "en"}}),
        ("GET", "/api/traces/01ABC", {}),
        ("GET", "/api/lab/ladder", {}),
        ("GET", "/api/glossary?lang=en", {}),
    ],
)
def test_skeleton_answers_501_with_the_error_envelope(
    client: TestClient,
    method: str,
    url: str,
    kwargs: dict,  # type: ignore[type-arg]
) -> None:
    response = client.request(method, url, **kwargs)
    assert response.status_code == 501
    error = response.json()["error"]
    assert set(error) == {"code", "message", "hint", "trace_id"}
    assert error["code"] == "internal_error"


def test_validation_errors_use_the_envelope_too(client: TestClient) -> None:
    response = client.post("/api/chat", json={"question": "missing ipo_id"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unexpected_exceptions_never_leak_a_stack_trace() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret detail")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret detail" not in response.text
    assert "Traceback" not in response.text


def test_every_sse_event_model_is_registered_in_openapi(spec: dict) -> None:  # type: ignore[type-arg]
    schemas = spec["components"]["schemas"]
    assert set(EVENT_MODELS) == {
        "stage", "guard", "retrieval", "abstain", "token", "answer", "verdict", "final", "error",
    }  # fmt: skip
    for model in EVENT_MODELS.values():
        assert model.__name__ in schemas


def test_chat_documents_the_event_stream(spec: dict) -> None:  # type: ignore[type-arg]
    ok = spec["paths"]["/api/chat"]["post"]["responses"]["200"]["content"]["text/event-stream"]
    assert set(ok["x-sse-events"]) == set(EVENT_MODELS)
    assert ok["x-sse-events"]["verdict"] == {"$ref": "#/components/schemas/VerdictEvent"}


def test_money_is_a_string_in_the_schema(spec: dict) -> None:  # type: ignore[type-arg]
    assert spec["components"]["schemas"]["Money"]["properties"]["value_inr"]["anyOf"][0] == {
        "type": "string",
        "examples": ["8000000000.00"],
    }


def test_committed_openapi_json_is_current() -> None:
    committed = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
    assert committed == create_app().openapi(), "run `uv run poe gen-openapi` and commit the result"
