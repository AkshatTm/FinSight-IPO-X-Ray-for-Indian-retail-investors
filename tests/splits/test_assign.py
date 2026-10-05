"""C1.4: strict time split (C-ADR-02) with showcase roles from demo_ipos.yaml."""

from datetime import date, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from finsight.splits import IpoRecord, SplitError, SplitRules, assign, check_strict


def new(i: int, d: date, company: str | None = None) -> IpoRecord:
    return IpoRecord.new(f"new-co-{i}-{d.year}", company or f"New Co {i} Limited", d)


def corpus(i: int, year: int) -> IpoRecord:
    return IpoRecord.corpus(f"old-co-{i}-{year}", f"Old Co {i} Limited", year)


def showcase(ipo_id: str, d: date, role: str, company: str | None = None) -> IpoRecord:
    name = company or ipo_id.replace("-", " ").title() + " Limited"
    return IpoRecord.showcase(ipo_id, name, d, role)


START = date(2024, 1, 1)
NEWS = [new(i, START + timedelta(days=12 * i)) for i in range(60)]  # Jan 2024 .. Dec 2025
OLD = [corpus(i, 2015 + i % 9) for i in range(20)]
SHOW = [
    showcase("hexa-2025", date(2025, 2, 5), "dev"),
    showcase("hdb-2025", date(2025, 6, 19), "test"),
    showcase("lgx-2025", date(2025, 9, 30), "test"),
]


def run(records: list[IpoRecord] | None = None, **kw: float) -> dict[str, str]:
    result = assign(records if records is not None else NEWS + OLD + SHOW, SplitRules(**kw))
    return result.slices


def test_every_train_doc_is_before_every_test_doc() -> None:
    result = assign(NEWS + OLD + SHOW, SplitRules())
    check_strict(result, NEWS + OLD + SHOW)
    assert result.train_cut == date(2025, 6, 19)  # the earliest test-slice document (hdb)
    dates = {r.ipo_id: r.doc_date for r in NEWS}
    train_new = [dates[i] for i, s in result.slices.items() if s == "train" and i in dates]
    assert train_new
    assert max(train_new) < result.train_cut


def test_showcase_roles_are_kept_whatever_the_date() -> None:
    slices = run()
    assert slices["hexa-2025"] == "dev"  # before the cut, still dev, never train
    assert slices["hdb-2025"] == "test"
    assert slices["lgx-2025"] == "test"


def test_corpus_is_train() -> None:
    slices = run()
    assert all(slices[r.ipo_id] == "train" for r in OLD)


def test_after_the_cut_the_older_share_is_dev_and_the_newer_is_test() -> None:
    result = assign(NEWS + OLD + SHOW, SplitRules(dev_share=1 / 3))
    after = sorted((r for r in NEWS if r.doc_date and r.doc_date >= result.train_cut),
                   key=lambda r: r.doc_date or START)  # fmt: skip
    roles = [result.slices[r.ipo_id] for r in after]
    n_dev = roles.count("dev")
    assert roles == ["dev"] * n_dev + ["test"] * (len(roles) - n_dev)
    assert n_dev == round(len(after) / 3)


def test_assignment_is_deterministic_and_order_free() -> None:
    a = run(NEWS + OLD + SHOW)
    b = run(list(reversed(NEWS + OLD + SHOW)))
    assert a == b


def test_same_company_as_a_test_ipo_is_excluded() -> None:
    twin = IpoRecord.corpus("hdb-fin-2019", "HDB Financial Services Ltd.", 2019)
    hdb = showcase("hdb-2025", date(2025, 6, 19), "test", "HDB Financial Services Limited")
    rec = [*NEWS, twin, hdb]
    result = assign(rec, SplitRules())
    assert result.slices["hdb-2025"] == "test"
    assert "hdb-fin-2019" not in result.slices
    assert "same company as test IPO hdb-2025" in result.excluded["hdb-fin-2019"]


def test_corpus_year_at_or_after_the_cut_year_is_an_error() -> None:
    late = IpoRecord.corpus("late-co-2025", "Late Co Limited", 2025)
    with pytest.raises(SplitError, match="corpus"):
        assign([*NEWS, *SHOW, late], SplitRules())


def test_without_test_showcase_the_train_share_sets_the_cut() -> None:
    result = assign(NEWS, SplitRules(train_share=0.7, dev_share=1 / 3))
    counts = {s: list(result.slices.values()).count(s) for s in ("train", "dev", "test")}
    assert counts == {"train": 42, "dev": 6, "test": 12}
    check_strict(result, NEWS)


def test_demo_is_the_newest_test_ipos() -> None:
    result = assign(NEWS + OLD + SHOW, SplitRules(demo_newest=2))
    assert result.demo == [NEWS[-1].ipo_id, NEWS[-2].ipo_id]


def test_duplicate_ids_are_an_error() -> None:
    with pytest.raises(SplitError, match="duplicate"):
        assign([NEWS[0], NEWS[0]], SplitRules())


@settings(max_examples=60, deadline=None)
@given(
    offsets=st.lists(st.integers(min_value=0, max_value=1000), min_size=3, max_size=40),
    show=st.lists(
        st.tuples(st.integers(min_value=0, max_value=1000), st.sampled_from(["dev", "test"])),
        max_size=5,
    ),
)
def test_property_one_slice_per_ipo_and_strict(
    offsets: list[int], show: list[tuple[int, str]]
) -> None:
    recs = [new(i, START + timedelta(days=o)) for i, o in enumerate(offsets)]
    recs += [
        showcase(f"show-{i}-2025", START + timedelta(days=o), r) for i, (o, r) in enumerate(show)
    ]
    result = assign(recs, SplitRules())
    assert set(result.slices) | set(result.excluded) == {r.ipo_id for r in recs}
    assert not set(result.slices) & set(result.excluded)
    check_strict(result, recs)
