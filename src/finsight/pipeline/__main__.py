"""Offline pipeline CLI.

uv run python -m finsight.pipeline build --ipo meesho-2025 [--doc rhp|prospectus|both]
                                        [--stage parse] [--no-images]
uv run python -m finsight.pipeline build-all [--no-images]
uv run python -m finsight.pipeline inspect --ipo meesho-2025 [--doc rhp] --stats
uv run python -m finsight.pipeline inspect --ipo meesho-2025 --page 1 [--lines 20]
uv run python -m finsight.pipeline inspect --ipo meesho-2025 --grep "fresh issue"
                                          [--write-samples NAME]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import cast

from finsight.core.config import get_settings
from finsight.core.schemas import DocType
from finsight.ingest.registry import DemoIpo, get_demo_ipo, list_demo_ipos
from finsight.pipeline import inspect as insp
from finsight.pipeline.parse_stage import ParseReport, load_parsed, run_parse

STAGES = ["parse"]


def _docs(choice: str) -> list[DocType]:
    return ["rhp", "prospectus"] if choice == "both" else [cast(DocType, choice)]


def _build(ipo: DemoIpo, docs: list[DocType], images: bool) -> list[ParseReport]:
    processed = get_settings().paths.processed_dir
    reports = []
    for doc in docs:
        pdf = ipo.rhp.file if doc == "rhp" else ipo.prospectus.file
        report = run_parse(pdf, processed, ipo.ipo_id, doc, images=images)
        print(
            f"{ipo.ipo_id:28} {doc:10} pages={report.pages:4} scanned={report.scanned_pages:3} "
            f"printed={report.pages_with_printed_number:4} parse={report.parse_s:6.1f}s "
            f"images={report.images_s:6.1f}s",
            flush=True,
        )
        reports.append(report)
    return reports


def _write_timing(reports: list[ParseReport]) -> None:
    out = get_settings().paths.eval_dir / "parse_timing.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    for r in reports:
        existing[f"{r.ipo_id}:{r.doc}"] = r.as_dict()
    out.write_text(
        json.dumps(dict(sorted(existing.items())), indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="finsight.pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="run pipeline stages for one IPO")
    build.add_argument("--ipo", required=True)
    build.add_argument("--doc", choices=["rhp", "prospectus", "both"], default="both")
    build.add_argument("--stage", choices=STAGES, default="parse")
    build.add_argument("--no-images", action="store_true")

    build_all = sub.add_parser("build-all", help="run pipeline stages for every demo IPO")
    build_all.add_argument("--stage", choices=STAGES, default="parse")
    build_all.add_argument("--no-images", action="store_true")

    ins = sub.add_parser("inspect", help="capped view of a parsed document (<= 40 lines)")
    ins.add_argument("--ipo", required=True)
    ins.add_argument("--doc", choices=["rhp", "prospectus"], default="rhp")
    ins.add_argument("--stats", action="store_true")
    ins.add_argument("--page", type=int)
    ins.add_argument("--lines", type=int, default=20)
    ins.add_argument("--grep")
    ins.add_argument("--write-samples", metavar="NAME", help="with --grep: data/samples/NAME.jsonl")

    args = parser.parse_args(argv)

    if args.command == "build":
        _write_timing(_build(get_demo_ipo(args.ipo), _docs(args.doc), not args.no_images))
    elif args.command == "build-all":
        reports: list[ParseReport] = []
        for ipo in list_demo_ipos():
            reports += _build(ipo, ["rhp", "prospectus"], not args.no_images)
            _write_timing(reports)
    else:
        settings = get_settings()
        doc = load_parsed(settings.paths.processed_dir, args.ipo, cast(DocType, args.doc))
        lines: list[str] = []
        if args.stats:
            lines += insp.stats(doc)
        if args.page:
            lines += insp.page_lines(doc, args.page, args.lines)
        if args.grep:
            lines += insp.grep(doc, args.grep)
            if args.write_samples:
                out = settings.paths.samples_dir / f"{args.write_samples}.jsonl"
                lines.append(f"wrote {insp.write_samples(doc, args.grep, out)} snippets to {out}")
        print("\n".join(insp._cap(lines or insp.stats(doc))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
