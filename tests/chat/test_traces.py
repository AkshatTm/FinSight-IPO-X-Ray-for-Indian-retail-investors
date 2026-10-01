from finsight.chat import TraceStore, new_trace_id
from finsight.core.schemas import Trace


def test_trace_ids_are_26_char_ulids_sorted_by_time() -> None:
    a, b = new_trace_id(1_000), new_trace_id(2_000)
    assert len(a) == len(b) == 26
    assert a < b
    assert set(a) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")


def test_trace_round_trip_and_missing(tmp_path) -> None:
    store = TraceStore(tmp_path / "sub" / "traces.sqlite")
    trace = Trace(
        trace_id="T1", question="q", stages=[{"name": "guard", "status": "end", "ms": 3}],
        passages=[{"id": "p"}], prompt="the prompt", checks=[], timings_ms={"guard": 3},
    )  # fmt: skip
    store.save("ather", trace)
    assert store.get("T1") == trace
    assert store.get("nope") is None
    assert store.count() == 1
