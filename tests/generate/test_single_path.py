"""No caller reaches the language model except through ``generate.respond`` (ADR-048).

The first Hindi bake-off called the model directly and bypassed the guard. This test fails when
any module outside ``generate`` (the ask CLI, bake-off scripts, chat, API) streams from a backend
itself: new callers must use ``respond`` so the question guard and the output filters apply.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CALLS_THE_MODEL = re.compile(
    r"\.(?:stream|generate)\(|OllamaBackend\(|:11434"
)  # 11434 = the Ollama port
ALLOWED = {"src/finsight/generate/llm_backend.py", "src/finsight/generate/respond.py"}


def python_files() -> list[Path]:
    return [*(ROOT / "src").rglob("*.py"), *(ROOT / "scripts").glob("*.py")]


def test_only_respond_and_the_backend_call_the_model() -> None:
    offenders = []
    for path in python_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED:
            continue
        if CALLS_THE_MODEL.search(path.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert offenders == []
