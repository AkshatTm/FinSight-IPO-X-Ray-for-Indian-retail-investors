"""Re-detect sections into a separate directory, leaving ``data/processed`` untouched (C3.7b).

    uv run python scripts/sections_overlay.py --src data/processed --dst <dir> ipo_id [ipo_id ...]

Some ``sections.json`` files were written before the SUMMARY / RESTATED FINANCIAL INFORMATION
title patterns were widened, so the financials stage could not find the cash-flow statement or
the summary table in them (the section ids were slugs, not the canonical ids). This copies each
IPO's ``parsed*.json`` and ``xray.json`` to ``--dst`` and writes freshly detected
``sections*.json`` beside them; point ``summary_eval.py`` / ``redflag_eval.py`` at ``--dst`` with
``--processed``. Nothing under ``--src`` is modified.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def build_overlay(src: Path, dst: Path, ipo_ids: list[str]) -> dict[str, list[str]]:
    """Copy parsed documents and write fresh sections; returns the section ids changed per file."""
    from pydantic import TypeAdapter

    from finsight.core.schemas import ParsedDoc, Section
    from finsight.parse import find_sections

    adapter = TypeAdapter(list[Section])
    changed: dict[str, list[str]] = {}
    for ipo in ipo_ids:
        out = dst / ipo
        out.mkdir(parents=True, exist_ok=True)
        if (src / ipo / "xray.json").exists():
            shutil.copy2(src / ipo / "xray.json", out / "xray.json")
        for suffix in ("", "_prospectus"):
            parsed = src / ipo / f"parsed{suffix}.json"
            if not parsed.exists():
                continue
            shutil.copy2(parsed, out / parsed.name)
            sections = find_sections(ParsedDoc.model_validate_json(parsed.read_bytes()))
            target = out / f"sections{suffix}.json"
            target.write_bytes(adapter.dump_json(sections, indent=1))
            old_path = src / ipo / f"sections{suffix}.json"
            if old_path.exists():
                old = {s.id for s in adapter.validate_json(old_path.read_bytes())}
                new = {s.id for s in sections}
                changed[f"{ipo}{suffix}"] = sorted(new ^ old)
    return changed


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--dst", type=Path, required=True)
    ap.add_argument("ipo_ids", nargs="+")
    a = ap.parse_args(argv)
    for name, ids in build_overlay(a.src, a.dst, a.ipo_ids).items():
        print(f"{name}: {len(ids)} section ids differ from the stored file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
