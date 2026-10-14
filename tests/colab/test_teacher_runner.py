"""The Colab teacher runner turns c2_teacher.ipynb into a valid script (C2.3 fileno fix)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "notebooks" / "colab" / "teacher_runner.py"
NOTEBOOK = ROOT / "notebooks" / "colab" / "c2_teacher.ipynb"


def _build_script(preset: str) -> str:
    """Run the runner's notebook-to-script part on the committed notebook (no Colab, no HF)."""
    src = RUNNER.read_text(encoding="utf-8")
    start, end = src.index("_cells = "), src.index("compile(_script")
    ns: dict = {"PRESET": preset, "UNITS_BEFORE": 12.5, "TEACHER_PICK": "google/gemma-4-31B-it",
                "_nb": str(NOTEBOOK)}  # fmt: skip
    exec("import json, re\n" + src[start:end], ns)
    return ns["_script"]


def test_script_compiles_with_params_and_no_secret_lookup() -> None:
    script = _build_script("gold_eval")
    compile(script, "teacher_job.py", "exec")
    assert "PRESET = 'gold_eval'" in script
    assert "UNASSIGN = False" in script  # the kernel releases the GPU, not the job
    assert "UNITS_BEFORE = 12.5" in script
    assert 'userdata.get("HF_TOKEN")' not in script
    assert "if __name__ == '__main__':" in script
    assert "from __future__" not in script


def test_runner_never_prints_the_token() -> None:
    src = RUNNER.read_text(encoding="utf-8")
    assert not any("print(" in line and "_tok" in line for line in src.splitlines())
    assert "runtime.unassign()" in src.split("finally:")[1]
