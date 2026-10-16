"""Reading answers back: Task A JSON replies and pasted frontier bundles.

Nothing here guesses. A Task A reply that holds no readable JSON object is ``unparseable`` and
every field of it scores as missing; a field the reply leaves out is missing too. A pasted bundle
is split on its ``### <prompt id>`` headings; a heading that is absent or empty is reported.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from finsight.bench.prompts import STATUSES

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


@dataclass
class FieldAnswer:
    """One field of a Task A reply."""

    id: str
    status: str
    value: str = ""
    unit: str = ""
    page: int | None = None


@dataclass
class TaskAReply:
    """A parsed Task A reply: the fields read and any problems found."""

    fields: dict[str, FieldAnswer] = field(default_factory=dict)
    unparseable: bool = False
    problems: list[str] = field(default_factory=list)


def _objects(text: str) -> Iterable[str]:
    """Candidate JSON texts: fenced blocks first, then the outermost ``{...}`` span."""
    yield from (m.group(1) for m in _FENCE.finditer(text))
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        yield text[start : end + 1]


def _load(text: str) -> Any:
    for candidate in _objects(text):
        for attempt in (candidate, _TRAILING_COMMA.sub(r"\1", candidate)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError:
                continue
    return None


def _page(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def _entry(fid: str, item: dict[str, Any], problems: list[str]) -> FieldAnswer:
    """One ``{status, value, unit, page}`` entry; an unknown status is flagged and not found."""
    status = str(item.get("status") or "").strip().lower().replace(" ", "_")
    if status not in STATUSES:
        problems.append(f"{fid}: status {status!r}")
        status = "not_found"
    value = item.get("value")
    return FieldAnswer(
        id=fid,
        status=status,
        value="" if value is None else str(value).strip(),
        unit=str(item.get("unit") or "").strip(),
        page=_page(item.get("page")),
    )


FLAT = "flat_format: keyed by field id instead of a fields list"
"""First problem of a reply read by ``_flat`` (counted separately by the bench scorer)."""

_NOT_FOUND = re.compile(r"^\s*(?:not[ _]found|n/?a|none|null|unknown|-)?\s*$", re.I)


def _flat(data: dict[str, Any], wanted: Sequence[str]) -> TaskAReply:
    """A reply that maps field ids straight to values: value only, no unit or page.

    Only the obvious statuses are read from the value: empty / "not found" is ``not_found`` and
    ``[●]`` is ``placeholder``; anything else is ``found`` as written.
    """
    reply = TaskAReply(problems=[FLAT])
    for fid in wanted:
        if fid not in data:
            reply.problems.append(f"{fid}: missing")
            continue
        raw = data[fid]
        if isinstance(raw, dict) and ("status" in raw or "value" in raw):  # {"<id>": {entry}}
            reply.fields[fid] = _entry(fid, raw, reply.problems)
            continue
        value = "" if raw is None else str(raw).strip()
        if isinstance(raw, dict | list):
            value = json.dumps(raw, ensure_ascii=False)
        status = (
            "placeholder" if "[●]" in value or "[•]" in value
            else "not_found" if _NOT_FOUND.match(value)
            else "found"
        )  # fmt: skip
        reply.fields[fid] = FieldAnswer(id=fid, status=status, value=value)
    return reply


def parse_task_a(text: str, wanted: Sequence[str]) -> TaskAReply:
    """Read the fields ``wanted`` (ids like ``revenue@latest``) from a Task A reply."""
    data = _load(text)
    items = data.get("fields") if isinstance(data, dict) else data
    if isinstance(data, dict) and not isinstance(items, list):
        flat = items if isinstance(items, dict) else data
        if any(w in flat for w in wanted):  # {"<field id>": "<value>"}: value only
            return _flat(flat, wanted)
    if not isinstance(items, list):
        return TaskAReply(unparseable=True, problems=["no JSON object with a fields list"])
    reply = TaskAReply()
    for item in items:
        if not isinstance(item, dict) or "id" not in item:
            reply.problems.append("an entry without an id")
            continue
        fid = str(item["id"]).strip()
        reply.fields[fid] = _entry(fid, item, reply.problems)
    reply.problems += [f"{w}: missing" for w in wanted if w not in reply.fields]
    return reply


# ----------------------------------------------------------------------------- paste bundles
BUNDLE_HEAD = """You will get {n} separate tasks from an evaluation. Treat each task on its own, \
as if it were the only message, and follow that task's own rules exactly. Do not use web search or \
anything you remember about this company; use only the text inside each task.
Answer every task, in order, under its own heading line, exactly like this:
### <task id>
<your answer to that task>
Write nothing before the first heading and nothing after the last answer."""


def bundle(prompts: Sequence[tuple[str, str]]) -> str:
    """One paste-ready message from ``(prompt_id, text)`` pairs."""
    parts = [BUNDLE_HEAD.format(n=len(prompts))]
    parts += [f"=== TASK {pid} ===\n{text}\n=== END OF TASK {pid} ===" for pid, text in prompts]
    return "\n\n".join(parts)


_HEADING = re.compile(r"^#{2,4}\s*(?:task\s*)?([A-Za-z]:[\w.\-]+(?::[\w.\-@]+)*)\s*$", re.M | re.I)


def split_bundle(reply: str, expected: Sequence[str]) -> tuple[dict[str, str], list[str]]:
    """``({prompt_id: answer}, problems)`` from a pasted reply to ``bundle``."""
    found = list(_HEADING.finditer(reply))
    out: dict[str, str] = {}
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(reply)
        pid = m.group(1)
        if pid in expected:
            out[pid] = reply[m.end() : end].strip()
    problems = [f"{pid}: no answer" for pid in expected if not out.get(pid)]
    problems += [f"{m.group(1)}: unexpected heading" for m in found if m.group(1) not in expected]
    return out, problems
