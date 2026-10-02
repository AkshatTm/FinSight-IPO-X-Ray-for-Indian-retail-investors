import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "bundle_artifacts", Path(__file__).resolve().parents[2] / "scripts" / "bundle_artifacts.py"
)
assert SPEC is not None
assert SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def make_root(tmp_path: Path) -> Path:
    def put(rel: str, text: str = "x") -> None:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    for rel in (
        "data/processed/a/xray.json",
        "data/processed/a/parsed.json",
        "data/processed/a/pages/1.webp",
        "data/processed/a/index/chunks.jsonl",
        "data/processed/a/index/dense.npy",
        "data/processed/a/candidates_rules.json",  # build intermediate: not bundled
        "data/processed/other/xray.json",  # not a demo IPO
        "data/demo_cache/a/k.json",
        "data/raw/rhp/a.pdf",
        "data/gold/gold.jsonl",
        "eval_results/ladder_table.json",
        "eval_results/ladder_table.csv",
        "eval_results/ladder/x.json",
        "configs/config.yaml",
    ):
        put(rel)
    return tmp_path


def names(files: list[tuple[Path, Path]]) -> set[str]:
    return {rel.as_posix() for _, rel in files}


def test_only_the_runtime_files_of_the_demo_ipos_are_bundled(tmp_path: Path) -> None:
    got = names(mod.plan(make_root(tmp_path), ["a"]))
    assert "data/processed/a/xray.json" in got
    assert "data/processed/a/pages/1.webp" in got
    assert "data/processed/a/index/chunks.jsonl" in got
    assert "data/demo_cache/a/k.json" in got
    assert "eval_results/ladder_table.csv" in got
    assert not any(n.startswith("data/raw") or n.startswith("data/gold") for n in got)
    assert "data/processed/other/xray.json" not in got
    assert "data/processed/a/candidates_rules.json" not in got
    assert len([n for n in got if n.endswith("ladder_table.json")]) == 1


def test_dense_index_and_pages_are_options(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    assert "data/processed/a/index/dense.npy" not in names(mod.plan(root, ["a"]))
    assert "data/processed/a/index/dense.npy" in names(mod.plan(root, ["a"], dense=True))
    assert "data/processed/a/pages/1.webp" not in names(mod.plan(root, ["a"], pages=False))


def test_the_manifest_lists_every_file_with_a_hash(tmp_path: Path) -> None:
    root = make_root(tmp_path / "repo")
    out = tmp_path / "out"
    manifest = mod.bundle(root, out, ["a"], pages=True, dense=False)
    on_disk = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    assert on_disk["n_files"] == manifest["n_files"] == len(on_disk["files"])
    assert all(len(f["sha256"]) == 64 for f in on_disk["files"])
    assert (out / "data/processed/a/xray.json").read_text(encoding="utf-8") == "x"
