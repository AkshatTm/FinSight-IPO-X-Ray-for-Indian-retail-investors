"""Record real chat streams for demo mode (``uv run poe record-demo``).

    uv run poe record-demo -- --ipo ather-energy-2025            # one IPO
    uv run poe record-demo                                        # every IPO with an X-Ray

For each IPO it asks the suggested questions (normal, scale trick, Hindi, advice) plus the
extras below through the real orchestrator and stores every event exactly as sent
(``data/demo_cache/<ipo>/``). Needs ``ollama serve`` and the profile's models; stop Ollama
afterwards. Streams that end in an error are skipped, never patched.
"""

from __future__ import annotations

import argparse
import sys

from finsight.api.demo import DemoCache
from finsight.api.ipos import IpoStore
from finsight.chat import ChatOrchestrator
from finsight.core.config import get_settings, load_settings
from finsight.extract import load_fields

EXTRAS = [
    ("Will this IPO double on listing day?", "en"),
    ("What is the home address of the company's CEO?", "en"),
    ("पैसा कहाँ लगेगा?", "hi"),
]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="record-demo")
    parser.add_argument(
        "--ipo", action="append", help="IPO id (repeatable); default: all with an X-Ray"
    )
    parser.add_argument("--profile")
    parser.add_argument(
        "--question", action="append", help="record only this question text (repeatable)"
    )
    args = parser.parse_args(argv)

    settings = load_settings(args.profile) if args.profile else get_settings()
    store = IpoStore(settings.paths.processed_dir, load_fields())
    cache = DemoCache(settings.paths.data_dir / "demo_cache")
    chat = ChatOrchestrator.from_settings(args.profile)
    ids = args.ipo or [
        i.id for i in store.list_ipos(None, None, None, "listing_date") if i.xray_status == "ready"
    ]
    failed = 0
    for ipo_id in ids:
        questions = [(q.text, q.language) for q in store.suggested(ipo_id)] + EXTRAS
        if args.question:
            questions = [q for q in questions if q[0] in args.question]
        for text, language in questions:
            events = list(chat.events(ipo_id, text, language))  # type: ignore[arg-type]
            try:
                path = cache.record(ipo_id, text, language, events)
                print(f"recorded {ipo_id}: {text[:50]!r} -> {path.name}", flush=True)
            except ValueError as exc:
                failed += 1
                print(f"SKIPPED {ipo_id}: {text[:50]!r} ({exc})", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
