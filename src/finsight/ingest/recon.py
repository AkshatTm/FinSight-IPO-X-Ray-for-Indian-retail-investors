"""Day-1 recon of the Ghosh et al. IPO dataset (05_DATA_AND_EVALUATION.md section 1.2).

Prints a *summary only*: counts, coverage and truncated examples. Claude Code reads that
summary, never the raw files. Columns that hold subscription outcomes, listing-day
targets or broker/member ratings are never summarised or sampled (ADR-005).

    uv run python -m finsight.ingest.recon                  # print the summary
    uv run python -m finsight.ingest.recon --write-samples  # also write data/samples/ rows
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import openpyxl

from finsight.core.config import get_settings
from finsight.ingest.registry import list_demo_ipos

SHEET = "data_ordered"
CoverKind = Literal["rhp", "drhp", "prospectus", "unknown"]

# The only columns we summarise or sample. Everything else is left alone on purpose.
ALLOWED_COLUMNS = [
    "mapping_key",
    "Issuer Company",
    "Company Name",
    "Exchange",
    "Close Year",
    "Listing Date",
    "Sector",
    "Industry",
    "Issue Type",
    "Total Issue Size",
    "Fresh Issue",
    "Offer for Sale",
    "Price Band",
    "Final_Issue_Price",
    "Issue Size (Rs Cr.)",
    "Lot Size",
    "Face Value per share",
    "most_relevant_link",
    "File_Rename_1st",
    "Text_extracted_JSON",
]

_FORBIDDEN = re.compile(
    r"^(Success_|NSE_|BSE_|Brokers_|Members_|day_\d+_|previous_quarter_success|"
    r"dynamic_last_90Day_success|Total_subscriptions$|elasticity$)"
)


def is_forbidden_column(name: str) -> bool:
    """Outcome / rating columns: subscription, listing-day results, broker and member views."""
    return bool(_FORBIDDEN.match(name))


def normalize_company(name: str) -> str:
    """``"Acme Ltd IPO"`` -> ``"acme"``: lowercase, drop 'IPO', 'Limited'/'Ltd', punctuation."""
    text = re.sub(r"\bipo\s*$", "", name.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"\b(limited|ltd)\b\.?\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^a-z0-9& ]+", " ", text.lower())
    return " ".join(text.split())


def flatten_text(obj: Any) -> str:
    """All strings inside nested lists/dicts (the per-page JSON layout), space-joined."""
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            parts.append(node.strip("\n") if node.strip() else "")
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list | tuple):
            for value in node:
                walk(value)

    walk(obj)
    return " ".join(p for p in parts if p).strip()


_TITLE = re.compile(r"\b(DRAFT\s+)?(RED\s+HERRING\s+)?PROSPECTUS\b")


def classify_cover(text: str) -> CoverKind:
    """DRHP, RHP or final Prospectus, judged by the *first* title phrase on the cover.

    Later mentions do not count: an RHP cover says "(This Draft Red Herring Prospectus...)"
    further down and a final Prospectus refers to "the Red Herring Prospectus dated ...".
    """
    match = _TITLE.search(" ".join(text[:1500].upper().split()))
    if not match:
        return "unknown"
    if match.group(1):
        return "drhp"
    return "rhp" if match.group(2) else "prospectus"


# ------------------------------------------------------------------------- Excel
@dataclass
class ExcelSummary:
    n_rows: int
    n_cols: int
    years: dict[str, int]
    coverage: dict[str, float]  # share of rows with a value, allowed columns only
    hidden_columns: int  # forbidden columns present but not summarised
    examples: dict[str, list[str]] = field(default_factory=dict)


def _rows(path: Path) -> tuple[list[str], list[tuple[Any, ...]]]:
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb[SHEET]
    it = ws.iter_rows(values_only=True)
    header = [str(h) for h in next(it)]
    rows = list(it)
    wb.close()
    return header, rows


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def summarize_excel(path: Path) -> ExcelSummary:
    header, rows = _rows(path)
    index = {name: i for i, name in enumerate(header)}
    years = Counter(str(r[index["Close Year"]]) for r in rows if "Close Year" in index)
    coverage: dict[str, float] = {}
    examples: dict[str, list[str]] = {}
    for name in ALLOWED_COLUMNS:
        if name not in index:
            continue
        values = [r[index[name]] for r in rows]
        coverage[name] = sum(not _blank(v) for v in values) / max(len(values), 1)
        examples[name] = [str(v)[:50].replace("\n", " ") for v in values if not _blank(v)][:2]
    return ExcelSummary(
        n_rows=len(rows),
        n_cols=len(header),
        years=dict(sorted(years.items())),
        coverage=coverage,
        hidden_columns=sum(is_forbidden_column(h) for h in header),
        examples=examples,
    )


def sample_rows(path: Path, n: int = 5, max_chars: int = 200) -> list[dict[str, Any]]:
    """First ``n`` rows, allowed columns only, every value truncated (committed as samples)."""
    header, rows = _rows(path)
    index = {name: i for i, name in enumerate(header)}
    keep = [c for c in ALLOWED_COLUMNS if c in index]
    return [
        {c: (None if _blank(r[index[c]]) else str(r[index[c]])[:max_chars]) for c in keep}
        for r in rows[:n]
    ]


def demo_overlap(path: Path, demo_companies: list[str]) -> list[str]:
    """Demo companies that also appear in the dataset (by normalised name)."""
    header, rows = _rows(path)
    columns = [header.index(c) for c in ("Issuer Company", "Company Name") if c in header]
    known = {normalize_company(str(r[i])) for r in rows for i in columns if not _blank(r[i])}
    return [c for c in demo_companies if normalize_company(c) in known]


# ------------------------------------------------------------------------- text zip
@dataclass
class ZipSummary:
    n_entries: int
    by_name_pattern: dict[str, int]
    by_cover: dict[str, int]
    by_name_and_cover: dict[str, int]  # "N_RHP.json -> prospectus": file names are not reliable
    size_mb_p50: float
    size_mb_max: float
    pages_p50: int


def _pattern(name: str) -> str:
    return re.sub(r"\d+", "N", name.rsplit("/", 1)[-1])[:24]


def summarize_zip(path: Path) -> ZipSummary:
    by_name: Counter[str] = Counter()
    by_cover: Counter[str] = Counter()
    by_both: Counter[str] = Counter()
    sizes: list[int] = []
    pages: list[int] = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if not info.filename.endswith(".json"):
                continue
            by_name[_pattern(info.filename)] += 1
            sizes.append(info.file_size)
            obj = json.loads(z.read(info))
            pages.append(len(obj) if isinstance(obj, dict) else 0)
            first = obj.get("Page_0") if isinstance(obj, dict) else None
            cover = classify_cover(flatten_text(first))
            by_cover[cover] += 1
            by_both[f"{_pattern(info.filename)} -> {cover}"] += 1
    sizes.sort()
    pages.sort()
    mid = len(sizes) // 2
    return ZipSummary(
        n_entries=len(sizes),
        by_name_pattern=dict(by_name.most_common()),
        by_cover=dict(by_cover),
        by_name_and_cover=dict(by_both.most_common()),
        size_mb_p50=round(sizes[mid] / 1e6, 2) if sizes else 0.0,
        size_mb_max=round(sizes[-1] / 1e6, 2) if sizes else 0.0,
        pages_p50=pages[mid] if pages else 0,
    )


# ------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    parser.add_argument("--write-samples", action="store_true", help="write 5 truncated rows")
    args = parser.parse_args(argv)

    settings = get_settings()
    base = settings.paths.raw_dir / "ipo_dataset"
    xlsx = base / "ipo_mainline_final_data_v18.xlsx"
    zpath = base / "texts_extracted_from_pdfs" / "ipo_mainline_txts_extracted.zip"

    ex = summarize_excel(xlsx)
    print(
        f"EXCEL  sheet={SHEET!r} rows={ex.n_rows} cols={ex.n_cols} "
        f"(outcome/rating columns present but never summarised: {ex.hidden_columns})"
    )
    print("Close Year counts:", ex.years)
    print("Coverage of allowed columns (share of rows with a value):")
    for name, cov in ex.coverage.items():
        print(f"  {name:22} {cov:5.0%}  e.g. {ex.examples[name]}")

    zs = summarize_zip(zpath)
    print(
        f"\nTEXT ZIP entries={zs.n_entries} size MB p50/max={zs.size_mb_p50}/{zs.size_mb_max} "
        f"pages p50={zs.pages_p50}"
    )
    print("By file-name pattern:", zs.by_name_pattern)
    print("By cover-page class :", zs.by_cover)
    print("File name -> cover  :", {k: v for k, v in zs.by_name_and_cover.items() if v >= 5})

    demo = [i.company for i in list_demo_ipos()]
    overlap = demo_overlap(xlsx, demo)
    print(f"\nDEMO OVERLAP with dataset (by name): {overlap or 'none'} of {len(demo)} demo IPOs")

    if args.write_samples:
        out = settings.paths.samples_dir / "ipo_dataset_rows.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = sample_rows(xlsx)
        out.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {len(rows)} truncated rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
