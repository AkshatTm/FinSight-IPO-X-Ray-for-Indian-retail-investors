"""Report which environment variables a profile still needs. Prints names only, never values.

uv run python scripts/check_env.py full
"""

from __future__ import annotations

import sys

from finsight.core.config import REQUIRED_ENV, missing_env


def main(argv: list[str]) -> int:
    profile = argv[1] if len(argv) > 1 else "dev_light"
    if profile not in REQUIRED_ENV:
        print(f"{profile}: no required environment variables")
        return 0
    missing = missing_env(profile)
    if missing:
        print(f"{profile}: missing {', '.join(missing)}")
        return 1
    print(f"{profile}: all required environment variables are set")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
