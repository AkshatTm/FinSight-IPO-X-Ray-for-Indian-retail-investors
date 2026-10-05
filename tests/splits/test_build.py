"""C1.4: `python -m finsight.splits build [--freeze]` on synthetic inputs (no real data)."""

import json
from pathlib import Path

import pytest

from finsight.splits import UNIVERSE_COLUMNS, load_splits, read_manifests
from finsight.splits.__main__ import main
from finsight.splits.assign import SplitRules
from finsight.splits.build import BuildError, BuildPaths, build, cover_date
from finsight.splits.retro import retro_manifests

SHA = "ab" * 32
DEMO = """ipos:
  - ipo_id: show-dev-2025
    split: dev
    company: "Show Dev Limited"
    rhp: {{file: r/a.pdf, pages: 500, sha256: {sha}, dated: "February 5, 2025"}}
    prospectus: {{file: p/a.pdf, pages: 500, sha256: {sha}, dated: "February 14, 2025"}}
  - ipo_id: show-test-2025
    split: test
    company: "Show Test Limited"
    rhp: {{file: r/b.pdf, pages: 600, sha256: {sha}, dated: "June 19, 2025"}}
    prospectus: {{file: p/b.pdf, pages: 600, sha256: {sha}, dated: "June 28, 2025"}}
"""


def universe_rows() -> list[str]:
    rows = []
    for i, day in enumerate(["2024-02-01", "2024-08-01", "2025-01-10", "2025-07-01", "2025-09-01",
                             "2025-12-01", "2026-02-01", "2026-04-01"]):  # fmt: skip
        rows.append(
            f"co-{i}-{day[:4]},Co {i} Limited,NSE,rhp,{day},,https://x/{i},{SHA},400,parsed,"
        )
    rows.append(
        f"broken-2025,Broken Limited,BSE,rhp,2025-05-01,,https://x/b,{SHA},,failed,parse timeout"
    )
    rows.append(
        f"show-test-2025,Show Test Limited,both,rhp,2025-06-19,,https://x/s,{SHA},600,parsed,"
    )
    return rows


@pytest.fixture
def paths(tmp_path: Path) -> BuildPaths:
    (tmp_path / "configs").mkdir()
    demo = tmp_path / "configs" / "demo_ipos.yaml"
    demo.write_text(DEMO.format(sha=SHA), encoding="utf-8")
    universe = tmp_path / "configs" / "ipo_universe.csv"
    universe.write_text("\n".join([",".join(UNIVERSE_COLUMNS), *universe_rows()]) + "\n",
                        encoding="utf-8")  # fmt: skip
    corpus = tmp_path / "processed" / "corpus"
    corpus.mkdir(parents=True)
    for i, year in enumerate([2019, 2021, 2023]):
        (corpus / f"old-{i}-{year}.json").write_text(json.dumps(
            {"ipo_id": f"old-{i}-{year}", "company": f"Old {i} Limited", "close_year": year,
             "pages": [{"number": 1, "text": "not read"}]}), encoding="utf-8")  # fmt: skip
    weak = tmp_path / "processed" / "weaklabel"
    weak.mkdir()
    (weak / "train.jsonl").write_text('{"ipo_id": "old-0-2019"}\n{"ipo_id": "old-1-2021"}\n',
                                      encoding="utf-8")  # fmt: skip
    (weak / "dev.jsonl").write_text('{"ipo_id": "old-2-2023"}\n', encoding="utf-8")
    return BuildPaths(
        universe=universe, corpus_dir=corpus, demo=demo, out=tmp_path / "configs" / "splits.yaml",
        manifests=tmp_path / "data" / "manifests", processed=tmp_path / "processed", root=tmp_path,
    )  # fmt: skip


def test_cover_date() -> None:
    assert cover_date("October 29, 2025").isoformat() == "2025-10-29"


def test_dry_run_prints_counts_and_writes_nothing(paths: BuildPaths) -> None:
    out = build(paths, SplitRules())
    assert not paths.out.exists()
    assert not paths.manifests.exists()
    text = "\n".join(out.report)
    assert "train cut (earliest test document): 2025-06-19" in text
    assert "dry run" in text
    assert "eval window n per test IPO" in text
    s = out.splits
    assert s.by_id()["show-test-2025"].slice == "test"
    assert s.by_id()["show-dev-2025"].slice == "dev"
    assert {e.ipo_id for e in s.ipos if e.slice == "train"} == {
        "old-0-2019",
        "old-1-2021",
        "old-2-2023",
        "co-0-2024",
        "co-1-2024",
        "co-2-2025",
    }
    assert [x.ipo_id for x in s.excluded] == ["broken-2025"]


def test_freeze_writes_splits_and_retro_manifests(paths: BuildPaths) -> None:
    out = build(paths, SplitRules(), freeze=True)
    saved = load_splits(paths.out)
    assert saved.frozen
    assert saved == out.splits
    names = {mf.artefact for mf in read_manifests(paths.manifests)}
    assert names == {"weaklabel_v1", "extractor_qa_v1", "bilstm_crf_v1", "guard_muril_v1"}
    assert "leakage check clean" in out.report[-1]
    with pytest.raises(Exception, match="C-ADR"):
        build(paths, SplitRules(), freeze=True)


def test_freeze_refused_while_rows_are_pending(paths: BuildPaths) -> None:
    with paths.universe.open("a", encoding="utf-8") as fh:
        fh.write(f"late-2026,Late Limited,NSE,rhp,2026-05-01,,https://x/l,{SHA},,downloaded,\n")
    assert any("not final yet" in line for line in build(paths, SplitRules()).report)
    with pytest.raises(BuildError, match="not final"):
        build(paths, SplitRules(), freeze=True)


def test_missing_universe_says_run_c11(paths: BuildPaths) -> None:
    paths.universe.unlink()
    with pytest.raises(BuildError, match=r"C1\.1"):
        build(paths, SplitRules())


def test_retro_without_weak_labels_says_so(tmp_path: Path) -> None:
    made, missing = retro_manifests(tmp_path / "nothing", tmp_path)
    assert [m.artefact for m in made] == ["guard_muril_v1"]
    assert made[0].ipo_ids == []
    assert "weak labels not found" in missing[0]


def test_cli_dry_run_and_check(paths: BuildPaths, capsys: pytest.CaptureFixture[str]) -> None:
    common = ["--universe", str(paths.universe), "--corpus-dir", str(paths.corpus_dir),
              "--out", str(paths.out), "--manifests", str(paths.manifests)]  # fmt: skip
    import finsight.splits.__main__ as cli

    cli_paths = cli._paths  # demo/processed come from the repo; point them at the fixture
    try:
        cli._paths = lambda args: paths  # type: ignore[assignment]
        assert main(["build", *common]) == 0
        assert "dry run" in capsys.readouterr().out
        assert main(["check", *common]) == 1  # not frozen yet
        assert main(["build", "--freeze", *common]) == 0
        assert main(["check", *common]) == 0
        assert main(["build", "--freeze", *common]) == 2  # frozen: needs --adr
        assert "C-ADR" in capsys.readouterr().err
    finally:
        cli._paths = cli_paths  # type: ignore[assignment]
