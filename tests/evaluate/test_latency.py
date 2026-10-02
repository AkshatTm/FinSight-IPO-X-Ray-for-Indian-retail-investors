from types import SimpleNamespace as NS

from finsight.evaluate.latency import peak, summarise, summarise_times, time_turn


class Clock:
    def __init__(self, ticks: list[float]) -> None:
        self.ticks = iter(ticks)

    def __call__(self) -> float:
        return next(self.ticks)


def test_times_are_summarised_in_ms_and_empty_is_none() -> None:
    assert summarise_times([]) == {"median": None, "p90": None, "max": None}
    got = summarise_times([100.0, 200.0, 300.0, 400.0, 1000.0])
    assert got["median"] == 300.0
    assert got["max"] == 1000.0
    assert got["p90"] == 1000.0


def test_time_turn_measures_the_first_token_and_the_total() -> None:
    events = [("stage", NS()), ("token", NS()), ("token", NS()),
              ("final", NS(timings_ms={"generating": 900}))]  # fmt: skip
    got = time_turn(events, clock=Clock([10.0, 10.5, 12.0]))  # start, first token, end
    assert got["first_token_ms"] == 500.0
    assert got["total_ms"] == 2000.0
    assert got["stages_ms"] == {"generating": 900}
    assert got["outcome"] == "answered"
    assert time_turn([("guard", NS())], clock=Clock([0.0, 1.0]))["outcome"] == "refused"


def test_summary_counts_answered_turns_only_and_keeps_the_memory_peak() -> None:
    turns = [
        {"outcome": "answered", "first_token_ms": 400.0, "total_ms": 5000.0,
         "stages_ms": {"generating": 4000}},
        {"outcome": "refused", "first_token_ms": None, "total_ms": 20.0, "stages_ms": {}},
    ]  # fmt: skip
    memory = [
        {"process_rss_gb": 1.0, "gpu_used_gb": None},
        {"process_rss_gb": 2.5, "gpu_used_gb": 3.1},
    ]
    s = summarise(turns, memory)
    assert s["outcomes"] == {"answered": 1, "refused": 1}
    assert s["total_ms"]["median"] == 5000.0
    assert s["stage_median_ms"] == {"generating": 4000.0}
    assert s["memory_peak"] == {"process_rss_gb": 2.5, "gpu_used_gb": 3.1}
    assert peak([]) == {}
