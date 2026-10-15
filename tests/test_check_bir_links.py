"""C1.5: link extraction from spreadsheet cells (no network)."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "check_bir_links", ROOT / "scripts" / "check_bir_links.py"
)
assert spec is not None
assert spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["check_bir_links"] = mod
spec.loader.exec_module(mod)


def test_extract_links_handles_lists_and_blanks() -> None:
    cell = "['https://a.example/x.pdf', 'http://b.example/y?z=1']"
    assert mod.extract_links(cell) == ["https://a.example/x.pdf", "http://b.example/y?z=1"]
    assert mod.extract_links(None) == []
    assert mod.extract_links("no link here") == []
