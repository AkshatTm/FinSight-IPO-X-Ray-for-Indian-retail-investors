"""C2.1: the teacher input export picks capped, seeded, train-only risks."""

from collections import Counter

from finsight.risks.teacher_input import Candidate, select


def cand(company: str, i: int, year: int = 2020, words: int = 60, title: str | None = None):
    return Candidate(
        risk_id=f"{company}-{year}#r{i}", ipo_id=f"{company}-{year}", company=company, year=year,
        title=title or f"Title {i} of {company}", body=" ".join(["word"] * words),
    )  # fmt: skip


def test_cap_per_company_and_achievable_below_target() -> None:
    cands = [cand("A", i) for i in range(40)] + [cand("B", i) for i in range(10)]
    sel = select(cands, n_risks=1000, per_company_cap=25)
    counts = Counter(c.company for c in sel.chosen)
    assert counts == {"A": 25, "B": 10}
    assert (sel.achievable, sel.target) == (35, 35)
    assert sel.dropped["over_company_cap"] == 15


def test_word_limits_and_duplicate_titles() -> None:
    cands = [
        cand("A", 1, words=5),  # too short
        cand("A", 2, words=900),  # too long
        cand("A", 3, title="Same title"),
        cand("A", 4, title="same   TITLE"),  # duplicate of the one above
        cand("A", 5),
    ]
    sel = select(cands, min_words=40, max_words=600)
    assert sel.dropped["too_short"] == 1
    assert sel.dropped["too_long"] == 1
    assert sel.dropped["duplicate_title"] == 1
    assert len(sel.chosen) == 2


def test_recent_documents_are_sampled_more_often() -> None:
    old = [cand(f"O{c}", i, year=2019) for c in range(60) for i in range(5)]
    new = [cand(f"N{c}", i, year=2025) for c in range(60) for i in range(5)]
    sel = select([*old, *new], n_risks=200, per_company_cap=25, recent_weight=4.0, seed=1)
    years = Counter(c.year for c in sel.chosen)
    assert len(sel.chosen) == 200
    assert years[2025] > years[2019] * 1.5


def test_selection_is_deterministic_and_seeded() -> None:
    cands = [cand(f"C{c}", i) for c in range(30) for i in range(10)]
    a = select(cands, n_risks=100, seed=7)
    b = select(list(reversed(cands)), n_risks=100, seed=7)
    c = select(cands, n_risks=100, seed=8)
    assert [x.risk_id for x in a.chosen] == [x.risk_id for x in b.chosen]
    assert [x.risk_id for x in a.chosen] != [x.risk_id for x in c.chosen]


def test_as_row_has_the_notebook_columns() -> None:
    row = cand("A", 1).as_row()
    assert {"risk_id", "company", "title", "body"} <= set(row)
