"""Write the API's OpenAPI document to ``openapi.json`` (the frontend generates types from it).

uv run poe gen-openapi            # rewrite the file
uv run poe gen-openapi -- --check # exit 1 if the committed file is stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from finsight.api.app import create_app

OUT = Path(__file__).resolve().parents[1] / "openapi.json"


def render() -> str:
    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("openapi.json is stale: run `uv run poe gen-openapi`", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
