"""Gold value file: schema, validator, empty template, self-consistency (05 section 2).

Akshat labels ``data/gold/gold_values.jsonl`` by hand, blind, from the PDFs: one line per
(ipo, field, document) with the value exactly as printed, the PDF page and the quote it came
from. This module never writes values; it only checks that the file is well formed.

    uv run python -m finsight.evaluate.gold template            # data/gold/gold_template.jsonl
    uv run python -m finsight.evaluate.gold validate [--complete] [path]
    uv run python -m finsight.evaluate.gold consistency first.jsonl second.jsonl
    uv run python -m finsight.evaluate.gold export-xlsx            # labelling sheet (git-ignored)
    uv run python -m finsight.evaluate.gold import-xlsx [--partial]  # sheet -> gold_values.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.core.schemas import Count, Money, Placeholder, Range
from finsight.ingest.registry import list_demo_ipos
from finsight.normalize import equal, parse_amount

# field id -> value type (01_PRD section 5.4)
FIELDS: dict[str, str] = {
    "fresh_issue_size": "money",
    "ofs_shares": "count",
    "ofs_amount": "money",
    "offer_price": "money",
    "price_band": "range",
    "total_issue_size": "money",
    "face_value": "money",
    "book_running_lead_managers": "list",
    "registrar": "text",
    "promoters": "list",
    "objects_of_offer": "table",
}
# The document a field is normally read from (ADR-023); the other one may be labelled too.
DEFAULT_DOC: dict[str, str] = {f: "rhp" for f in FIELDS} | {
    "offer_price": "prospectus",
    "total_issue_size": "prospectus",
}
STATUSES = ("present", "not_in_document", "placeholder")
DOCS = ("rhp", "prospectus")
LABEL_SOURCES = ("hand", "ai_assisted_verified")  # ADR-035; a missing label_source means "hand"
AI_TAG = "[AI-prefilled, needs human verification]"
Key = tuple[str, str, str]  # (ipo_id, field_id, doc)


_MARKS = re.compile(r"[\^*#†‡]")  # footnote marks printed after a number or name


_NOTE_REFS = re.compile(r"(?<=[^\W\d_])(?:\(\d{1,2}\))+")  # note references glued to a word


def _clean(text: str) -> str:
    return _MARKS.sub("", text).replace("•", "●").casefold()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", _clean(text))


def _words(text: str) -> list[str]:
    bare = _NOTE_REFS.sub("", _clean(text))  # "purposes(1)(2)" -> "purposes"
    return [w.strip(",;:.") for w in bare.split() if w.strip(",;:.")]


def _in_order(needle: str, haystack: str) -> bool:
    """Every word of ``needle`` appears in ``haystack`` in the same order, gaps allowed."""
    rest = iter(_words(haystack))
    return all(word in rest for word in _words(needle))


def _appears(text: str, quote: str, loose: bool) -> bool:
    if _compact(text) in _compact(quote):
        return True
    return loose and _in_order(text, quote)


def _pages(ipo_id: str, doc: str) -> int | None:
    for ipo in list_demo_ipos():
        if ipo.ipo_id == ipo_id:
            return (ipo.rhp if doc == "rhp" else ipo.prospectus).pages
    return None


def _value_problems(field_id: str, kind: str, value: Any, status: str) -> list[str]:
    if kind in ("money", "count", "range"):
        if not isinstance(value, str):
            return [f"{field_id}: value_raw must be text"]
        amount = parse_amount(value)
        if status == "placeholder":
            return [] if isinstance(amount, Placeholder) else ["placeholder: value_raw must be [●]"]
        if isinstance(amount, Placeholder):
            return ["value is [●]; use status=placeholder"]
        expected = {"money": Money, "count": Count, "range": Range}[kind]
        if not isinstance(amount, expected):
            return [f"value_raw {value!r} does not parse as {kind}"]
        return []
    if kind == "text":
        return [] if isinstance(value, str) and value.strip() else ["value_raw must be text"]
    if kind == "list":
        ok = isinstance(value, list) and value and all(isinstance(x, str) and x for x in value)
        return [] if ok else ["value_raw must be a list of text"]
    pairs = (
        isinstance(value, list)
        and value
        and all(
            isinstance(p, list) and len(p) == 2 and all(isinstance(x, str) for x in p)
            for p in value
        )
    )
    return [] if pairs else ["value_raw must be a list of [purpose, amount] pairs"]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [s for item in value for s in _strings(item)]


def validate_row(raw: dict[str, Any]) -> list[str]:
    """Problems with one gold line (empty list = valid)."""
    out: list[str] = []
    ipo_id, field_id, doc = raw.get("ipo_id"), raw.get("field_id"), raw.get("doc")
    known = {i.ipo_id for i in list_demo_ipos()}
    if ipo_id not in known:
        out.append(f"unknown ipo_id {ipo_id!r}")
    if field_id not in FIELDS:
        out.append(f"unknown field_id {field_id!r}")
    if doc not in DOCS:
        out.append(f"doc must be rhp or prospectus, got {doc!r}")
    status = raw.get("status")
    if status not in STATUSES:
        out.append(f"status must be one of {', '.join(STATUSES)}")
        return out
    value, page, quote = raw.get("value_raw"), raw.get("page"), raw.get("quote") or ""
    source = raw.get("label_source", "hand")
    if source not in LABEL_SOURCES:
        out.append(f"label_source must be one of {', '.join(LABEL_SOURCES)}")
    total = _pages(str(ipo_id), str(doc)) if ipo_id in known and doc in DOCS else None
    if status == "not_in_document":
        # value stays empty; page and quote may be kept as evidence (for example "will not
        # receive any proceeds from the Offer" for a pure offer for sale)
        if value not in ("", None, []):
            out.append("not_in_document rows have no value_raw")
        if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
            out.append("page must be a PDF page number >= 1")
        elif isinstance(page, int) and total is not None and page > total:
            out.append(f"page {page} is beyond the document ({total} pages)")
        return out
    if value in ("", None, []):
        out.append("value_raw is empty")
    try:
        date.fromisoformat(str(raw.get("labelled_at")))
    except ValueError:
        out.append("labelled_at must be an ISO date (2026-10-08)")
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        out.append("page must be a PDF page number >= 1")
    elif total is not None and page > total:
        out.append(f"page {page} is beyond the document ({total} pages)")
    if not quote.strip():
        out.append("quote is empty")
    if field_id in FIELDS and value not in ("", None, []):
        out += _value_problems(str(field_id), FIELDS[str(field_id)], value, status)
        loose = FIELDS[str(field_id)] in ("text", "list", "table")
        if quote.strip() and not all(_appears(s, quote, loose) for s in _strings(value)):
            out.append("value_raw does not appear in the quote")
    return out


def convert_prefill(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format fixes for an AI-prefilled file (ADR-035). Values and quotes are never changed."""
    out: list[dict[str, Any]] = []
    for raw in rows:
        r = dict(raw)
        if r.get("doc") == "pro":
            r["doc"] = "prospectus"
        value = r.get("value_raw")
        if FIELDS.get(str(r.get("field_id"))) == "table" and isinstance(value, list):
            r["value_raw"] = [
                item.rsplit(" :: ", 1) if isinstance(item, str) and " :: " in item else item
                for item in value
            ]
        r["label_source"] = "ai_assisted_verified"
        r["notes"] = str(r.get("notes") or "").replace(AI_TAG, "").strip()
        out.append(r)
    return out


def expected_keys() -> set[Key]:
    return {(i.ipo_id, f, DEFAULT_DOC[f]) for i in list_demo_ipos() for f in FIELDS}


def _read(path: Path) -> list[tuple[int, dict[str, Any] | None]]:
    rows: list[tuple[int, dict[str, Any] | None]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            obj = None
        rows.append((n, obj if isinstance(obj, dict) else None))
    return rows


def validate_file(path: Path, require_complete: bool = False) -> list[str]:
    """One message per bad line (``line 7: ...``), then ``missing ...`` lines if required."""
    issues: list[str] = []
    seen: dict[Key, int] = {}
    for n, obj in _read(path):
        if obj is None:
            issues.append(f"line {n}: not a JSON object")
            continue
        problems = validate_row(obj)
        key = (str(obj.get("ipo_id")), str(obj.get("field_id")), str(obj.get("doc")))
        if key in seen:
            issues.append(f"line {n}: duplicate of line {seen[key]} {key}")
        else:
            seen[key] = n
        if problems:
            issues.append(f"line {n}: " + "; ".join(problems))
    if require_complete:
        issues += [f"missing {k}" for k in sorted(expected_keys() - set(seen))]
    return issues


def template_rows(ipo_id: str | None = None) -> list[dict[str, Any]]:
    """One empty row per (ipo, field) in its default document. No values, on purpose."""
    return [
        {"ipo_id": i.ipo_id, "field_id": f, "doc": DEFAULT_DOC[f], "value_raw": "", "page": None,
         "quote": "", "status": "", "labelled_at": "", "notes": ""}
        for i in list_demo_ipos()
        if ipo_id in (None, i.ipo_id)
        for f in FIELDS
    ]  # fmt: skip


@dataclass
class Consistency:
    n: int = 0
    agree: int = 0
    disagreements: list[Key] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.agree / self.n if self.n else 0.0


def _same(kind: str, a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a.get("status") != b.get("status"):
        return False
    if a.get("status") == "not_in_document":
        return True
    va, vb = a.get("value_raw"), b.get("value_raw")
    if kind in ("money", "count", "range") and isinstance(va, str) and isinstance(vb, str):
        pa, pb = parse_amount(va), parse_amount(vb)
        return pa is not None and pb is not None and equal(pa, pb)
    if kind == "text":
        return _compact(str(va)) == _compact(str(vb))
    if kind == "list":
        return {_compact(s) for s in _strings(va)} == {_compact(s) for s in _strings(vb)}
    return {_compact(p[0]) for p in va} == {_compact(p[0]) for p in vb}


def self_consistency(first: Path, second: Path) -> Consistency:
    """Agreement between two labelling passes over the same keys (05 section 2, rule 4)."""

    def by_key(path: Path) -> dict[Key, dict[str, Any]]:
        return {
            (str(o["ipo_id"]), str(o["field_id"]), str(o["doc"])): o
            for _, o in _read(path)
            if o is not None
        }

    a, b = by_key(first), by_key(second)
    report = Consistency()
    for key in sorted(a.keys() & b.keys()):
        report.n += 1
        if _same(FIELDS.get(key[1], "text"), a[key], b[key]):
            report.agree += 1
        else:
            report.disagreements.append(key)
    return report


def _import_prefill(src: Path, out: Path) -> int:
    rows = [obj for _, obj in _read(src) if obj is not None]
    converted = convert_prefill(rows)
    tmp = out.with_suffix(".tmp")
    lines = [json.dumps(r, ensure_ascii=False) for r in converted]
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    issues = validate_file(tmp, require_complete=True)
    if issues:
        tmp.unlink()
        print(f"{len(issues)} problem(s); nothing was written:")
        print("\n".join(issues[:60]))
        return 1
    tmp.replace(out)
    print(f"OK: wrote {len(converted)} rows to {out}")
    return 0


def _xlsx_command(args: argparse.Namespace) -> int:
    from finsight.evaluate.gold_xlsx import export_xlsx, import_xlsx

    if args.command == "export-xlsx":
        try:
            print(f"wrote {export_xlsx(args.xlsx, args.force)}")
        except FileExistsError as exc:
            print(exc)
            return 1
        return 0
    result = import_xlsx(args.xlsx, args.out, args.partial)
    if result.errors:
        print(f"{len(result.errors)} problem(s) to fix in {args.xlsx.name}; nothing was written:\n")
        print("\n".join(result.errors[:60]))
        if len(result.errors) > 60:
            print(f"... and {len(result.errors) - 60} more")
        return 1
    note = f" ({result.unfilled} rows not filled in yet)" if result.unfilled else ""
    print(f"OK: wrote {result.written} values to {args.out}{note}")
    return 0


def main(argv: list[str] | None = None) -> int:
    gold_dir = get_settings().paths.gold_dir
    parser = argparse.ArgumentParser(description="Gold value file tools (P1.7)")
    sub = parser.add_subparsers(dest="command", required=True)
    tpl = sub.add_parser("template", help="write an empty template (no values)")
    tpl.add_argument("--ipo")
    tpl.add_argument("--out", type=Path, default=gold_dir / "gold_template.jsonl")
    val = sub.add_parser("validate", help="check a gold file")
    val.add_argument("path", nargs="?", type=Path, default=gold_dir / "gold_values.jsonl")
    val.add_argument("--complete", action="store_true", help="every ipo x field must be present")
    con = sub.add_parser("consistency", help="agreement between two labelling passes")
    con.add_argument("first", type=Path)
    con.add_argument("second", type=Path)
    exp = sub.add_parser("export-xlsx", help="write the Excel labelling sheet")
    exp.add_argument("--xlsx", type=Path, default=gold_dir / "gold_labelling.xlsx")
    exp.add_argument("--force", action="store_true", help="overwrite an existing sheet")
    imp = sub.add_parser("import-xlsx", help="filled sheet -> gold_values.jsonl, then validate")
    imp.add_argument("--xlsx", type=Path, default=gold_dir / "gold_labelling.xlsx")
    imp.add_argument("--out", type=Path, default=gold_dir / "gold_values.jsonl")
    imp.add_argument("--partial", action="store_true", help="skip rows not filled in yet")
    pre = sub.add_parser("import-prefill", help="AI-prefilled jsonl -> gold_values.jsonl (ADR-035)")
    pre.add_argument("--src", type=Path, default=gold_dir / "gold_prefill.jsonl")
    pre.add_argument("--out", type=Path, default=gold_dir / "gold_values.jsonl")
    args = parser.parse_args(argv)

    if args.command == "import-prefill":
        return _import_prefill(args.src, args.out)
    if args.command in ("export-xlsx", "import-xlsx"):
        return _xlsx_command(args)
    if args.command == "template":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(r, ensure_ascii=False) for r in template_rows(args.ipo)]
        args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {len(lines)} empty rows to {args.out}")
        return 0
    if args.command == "consistency":
        report = self_consistency(args.first, args.second)
        print(f"agreement {report.agree}/{report.n} = {report.rate:.0%}")
        for ipo_id, field_id, doc in report.disagreements:
            print(f"  differs: {ipo_id} {field_id} ({doc})")
        return 0
    issues = validate_file(args.path, args.complete)
    print("\n".join(issues[:40]) if issues else f"{args.path}: OK")
    if len(issues) > 40:
        print(f"... and {len(issues) - 40} more")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
