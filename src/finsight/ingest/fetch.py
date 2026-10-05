"""Polite offer-document downloader (C1.2, C02 §3).

For every ``listed`` row of ``configs/ipo_universe.csv`` it opens the filing page on sebi.gov.in,
finds the PDF link(s), downloads them to ``data/raw/offer_docs/<ipo_id>.pdf`` and records the
sha256. One request every few seconds, an honest User-Agent, resume (finished files are kept),
a retry cap (a 4xx is tried at most twice, a 5xx or network error three times with backoff) and a
stop when free disk is below 15 GB. Multi-part filings are merged in page order; the part hashes
go to a ``<ipo_id>.parts.json`` sidecar. A row that cannot be fetched becomes ``failed`` with a
reason starting ``manual:`` and goes on the manual-download list; once Akshat drops the PDF into
the same folder, ``--adopt`` turns it into ``downloaded``. Nothing here is committed except the
CSV metadata (PDFs live in gitignored ``data/``).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from finsight.splits import UNIVERSE_COLUMNS

USER_AGENT = "FinSight-research/0.1 (student project; akshattmofficial@gmail.com)"
MIN_FREE_BYTES = 15 * 1024**3
MAX_4XX_TRIES = 2
MAX_OTHER_TRIES = 3
_IFRAME_FILE = re.compile(r"""<iframe[^>]+src=['"][^'"]*[?&]file=([^'"&]+\.pdf)""", re.I)
_PDF_HREF = re.compile(r"""href=['"]([^'"]+/attachdocs/[^'"]+\.pdf)['"]""", re.I)


class DiskLowError(RuntimeError):
    """Free disk space fell below the limit; the run stops (C06: 15 GB)."""


class FetchError(RuntimeError):
    """One document could not be fetched; the message becomes the row's reason."""


def extract_pdf_urls(page: str, base: str) -> list[str]:
    """PDF links of a filing page in page order, without the abridged prospectus (commondocs).

    Args:
        page: Filing page HTML.
        base: The page URL, used to resolve relative links.
    """
    found: list[str] = []
    for m in [*_IFRAME_FILE.finditer(page), *_PDF_HREF.finditer(page)]:
        url = urllib.parse.urljoin(base, urllib.parse.unquote(m.group(1)).replace(" ", "%20"))
        if "/commondocs/" in url or url in found:
            continue
        found.append(url)
    return found


def free_bytes(path: Path) -> int:
    """Free bytes on the disk holding ``path`` (or its nearest existing parent)."""
    p = path
    while not p.exists():
        p = p.parent
    return shutil.disk_usage(p).free


def sha256_of(path: Path) -> str:
    """Hex sha256 of a file, read in 1 MB chunks."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_pages(path: Path) -> int:
    """Page count of a PDF; raises ``FetchError`` when the file does not open as one."""
    import pymupdf  # PyMuPDF, imported lazily

    try:
        with pymupdf.open(path) as doc:
            pages = int(doc.page_count)
        if pages < 1:
            raise FetchError("PDF has no pages (truncated download?)")
        return pages
    except FetchError:
        raise
    except Exception as err:
        raise FetchError(f"not a readable PDF ({err.__class__.__name__})") from err


@dataclass
class Fetcher:
    """HTTP with a minimum gap between requests, retries and backoff."""

    delay: float = 4.0
    timeout: float = 60.0
    backoff: float = 5.0
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    requests: int = 0
    _last: float = field(default=-1e9, repr=False)

    def _wait(self) -> None:
        gap = self.delay - (self.clock() - self._last)
        if gap > 0:
            self.sleep(gap)
        self._last = self.clock()
        self.requests += 1

    def _open(self, url: str, sink: Callable[[urllib.request.addinfourl], None]) -> None:
        tries4 = tries_other = 0
        while True:
            self._wait()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    sink(resp)
                    return
            except urllib.error.HTTPError as err:
                if 400 <= err.code < 500 and err.code != 429:
                    tries4 += 1
                    if tries4 >= MAX_4XX_TRIES:
                        raise FetchError(f"HTTP {err.code}") from err
                    continue
                tries_other += 1
                if tries_other >= MAX_OTHER_TRIES:
                    raise FetchError(f"HTTP {err.code}") from err
                wait = float(err.headers.get("Retry-After", "") or self.backoff * 2**tries_other)
                self.sleep(min(wait, 120.0))
            except OSError as err:  # connection reset, timeout, DNS
                tries_other += 1
                if tries_other >= MAX_OTHER_TRIES:
                    raise FetchError(f"network error: {err.__class__.__name__}") from err
                self.sleep(self.backoff * 2**tries_other)

    def get_text(self, url: str) -> str:
        """Fetch a page as text (UTF-8, falling back to Windows-1252)."""
        box: list[bytes] = []
        self._open(url, lambda r: box.append(r.read()))
        try:
            return box[0].decode("utf-8")
        except UnicodeDecodeError:
            return box[0].decode("cp1252", errors="replace")

    def download(self, url: str, dest: Path) -> None:
        """Stream ``url`` to ``dest`` via a ``.part`` file; only a real PDF is kept."""
        part = dest.with_suffix(dest.suffix + ".part")
        part.parent.mkdir(parents=True, exist_ok=True)

        def sink(resp: urllib.request.addinfourl) -> None:
            with part.open("wb") as fh:
                shutil.copyfileobj(resp, fh, 1 << 20)
            expected = resp.headers.get("Content-Length")
            if expected and expected.isdigit() and part.stat().st_size != int(expected):
                raise ConnectionError("short read: connection closed early")  # retried

        try:
            self._open(url, sink)
            with part.open("rb") as fh:
                if fh.read(5) != b"%PDF-":
                    raise FetchError("response is not a PDF (blocked or error page)")
            part.replace(dest)
        finally:
            part.unlink(missing_ok=True)


def merge_pdfs(parts: list[Path], dest: Path) -> None:
    """Concatenate PDFs in order into ``dest``."""
    import pymupdf

    out = pymupdf.open()
    try:
        for p in parts:
            with pymupdf.open(p) as src:
                out.insert_pdf(src)
        out.save(dest)
    finally:
        out.close()


def read_rows(path: Path) -> list[dict[str, str]]:
    """The universe CSV as plain dict rows (no validation: ``load_universe`` does that)."""
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    """Atomically rewrite the universe CSV with the contract columns."""
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=UNIVERSE_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def fetch_row(row: dict[str, str], out_dir: Path, fetcher: Fetcher) -> None:
    """Download one document into ``out_dir`` and fill ``sha256``/``pages``/``status`` in ``row``.

    Raises:
        FetchError: when the document cannot be fetched (reason in the message).
        DiskLowError: when free disk is below 15 GB.
    """
    if free_bytes(out_dir) < MIN_FREE_BYTES:
        raise DiskLowError(f"free disk below {MIN_FREE_BYTES // 1024**3} GB")
    dest = out_dir / f"{row['ipo_id']}.pdf"
    page = fetcher.get_text(row["source_url"])
    urls = extract_pdf_urls(page, row["source_url"])
    if not urls:
        raise FetchError("no PDF link on the filing page")
    if len(urls) == 1:
        fetcher.download(urls[0], dest)
        note = ""
    else:
        parts = []
        for i, u in enumerate(urls, 1):
            p = out_dir / f"{row['ipo_id']}.part{i}.pdf"
            fetcher.download(u, p)
            parts.append(p)
        shas = [sha256_of(p) for p in parts]
        merge_pdfs(parts, dest)
        (out_dir / f"{row['ipo_id']}.parts.json").write_text(
            json.dumps({"urls": urls, "sha256": shas}, indent=1), encoding="utf-8"
        )
        for p in parts:
            p.unlink()
        note = f"merged {len(parts)} parts"
    row["pages"] = str(pdf_pages(dest))
    row["sha256"] = sha256_of(dest)
    row["status"] = "downloaded"
    row["reason"] = note


def adopt_existing(row: dict[str, str], out_dir: Path) -> bool:
    """Accept a PDF already in ``out_dir`` (manual or earlier run); True if adopted."""
    dest = out_dir / f"{row['ipo_id']}.pdf"
    if not dest.exists():
        return False
    try:
        row["pages"] = str(pdf_pages(dest))
    except FetchError:
        return False
    row["sha256"] = sha256_of(dest)
    row["status"] = "downloaded"
    row["reason"] = ""
    return True


@dataclass
class RunReport:
    """What one run did."""

    downloaded: list[str] = field(default_factory=list)
    adopted: list[str] = field(default_factory=list)
    manual: list[tuple[str, str, str]] = field(default_factory=list)  # (ipo_id, url, why)
    stopped: str = ""


def run(
    csv_path: Path,
    out_dir: Path,
    fetcher: Fetcher,
    only: set[str] | None = None,
    limit: int | None = None,
    showcase_dirs: dict[str, Path] | None = None,
    retry: bool = False,
    log: Callable[[str], None] = print,
) -> RunReport:
    """Fetch every pending row; the CSV is saved after each row so a crash loses nothing.

    Args:
        csv_path: ``configs/ipo_universe.csv``.
        out_dir: ``data/raw/offer_docs``.
        fetcher: The rate-limited HTTP client.
        only: Restrict to these ``ipo_id`` values.
        limit: Stop after this many network fetches.
        showcase_dirs: ``ipo_id -> existing local RHP path``; copied instead of downloaded.
        retry: Try the ``manual:`` rows again over the network.
        log: Progress sink.
    """
    rows = read_rows(csv_path)
    report = RunReport()
    out_dir.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for row in rows:
        ipo = row["ipo_id"]
        if only and ipo not in only:
            continue
        retry_manual = row["status"] == "failed" and row["reason"].startswith("manual:")
        if retry_manual and retry:
            row["status"], row["reason"], retry_manual = "listed", "", False
        if row["status"] != "listed" and not retry_manual:
            continue
        local = (showcase_dirs or {}).get(ipo)
        if local and local.exists() and not (out_dir / f"{ipo}.pdf").exists():
            shutil.copy2(local, out_dir / f"{ipo}.pdf")
        if adopt_existing(row, out_dir):
            report.adopted.append(ipo)
            write_rows(csv_path, rows)
            continue
        if retry_manual:
            report.manual.append((ipo, row["source_url"], row["reason"]))
            continue
        if limit is not None and fetched >= limit:
            report.stopped = f"limit {limit} reached"
            break
        fetched += 1
        try:
            fetch_row(row, out_dir, fetcher)
            report.downloaded.append(ipo)
            log(f"downloaded {ipo} ({row['pages']} pages)")
        except DiskLowError as err:
            report.stopped = str(err)
            log(f"STOP: {err}")
            break
        except FetchError as err:
            row["status"], row["reason"] = "failed", f"manual: {err}"
            report.manual.append((ipo, row["source_url"], row["reason"]))
            log(f"manual {ipo}: {err}")
        write_rows(csv_path, rows)
    write_rows(csv_path, rows)
    return report
