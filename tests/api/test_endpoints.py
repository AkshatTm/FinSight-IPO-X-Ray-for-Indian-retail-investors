"""The routes against a small synthetic data folder (no real PDFs, models or Ollama)."""

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from finsight.api import state as state_module
from finsight.api.app import create_app
from finsight.api.demo import DemoCache
from finsight.api.ipos import IpoStore
from finsight.api.state import AppState, get_state
from finsight.chat import ChatOrchestrator, TraceStore
from finsight.core.config import load_settings
from finsight.core.schemas import (
    Candidate,
    CheckResult,
    FieldResult,
    FieldSpec,
    Money,
    Page,
    ParsedDoc,
    Passage,
    Placeholder,
    Word,
    XRay,
)
from finsight.retrieve import Hit, SearchResult
from finsight.voice import AsrManager, Transcript

IPO = "ather-energy-2025"
TEXT = "Fresh Issue of up to Rs. 26,260 million."


def money(inr: str, raw: str) -> Money:
    return Money(value_inr=inr, currency="INR", raw=raw, precision=2)


def cand(field: str, doc: str, value: Any, page: int, score: float = 0.9) -> Candidate:
    return Candidate(
        field_id=field, extractor="rules", doc_type=doc, raw="raw", value=value, page=page,
        bbox=(1.0, 2.0, 3.0, 4.0), score=score,
    )  # fmt: skip


def xray() -> XRay:
    fresh = cand("fresh_issue_size", "rhp", money("26260000000.00", "Rs. 26,260 million"), 3)
    ofs_rhp = cand("ofs_amount", "rhp", Placeholder(raw="[●]"), 3)
    ofs_pro = cand("ofs_amount", "prospectus", money("3550000000.00", "Rs. 3,550 million"), 3)
    check = CheckResult(check="total", status="verified", reason_code="verified", reason="ok")
    return XRay(
        ipo_id=IPO, company="Ather Energy Limited", built_at=datetime(2025, 5, 1), derived={},
        fields=[
            FieldResult(field_id="fresh_issue_size", chosen=fresh, candidates=[fresh],
                        verdict="verified", reason_code="verified", reason="Matches.", checks=[check]),
            FieldResult(field_id="ofs_amount", chosen=ofs_rhp, candidates=[ofs_rhp, ofs_pro],
                        verdict="verified", reason_code="placeholder", reason="Blank.", checks=[]),
            FieldResult(field_id="registrar", chosen=None, candidates=[], verdict="unverifiable",
                        reason_code="not_in_document", reason="Not in the document.", checks=[]),
        ],
    )  # fmt: skip


def specs() -> list[FieldSpec]:
    def spec(i: str, typ: str) -> FieldSpec:
        return FieldSpec(id=i, label_en=i.title(), label_hi="हि", type=typ, doc="rhp", sections=[],
                         questions=[], extractor="rules")  # fmt: skip

    return [
        spec("fresh_issue_size", "money"),
        spec("ofs_amount", "money"),
        spec("registrar", "text"),
    ]


@pytest.fixture
def data(tmp_path: Path) -> Path:
    base = tmp_path / "processed" / IPO
    base.mkdir(parents=True)
    (base / "xray.json").write_text(xray().model_dump_json(), encoding="utf-8")
    (base / "sections.json").write_text(
        json.dumps([{"id": "the_offer", "title": "THE OFFER", "start_page": 3, "end_page": 4,
                     "method": "toc", "confidence": 1.0}]), encoding="utf-8")  # fmt: skip
    (base / "pages").mkdir()
    Image.new("RGB", (935, 1210), "white").save(base / "pages" / "3.webp", "WEBP")
    page = Page(number=3, width=612.0, height=792.0, text="Fresh",
                words=[Word(text="Fresh", bbox=(72.0, 410.0, 98.0, 422.0), font_size=10.0, bold=False)],
                is_scanned=False)  # fmt: skip
    doc = ParsedDoc(ipo_id=IPO, doc_type="rhp", source_path="x", n_pages=1,
                    pages=[Page(number=1, width=612.0, height=792.0, words=[], text="", is_scanned=False),
                           Page(number=2, width=612.0, height=792.0, words=[], text="", is_scanned=False),
                           page], sha256="0")  # fmt: skip
    (base / "parsed.json").write_text(doc.model_dump_json(), encoding="utf-8")
    return tmp_path


class FakeLLM:
    def stream(self, prompt: str, **_: Any) -> Iterator[str]:
        yield from ("The fresh issue is ", "Rs. 26,260 million [1].")


class FakeBackend:
    loaded = False

    def load(self) -> float:
        self.loaded = True
        return 0.0

    def unload(self) -> None:
        self.loaded = False

    def transcribe_detailed(self, audio_path: Path, language: str = "hi") -> Transcript:
        return Transcript(
            text="पैसा कहाँ लगेगा", language=language, duration_s=4.0, seconds=0.1, model="fake"
        )


@pytest.fixture
def app_state(data: Path, monkeypatch: pytest.MonkeyPatch) -> AppState:
    for cache in (state_module.get_settings,):
        cache.cache_clear()  # type: ignore[attr-defined]
    from finsight.api import ipos as ipos_module

    for fn in (ipos_module._load_xray, ipos_module._load_parsed, ipos_module._load_sections):
        fn.cache_clear()
    settings = load_settings("dev_light")
    settings.paths.processed_dir = data / "processed"
    settings.paths.data_dir = data
    settings.paths.eval_dir = data / "eval_results"
    (data / "eval_results").mkdir()
    (data / "eval_results" / "ladder_table.json").write_text(
        '{"name": "ladder_table"}', encoding="utf-8"
    )
    state = AppState(
        settings=settings,
        store=IpoStore(data / "processed", specs()),
        traces=TraceStore(data / "traces.sqlite"),
        demo=DemoCache(data / "demo_cache"),
    )
    passage = Passage(id=f"{IPO}:p3:c0", ipo_id=IPO, doc_type="rhp", section_id="the_offer",
                      page_start=3, page_end=3, text=TEXT,
                      char_to_bbox=[(0, len(TEXT), 3, (10.0, 20.0, 300.0, 34.0))])  # fmt: skip
    state._chat = ChatOrchestrator(
        search=lambda q, ipo: SearchResult([Hit(passage, 0.9, 1)], "bm25", False, 0.9),
        llm=FakeLLM(),  # type: ignore[arg-type]
        traces=state.traces,
        facts=lambda ipo: [],
        budget_chars=3000,
    )
    monkeypatch.setattr(state_module, "_ollama_loaded", lambda model, timeout=0.5: None)
    return state


@pytest.fixture
def client(app_state: AppState) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_state] = lambda: app_state
    return TestClient(app, raise_server_exceptions=False)


def sse_events(text: str) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for block in text.strip().split("\n\n"):
        name, data = block.split("\n")
        out.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return out


# --------------------------------------------------------------------------- read-only routes
def test_ipo_list_has_all_demo_ipos_with_xray_status(client: TestClient) -> None:
    rows = client.get("/api/ipos").json()
    assert len(rows) == 10
    ather = next(r for r in rows if r["id"] == IPO)
    assert ather["xray_status"] == "ready"
    assert ather["fresh_inr"] == "26260000000.00"
    assert ather["ofs_inr"] == "3550000000.00"  # RHP blank, filled from the prospectus
    assert ather["issue_size_inr"] is None
    assert ather["sector"] == "Electric vehicles"
    assert next(r for r in rows if r["id"] == "lenskart-2025")["xray_status"] == "missing"


def test_ipo_list_filters_and_sorts(client: TestClient) -> None:
    assert [r["id"] for r in client.get("/api/ipos", params={"q": "ather"}).json()] == [IPO]
    assert [r["id"] for r in client.get("/api/ipos", params={"sector": "education"}).json()] == [
        "physicswallah-2025"
    ]
    by_date = [r["listing_date"] for r in client.get("/api/ipos").json()]
    assert by_date == sorted(by_date, reverse=True)
    assert client.get("/api/ipos", params={"year": 1999}).json() == []


def test_detail_has_page_size_and_sections(client: TestClient) -> None:
    body = client.get(f"/api/ipos/{IPO}").json()
    assert body["rhp_pages"] == 586
    assert body["page_size"] == {"width": 612.0, "height": 792.0}
    assert body["sections"][0] == {
        "id": "the_offer", "doc": "rhp", "title": "THE OFFER", "start_page": 3,
        "printed_start_page": None, "end_page": 4,
    }  # fmt: skip


def test_xray_maps_value_companion_and_not_in_document(client: TestClient) -> None:
    fields = {f["field_id"]: f for f in client.get(f"/api/ipos/{IPO}/xray").json()["fields"]}
    fresh = fields["fresh_issue_size"]
    assert fresh["value"]["value_inr"] == "26260000000.00"
    assert fresh["checks"][0]["status"] == "verified"
    assert fresh["companion"] is None
    ofs = fields["ofs_amount"]
    assert ofs["value"]["kind"] == "placeholder"
    assert ofs["companion"]["doc"] == "prospectus"
    assert ofs["companion"]["value"]["value_inr"] == "3550000000.00"
    registrar = fields["registrar"]
    assert registrar["value"] is None
    assert registrar["reason_code"] == "not_in_document"


def test_page_image_and_errors(client: TestClient) -> None:
    ok = client.get(f"/api/ipos/{IPO}/pages/3")
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "image/webp"
    assert "immutable" in ok.headers["cache-control"]
    missing = client.get(f"/api/ipos/{IPO}/pages/9999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "page_out_of_range"
    assert client.get(f"/api/ipos/{IPO}/pages/4").status_code == 404  # in range, not rendered
    assert client.get("/api/ipos/nope/pages/1").json()["error"]["code"] == "ipo_not_found"
    assert client.get(f"/api/ipos/{IPO}/pages/3", params={"doc": "other"}).status_code == 422


def test_page_words(client: TestClient) -> None:
    body = client.get(f"/api/ipos/{IPO}/pages/3/words").json()
    assert body["page"] == 3
    assert body["words"] == [{"t": "Fresh", "b": [72.0, 410.0, 98.0, 422.0]}]


def test_suggested_questions_include_the_scale_trick_from_the_xray(client: TestClient) -> None:
    rows = client.get(f"/api/ipos/{IPO}/suggested-questions").json()
    kinds = [r["kind"] for r in rows]
    assert {"normal", "trick", "advice"} <= set(kinds)
    trick = next(r for r in rows if r["kind"] == "trick")
    assert trick["text"] == "Is the fresh issue ₹2,626 lakh?"
    assert any(r["language"] == "hi" for r in rows)
    no_xray = client.get("/api/ipos/lenskart-2025/suggested-questions").json()
    assert "trick" not in [r["kind"] for r in no_xray]


def test_glossary_in_both_languages(client: TestClient) -> None:
    en = client.get("/api/glossary").json()
    hi = client.get("/api/glossary", params={"lang": "hi"}).json()
    assert len(en) == len(hi) >= 17
    assert next(g for g in en if g["term"] == "sebi")["title"] == "SEBI"
    assert next(g for g in hi if g["term"] == "sebi")["title"] == "सेबी"


def test_lab_serves_result_files_and_404s_when_missing(client: TestClient) -> None:
    assert client.get("/api/lab/ladder").json() == {"name": "ladder_table"}
    missing = client.get("/api/lab/frontier")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_available"


def test_health_degraded_without_ollama_and_ok_in_demo_mode(
    client: TestClient, app_state: AppState
) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["models"]["llm"]["loaded"] is False
    assert body["models"]["asr"] == {"name": None, "loaded": False, "lazy": True}
    app_state.settings.demo_mode = True
    assert client.get("/api/health").json()["status"] == "ok"


# ------------------------------------------------------------------------------------- chat
def chat(client: TestClient, question: str = "How big is the fresh issue?", **extra: Any):
    body = {"ipo_id": IPO, "question": question, "language": "en", **extra}
    return client.post("/api/chat", json=body)


def test_chat_streams_sse_events_in_contract_order(client: TestClient) -> None:
    response = chat(client)
    assert response.headers["content-type"].startswith("text/event-stream")
    events = sse_events(response.text)
    names = [n for n, _ in events if n not in ("stage", "token")]
    assert names == ["retrieval", "answer", "verdict", "final"]
    verdict = next(d for n, d in events if n == "verdict")
    assert verdict["status"] == "verified"
    final = events[-1][1]
    assert final["n_numbers"] == 1
    trace = client.get(f"/api/traces/{final['trace_id']}")
    assert trace.status_code == 200
    assert "How big is the fresh issue?" in trace.json()["prompt"]


def test_chat_advice_question_is_a_guard_event(client: TestClient) -> None:
    events = sse_events(chat(client, "Should I apply for this IPO?").text)
    assert [n for n, _ in events if n != "stage"] == ["guard", "final"]


def test_chat_errors_are_plain_json_before_the_stream_starts(client: TestClient) -> None:
    assert client.post("/api/chat", json={"ipo_id": "nope", "question": "q"}).status_code == 404
    long = chat(client, "x" * 301)
    assert long.status_code == 422
    assert long.json()["error"]["code"] == "validation_error"
    assert chat(client, "   ").status_code == 422


def test_unknown_trace_is_404(client: TestClient) -> None:
    assert client.get("/api/traces/NOPE").status_code == 404


def test_demo_mode_replays_recorded_streams_and_never_invents(
    client: TestClient, app_state: AppState
) -> None:
    live = sse_events(chat(client).text)
    assert not app_state.demo.has(IPO, "How big is the fresh issue?", "en")
    missing = sse_events(chat(client, demo=True).text)
    assert missing[0][0] == "error"
    from finsight.api.events import EVENT_MODELS

    app_state.demo.record(IPO, "How big is the fresh issue?", "en",
                          [(n, EVENT_MODELS[n].model_validate(d)) for n, d in live])  # fmt: skip
    replay = sse_events(
        chat(client, "how big is the fresh issue", demo=True).text
    )  # key ignores case and ?
    assert [n for n, _ in replay] == [n for n, _ in live]
    assert replay[-1][1]["trace_id"] == live[-1][1]["trace_id"]


def test_recorder_refuses_a_stream_without_final(app_state: AppState) -> None:
    from finsight.api.events import StageEvent

    with pytest.raises(ValueError, match="final"):
        app_state.demo.record(IPO, "q", "en", [("stage", StageEvent(name="guard", status="start"))])


# ------------------------------------------------------------------------------------ voice
def test_voice_is_off_in_the_light_profile(client: TestClient) -> None:
    r = client.post("/api/voice", files={"audio": ("a.webm", b"abc")})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "asr_failed"


def test_voice_transcribes_with_the_manager(client: TestClient, app_state: AppState) -> None:
    app_state.settings.voice.asr = "faster-whisper-small"
    app_state._asr = AsrManager(FakeBackend())  # type: ignore[arg-type]
    r = client.post("/api/voice", files={"audio": ("a.webm", b"abc")}, data={"language": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"] == "पैसा कहाँ लगेगा"
    assert body["asr_model"] == "fake"
    assert set(body) == {"transcript", "language", "asr_model", "ms"}
    assert client.get("/api/health").json()["models"]["asr"]["loaded"] is True


def test_voice_rejects_empty_and_oversized_audio(client: TestClient, app_state: AppState) -> None:
    app_state.settings.voice.asr = "faster-whisper-small"
    app_state._asr = AsrManager(FakeBackend())  # type: ignore[arg-type]
    assert client.post("/api/voice", files={"audio": ("a.webm", b"")}).status_code == 422
    big = client.post("/api/voice", files={"audio": ("a.webm", b"x" * 4_000_001)})
    assert big.status_code == 413
    assert big.json()["error"]["code"] == "audio_too_long"
