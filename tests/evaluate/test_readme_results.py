import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "readme_results", Path(__file__).resolve().parents[2] / "scripts" / "readme_results.py"
)
assert SPEC is not None
assert SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def write(eval_dir: Path, name: str, data: object) -> None:
    (eval_dir / name).write_text(json.dumps(data), encoding="utf-8")


def test_rows_come_from_the_files_and_missing_files_are_left_out(tmp_path: Path) -> None:
    write(
        tmp_path,
        "ladder_table.json",
        {"ladder": {"rules": {"label": "Rung 1: rules", "test": {
            "full": {"nvm": 0.857}, "body_only": {"nvm": 0.229}}}}},
    )  # fmt: skip
    text = mod.render(tmp_path)
    assert "Rung 1: rules" in text
    assert "full 0.86, body-only 0.23" in text
    assert "verifier" not in text  # no file, no row
    assert "e7" not in text


def test_the_block_is_replaced_between_the_markers_only() -> None:
    readme = f"before\n{mod.START}\nold\n{mod.END}\nafter\n"
    out = mod.replace_block(readme, "NEW")
    assert out == f"before\n{mod.START}\nNEW\n{mod.END}\nafter\n"
    assert mod.replace_block(out, "NEW") == out  # idempotent
