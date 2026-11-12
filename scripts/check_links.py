"""Check the relative links and images in the repository's Markdown files.

Every ``[text](target)`` and ``![alt](target)`` whose target is a relative path must point at a
file or folder that exists (the ``#anchor`` part is not checked). External links (``http``,
``mailto``) are not fetched, except links into this repository on GitHub
(``.../blob/main/<path>`` or ``.../tree/main/<path>``), which are checked against the working tree
because the docs site uses them for files outside ``docs/``. Files in ``docs/archive/`` are
skipped: they are kept exactly as they were when archived, so their old relative links may break.

    uv run python scripts/check_links.py            # every tracked .md file
    uv run python scripts/check_links.py README.md docs/index.md
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_PREFIXES = ("docs/archive/", "data/", "models/", "ml/handoff/data/", ".pytest_cache/")
LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]*`")
REPO_URL = re.compile(
    r"^https://github\.com/AkshatTm/Vidura-IPO-X-Ray/"
    r"(?:blob|tree)/main/(.+)$"
)


def tracked_markdown() -> list[str]:
    """Return the tracked Markdown files that are checked."""
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [f for f in out if not f.startswith(SKIP_PREFIXES)]


def dead_links(rel: str) -> list[tuple[int, str]]:
    """Return ``(line number, target)`` for each relative link in ``rel`` that does not resolve."""
    path = ROOT / rel
    bad: list[tuple[int, str]] = []
    in_fence = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK.findall(INLINE_CODE.sub("", line)):
            repo = REPO_URL.match(target)
            if repo:
                if not (ROOT / unquote(repo.group(1).split("#", 1)[0])).exists():
                    bad.append((n, target))
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith(("#", "/")):
                continue
            file_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not file_part:
                continue
            if not (path.parent / file_part).exists():
                bad.append((n, target))
    return bad


def main(argv: list[str]) -> int:
    """Print every dead link and return 1 when there is one."""
    files = argv or tracked_markdown()
    total = 0
    for rel in files:
        for n, target in dead_links(rel):
            print(f"{rel}:{n}: {target}")
            total += 1
    print(f"{total} dead relative link(s) in {len(files)} file(s)", file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
