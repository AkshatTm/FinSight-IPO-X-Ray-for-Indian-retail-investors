"""Ask one question through the same event stream the API sends.

    uv run python -m finsight.chat ask --ipo ather-energy-2025 "How will the money be used?"
    uv run python -m finsight.chat ask --ipo ather-energy-2025 --lang hi "पैसा कहाँ लगेगा?"

Prints every SSE event (name and a short payload) so the order and content can be read in a
terminal; tokens are joined on one line. Needs Ollama for a real answer (`ollama serve`).
"""

from __future__ import annotations

import argparse
import sys

from finsight.chat.orchestrator import ChatOrchestrator


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.chat")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="answer one question and print the events")
    ask.add_argument("--ipo", required=True)
    ask.add_argument("--lang", choices=["en", "hi"], default="en")
    ask.add_argument("--profile")
    ask.add_argument("question")
    args = parser.parse_args(argv)

    chat = ChatOrchestrator.from_settings(args.profile)
    status = 0
    for name, event in chat.events(args.ipo, args.question, args.lang):
        if name == "token":
            print(event.text, end="", flush=True)  # type: ignore[attr-defined]
            continue
        print("\n[" + name + "] " + event.model_dump_json(exclude_none=True)[:400])
        if name == "error":
            status = 2
    print()
    return status


if __name__ == "__main__":
    sys.exit(main())
