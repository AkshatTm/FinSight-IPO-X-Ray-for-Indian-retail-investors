from finsight.weaklabel.bio import to_bio, to_dev, tokenize


def row(i: str, field: str, ctx: str, text: str | None) -> dict:
    answers = (
        {"text": [text], "answer_start": [ctx.index(text)]}
        if text
        else {"text": [], "answer_start": []}
    )
    return {"id": i, "ipo_id": "x", "field_id": field, "context": ctx, "answers": answers}


def spans(seq: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for tok, tag in zip(seq["tokens"], seq["tags"], strict=True):
        if tag.startswith("B-"):
            out.append((tag[2:], tok))
        elif tag.startswith("I-"):
            out[-1] = (out[-1][0], out[-1][1] + " " + tok)
    return out


def test_numbers_stay_one_token() -> None:
    assert [t for t, _, _ in tokenize("₹ 19,000.50 million (A)")] == [
        "₹", "19,000.50", "million", "(", "A", ")",
    ]  # fmt: skip


def test_span_is_tagged_b_then_i() -> None:
    ctx = "Fresh issue of up to ₹ 3,000 million by the Company."
    seq = to_bio([row("a:p1:c1:fresh_issue_size", "fresh_issue_size", ctx, "₹ 3,000 million")])[0]
    assert spans(seq) == [("fresh_issue_size", "₹ 3,000 million")]
    assert seq["tags"][0] == "O"


def test_same_context_is_one_sequence_and_overlap_gets_a_copy() -> None:
    ctx = "Issue of ₹ 3,000 million."
    rows = [
        row("a:p1:c1:fresh_issue_size", "fresh_issue_size", ctx, "₹ 3,000 million"),
        row("a:p1:c1:total_issue_size", "total_issue_size", ctx, "₹ 3,000 million"),
        row("a:p1:c1:face_value", "face_value", ctx, "Issue"),
    ]
    seqs = to_bio(rows)
    assert len(seqs) == 2  # the overlapping field moved to its own copy
    assert sorted(f for s in seqs for f, _ in spans(s)) == [
        "face_value", "fresh_issue_size", "total_issue_size",
    ]  # fmt: skip


def test_unanswerable_row_is_all_o() -> None:
    seq = to_bio([row("a:p1:c1:registrar", "registrar", "Nothing here.", None)])[0]
    assert set(seq["tags"]) == {"O"}


def test_dev_keeps_the_rows_of_a_context() -> None:
    ctx = "Face value ₹ 10 each."
    dev = to_dev([row("d:1", "face_value", ctx, "₹ 10"), row("d:2", "registrar", ctx, None)])
    assert len(dev) == 1
    assert [r["id"] for r in dev[0]["rows"]] == ["d:1", "d:2"]
