"""Strict time split (C-ADR-02, C02 §4): every `train` document is dated before every `test` one.

Rules, in order:

1. Showcase IPOs keep their role from ``configs/demo_ipos.yaml`` (dev or test), whatever the date.
2. The **train cut** is the earliest test-slice document. With test showcase IPOs that is the
   earliest of them; without, the oldest ``train_share`` of the new documents set it.
3. Corpus IPOs (2009–2023, close year only) and new documents dated before the cut are `train`.
4. Non-showcase new documents on or after the cut: the older ``dev_share`` is `dev`, the rest
   `test`.
5. Any non-test IPO with the same company key as a test IPO is excluded (a re-filer or a renamed
   company would otherwise leak the test company into training).

Split is by IPO, never by passage or risk. ``demo`` is the newest few test IPOs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from finsight.risks import company_key

Slice = Literal["train", "dev", "test"]
Source = Literal["corpus", "new", "showcase"]


class SplitError(ValueError):
    """The inputs cannot give a strict split (the message says why)."""


@dataclass(frozen=True)
class IpoRecord:
    """One IPO as the split sees it: identity, date and where it came from."""

    ipo_id: str
    company: str
    source: Source
    doc_date: date | None = None  # new + showcase documents: the cover date
    close_year: int | None = None  # corpus IPOs only have the issue's close year
    role: Literal["dev", "test"] | None = None  # showcase role from demo_ipos.yaml

    @property
    def company_key(self) -> str:
        """Loose company identity, shared with the risk bank (``finsight.risks.company_key``)."""
        return company_key(self.company)

    @classmethod
    def new(cls, ipo_id: str, company: str, doc_date: date) -> IpoRecord:
        """A newly collected offer document (C1.1 universe)."""
        return cls(ipo_id, company, "new", doc_date=doc_date)

    @classmethod
    def corpus(cls, ipo_id: str, company: str, close_year: int | None) -> IpoRecord:
        """An older corpus IPO (text only, close year only)."""
        return cls(ipo_id, company, "corpus", close_year=close_year)

    @classmethod
    def showcase(cls, ipo_id: str, company: str, doc_date: date, role: str) -> IpoRecord:
        """A showcase IPO with its fixed role."""
        if role not in ("dev", "test"):
            raise SplitError(f"showcase role must be dev or test, got {role!r} for {ipo_id}")
        return cls(ipo_id, company, "showcase", doc_date=doc_date, role=role)  # type: ignore[arg-type]


@dataclass(frozen=True)
class SplitRules:
    """Shares and sizes; recorded in ``splits.yaml`` so the split can be rebuilt exactly."""

    dev_share: float = 1 / 3  # of the non-showcase documents on or after the cut
    train_share: float = 0.7  # only used when there is no test showcase IPO
    demo_newest: int = 3


@dataclass
class SplitResult:
    """``slices`` maps every kept IPO to its slice; ``excluded`` maps the rest to a reason."""

    slices: dict[str, Slice]
    excluded: dict[str, str] = field(default_factory=dict)
    train_cut: date | None = None
    demo: list[str] = field(default_factory=list)


def _day(r: IpoRecord) -> date:
    assert r.doc_date is not None
    return r.doc_date


def assign(records: list[IpoRecord], rules: SplitRules) -> SplitResult:
    """Assign every IPO to train, dev or test under the strict rule (module docstring)."""
    ids = [r.ipo_id for r in records]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SplitError(f"duplicate ipo_id: {', '.join(dupes)}")
    for r in records:
        if r.source != "corpus" and r.doc_date is None:
            raise SplitError(f"{r.ipo_id}: a {r.source} document needs a doc_date")

    slices: dict[str, Slice] = {}
    shows = [r for r in records if r.source == "showcase"]
    for r in shows:
        slices[r.ipo_id] = r.role  # type: ignore[assignment]
    news = sorted((r for r in records if r.source == "new"), key=lambda r: (_day(r), r.ipo_id))

    test_show = [_day(r) for r in shows if r.role == "test"]
    cut: date | None = None
    if test_show:
        first = min(test_show)
        before = [r for r in news if _day(r) < first]
        after = [r for r in news if _day(r) >= first]
    else:
        n_train = round(len(news) * rules.train_share)
        before, after = news[:n_train], news[n_train:]
    n_dev = round(len(after) * rules.dev_share)
    for r in before:
        slices[r.ipo_id] = "train"
    for i, r in enumerate(after):
        slices[r.ipo_id] = "dev" if i < n_dev else "test"

    test_dates = [_day(r) for r in news + shows if slices[r.ipo_id] == "test"]
    cut = min(test_dates) if test_dates else cut
    if cut is not None:  # ties on the cut day (no test showcase): such train docs become dev
        for r in before:
            if _day(r) >= cut:
                slices[r.ipo_id] = "dev"

    for r in records:
        if r.source == "corpus":
            if cut is not None and r.close_year is not None and r.close_year >= cut.year:
                raise SplitError(
                    f"corpus IPO {r.ipo_id} closed in {r.close_year}, not before the train cut "
                    f"{cut.isoformat()}; the corpus must be older than every test document"
                )
            slices[r.ipo_id] = "train"

    excluded: dict[str, str] = {}
    test_keys = {r.company_key: r.ipo_id for r in records if slices.get(r.ipo_id) == "test"}
    for r in records:
        hit = test_keys.get(r.company_key)
        if slices.get(r.ipo_id) != "test" and hit is not None:
            excluded[r.ipo_id] = f"same company as test IPO {hit}"
            del slices[r.ipo_id]

    by_id = {r.ipo_id: r for r in records}
    tests = sorted((i for i, s in slices.items() if s == "test"),
                   key=lambda i: (_day(by_id[i]), i), reverse=True)  # fmt: skip
    return SplitResult(slices, excluded, cut, tests[: rules.demo_newest])


def check_strict(result: SplitResult, records: list[IpoRecord]) -> None:
    """Raise ``SplitError`` unless every train document is dated before every test document."""
    by_id = {r.ipo_id: r for r in records}
    tests = [by_id[i] for i, s in result.slices.items() if s == "test"]
    trains = [by_id[i] for i, s in result.slices.items() if s == "train"]
    if not tests:
        return
    first_test = min(_day(r) for r in tests)
    late = [r.ipo_id for r in trains if r.doc_date is not None and r.doc_date >= first_test]
    late += [
        r.ipo_id for r in trains
        if r.doc_date is None and r.close_year is not None and r.close_year >= first_test.year
    ]  # fmt: skip
    if late:
        raise SplitError(f"train documents not before the first test document: {', '.join(late)}")
    leaked = {r.company_key for r in trains} & {r.company_key for r in tests}
    if leaked:
        raise SplitError(f"companies in both train and test: {', '.join(sorted(leaked))}")
