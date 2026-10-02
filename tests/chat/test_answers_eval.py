from types import SimpleNamespace as NS

from finsight.evaluate.answers import summarise, turn_record

Q = {"ipo_id": "a", "question": "q", "language": "en", "answerable": True, "answer_gold": "x"}


def verdict(status: str) -> NS:
    return NS(status=status, reason_code="verified", answer_char_span=(0, 3))


def test_turn_record_reads_the_event_stream() -> None:
    events = [
        ("stage", NS()),
        ("answer", NS(text="Rs. 5 [1]")),
        ("verdict", verdict("verified")),
        ("final", NS(timings_ms={"guard": 1})),
    ]
    row = turn_record(Q, events)
    assert row["outcome"] == "answered"
    assert row["answer"] == "Rs. 5 [1]"
    assert row["verdicts"][0]["status"] == "verified"
    assert row["reviewed_by_akshat"] == ""


def test_outcomes_for_guard_abstain_and_error() -> None:
    assert turn_record(Q, [("guard", NS())])["outcome"] == "refused"
    assert turn_record(Q, [("abstain", NS())])["outcome"] == "abstained"
    assert turn_record(Q, [("error", NS())])["outcome"] == "error"


def test_summary_counts() -> None:
    a = turn_record(
        Q,
        [
            ("answer", NS(text="t")),
            ("verdict", verdict("verified")),
            ("verdict", verdict("contradicted")),
        ],
    )
    b = turn_record({**Q, "answerable": False}, [("abstain", NS())])
    s = summarise([a, b])
    assert s["n_questions"] == 2
    assert s["verdicts"] == {"verified": 1, "contradicted": 1}
    assert s["verified_share"] == 0.5
    assert s["unanswerable_abstained_or_not_found"] == 1
