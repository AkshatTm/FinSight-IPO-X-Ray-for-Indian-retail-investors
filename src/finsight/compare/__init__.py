"""Compare: the issuer against the listed peers its document names, and against past IPOs.

- **Peers** come from the peer table in "Basis for Offer Price" (``peers_from_table``): name,
  P/E, basic EPS, RoNW and NAV per share, with the page and box of each row. The issuer's own row
  is flagged; its P/E is often a blank ``[●]`` in an RHP, so ``issuer_pe`` can compute it from the
  offer price and EPS.
- **Percentiles** place four numbers among past Indian IPOs (2018-2023): issue size, OFS share,
  insider price gap and P/E, using the reference quantiles in ``configs/compare.yaml``.

Only facts from the document and the reference set are shown: no judgement, no advice (B-ADR-13).
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from finsight.core.config import project_root
from finsight.core.schemas import (
    BBox,
    Compare,
    CompareMetric,
    ComparePercentile,
    PageEvidence,
    Peer,
    Table,
    TableCell,
)
from finsight.risklevel import percentile
from finsight.storage import Storage, doc_key, put_json

METRICS: tuple[CompareMetric, ...] = ("issue_size_inr", "ofs_share", "insider_price_gap", "pe")

# Header words for each column (lower case; the first column whose header matches wins).
COLUMNS: dict[str, tuple[str, ...]] = {
    "name": (
        "name of the company",
        "name of company",
        "company name",
        "name of the issuer",
        "name",
    ),
    "pe": ("p/e", "p / e", "price earning", "price to earning", "pe ratio"),
    "eps": ("eps", "earnings per share", "earning per share"),
    "ronw": ("ronw", "return on net worth", "return on networth"),
    "nav": ("nav", "net asset value", "book value"),
}
_BLANK = re.compile(r"^(?:n\.?\s?a\.?|not applicable|not available|nil|-+|–|—|\[[●•]\]|)$", re.I)
_NUMBER = re.compile(r"\(?-?[\d,]*\.?\d+\)?")
_ISSUER_WORDS = ("our company", "the company", "the issuer")


def load_config(path: Path | None = None) -> dict[str, Any]:
    """The compare settings and reference quantiles (``configs/compare.yaml``)."""
    path = path or project_root() / "configs" / "compare.yaml"
    return dict(yaml.safe_load(path.read_text(encoding="utf-8")))


def cell_number(text: str) -> Decimal | None:
    """A table cell as a number: ``"1,234.5"`` → 1234.5, ``"(3.2)"`` → -3.2; blanks → ``None``.

    Footnote marks and units around the number (``"45.6x"``, ``"12.3%"``, ``"₹ 10"``) are ignored.
    """
    text = text.strip().replace("−", "-")
    if _BLANK.match(text):
        return None
    m = _NUMBER.search(text.replace(" ", ""))
    if not m:
        return None
    raw = m.group(0)
    negative = (raw.startswith("(") and raw.endswith(")")) or raw.lstrip("(").startswith("-")
    digits = raw.strip("()").lstrip("-").replace(",", "")
    try:
        value = Decimal(digits)
    except InvalidOperation:
        return None
    return -value if negative else value


def _rows(table: Table) -> list[list[TableCell]]:
    by_row: dict[int, list[TableCell]] = {}
    for cell in table.cells:
        by_row.setdefault(cell.row, []).append(cell)
    return [sorted(by_row[r], key=lambda c: c.col) for r in sorted(by_row)]


def _header_map(header: Sequence[TableCell]) -> dict[str, int]:
    """Column index per key. EPS prefers the "basic" column over "diluted"."""
    texts = [(c.col, " ".join(c.text.lower().split())) for c in header]
    found: dict[str, int] = {}
    for key, words in COLUMNS.items():
        hits = [col for col, text in texts if any(w in text for w in words)]
        hits = [col for col in hits if col not in found.values()]
        if key == "eps":
            ranked = sorted(hits, key=lambda col: _eps_rank(dict(texts)[col]))
            hits = ranked
        if hits:
            found[key] = hits[0]
    return found


def _eps_rank(text: str) -> int:
    return 0 if "basic" in text else (2 if "diluted" in text else 1)


def _union(cells: Sequence[TableCell]) -> BBox:
    return (
        min(c.bbox[0] for c in cells),
        min(c.bbox[1] for c in cells),
        max(c.bbox[2] for c in cells),
        max(c.bbox[3] for c in cells),
    )


def peers_from_table(table: Table, doc_id: str, issuer: str | None = None) -> list[Peer]:
    """Peers from a Basis for Offer Price peer table; ``[]`` if it has no name and P/E columns.

    The issuer row is the one whose name matches ``issuer`` (or says "our company"), else the first
    data row, which is where SEBI's format puts it. Rows with a name but no number ("Listed
    peers") are headings and are skipped.
    """
    rows = _rows(table)
    found = [(i, _header_map(r)) for i, r in enumerate(rows)]
    header = next(((i, c) for i, c in found if "name" in c and "pe" in c), None)
    if header is None:
        return []
    h, cols = header
    peers: list[Peer] = []
    issuer_key = _key(issuer) if issuer else ""
    for row in rows[h + 1 :]:
        by_col = {c.col: c for c in row}
        name_cell = by_col.get(cols["name"])
        if name_cell is None or not name_cell.text.strip():
            continue
        values = {k: cell_number(by_col[c].text) if c in by_col else None for k, c in cols.items()}
        if all(values[k] is None for k in ("pe", "eps", "ronw", "nav")) and not _is_issuer_name(
            name_cell.text, issuer_key
        ):
            continue  # a heading row such as "Listed peers"
        name = " ".join(name_cell.text.split())
        peers.append(
            Peer(
                name=re.sub(r"[\*#\^]+$|\(\d\)$", "", name).strip(),
                pe=values.get("pe"),
                eps=values.get("eps"),
                ronw=values.get("ronw"),
                nav=values.get("nav"),
                evidence=PageEvidence(
                    doc_id=doc_id, page=name_cell.page, bbox=_union(row), sentence=name
                ),
            )
        )
    if peers:
        match = [p for p in peers if _is_issuer_name(p.name, issuer_key)]
        (match[0] if match else peers[0]).is_issuer = True
    return peers


def _key(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in {"limited", "ltd", "private", "pvt"})


def _is_issuer_name(name: str, issuer_key: str) -> bool:
    low = name.lower()
    if any(w in low for w in _ISSUER_WORDS):
        return True
    return bool(issuer_key) and _key(name).startswith(issuer_key)


def issuer_pe(offer_price: Decimal | None, eps: Decimal | None) -> Decimal | None:
    """P/E at the offer price; ``None`` for a loss (no meaningful P/E) or a missing number."""
    if offer_price is None or eps is None or eps <= 0:
        return None
    return (offer_price / eps).quantize(Decimal("0.01"))


def peer_median_pe(peers: Sequence[Peer]) -> Decimal | None:
    """Median P/E of the listed peers (issuer excluded, losses and blanks left out)."""
    values = [p.pe for p in peers if not p.is_issuer and p.pe is not None and p.pe > 0]
    return Decimal(str(statistics.median(values))) if values else None


def percentiles(
    metrics: Mapping[str, float | Decimal | None], cfg: dict[str, Any]
) -> list[ComparePercentile]:
    """Where each available metric falls among past IPOs (missing metrics are left out)."""
    out = []
    for metric in METRICS:
        value = metrics.get(metric)
        quantiles = cfg["reference_quantiles"].get(metric)
        if value is None or not quantiles:
            continue
        v = float(value)
        out.append(
            ComparePercentile(
                metric=metric,
                value=v,
                percentile=percentile(v, quantiles),
                corpus_n=int(cfg["corpus_n"]),
            )
        )
    return out


def compare(
    peers: Sequence[Peer],
    metrics: Mapping[str, float | Decimal | None],
    cfg: dict[str, Any] | None = None,
    offer_price: Decimal | None = None,
) -> Compare:
    """The compare result. The issuer's P/E falls back to offer price ÷ EPS when the table
    leaves it blank, and feeds the ``pe`` percentile when ``metrics`` has none."""
    cfg = cfg or load_config()
    rows = [p.model_copy() for p in peers]
    for p in rows:
        if p.is_issuer and p.pe is None:
            p.pe = issuer_pe(offer_price, p.eps)
    issuer = next((p for p in rows if p.is_issuer), None)
    values = dict(metrics)
    if values.get("pe") is None and issuer is not None and issuer.pe is not None:
        values["pe"] = issuer.pe
    return Compare(
        peers=rows,
        peer_median_pe=peer_median_pe(rows),
        percentiles=percentiles(values, cfg),
        provisional=bool(cfg.get("provisional", True)),
    )


def build(
    storage: Storage,
    doc_id: str,
    peers: Sequence[Peer],
    metrics: Mapping[str, float | Decimal | None],
    offer_price: Decimal | None = None,
    cfg: dict[str, Any] | None = None,
) -> Compare:
    """The ``compare`` stage: write ``docs/<doc_id>/compare.json``."""
    result = compare(peers, metrics, cfg, offer_price)
    put_json(storage, doc_key(doc_id, "compare.json"), result.model_dump(mode="json"))
    return result


__all__ = [
    "COLUMNS",
    "METRICS",
    "build",
    "cell_number",
    "compare",
    "issuer_pe",
    "load_config",
    "peer_median_pe",
    "peers_from_table",
    "percentiles",
]
