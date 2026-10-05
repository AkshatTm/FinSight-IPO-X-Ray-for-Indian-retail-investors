"""C1.2: the polite downloader against a local fake HTTP server (no real network)."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import fitz
import pytest

from finsight.ingest import fetch
from finsight.ingest.fetch import Fetcher, extract_pdf_urls, read_rows, run, write_rows
from finsight.splits import UNIVERSE_COLUMNS, load_universe


def make_pdf(pages: int) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"page {i}")
    data = doc.tobytes()
    doc.close()
    return bytes(data)


class Site:
    """Routes -> (status, body bytes) plus a request log."""

    def __init__(self) -> None:
        self.routes: dict[str, tuple[int, bytes]] = {}
        self.log: list[str] = []
        self.overstate: set[str] = set()  # paths whose Content-Length claims too many bytes
        self.base = ""


@pytest.fixture
def site() -> Iterator[Site]:
    s = Site()

    class H(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            s.log.append(self.path)
            status, body = s.routes.get(self.path, (404, b"missing"))
            self.send_response(status)
            extra = 500 if self.path in s.overstate else 0
            self.send_header("Content-Length", str(len(body) + extra))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), H)
    s.base = f"http://127.0.0.1:{server.server_address[1]}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield s
    server.shutdown()
    server.server_close()


def filing(*files: str) -> bytes:
    frames = "".join(f"<iframe src='../../web/?file={f}' width='1'></iframe>" for f in files)
    return f"<html>{frames}<a href='/commondocs/ap.pdf'>abridged</a></html>".encode()


def universe(tmp_path: Path, site: Site, ids: list[str]) -> Path:
    rows = []
    for i in ids:
        row = dict.fromkeys(UNIVERSE_COLUMNS, "")
        row.update(
            ipo_id=i, company=i.title(), exchange="both", doc_type="rhp", doc_date="2025-01-02",
            source_url=f"{site.base}/filing/{i}.html", status="listed",
        )  # fmt: skip
        rows.append(row)
    path = tmp_path / "ipo_universe.csv"
    write_rows(path, rows)
    return path


def fast_fetcher(delay: float = 0.0) -> Fetcher:
    return Fetcher(delay=delay, backoff=0.0, sleep=lambda s: None)


def quiet(msg: str) -> None:
    pass


def test_extract_pdf_urls() -> None:
    page = filing(
        "https://www.sebi.gov.in/sebi_data/attachdocs/a.pdf",
        "https://www.sebi.gov.in/sebi_data/attachdocs/b.pdf",
        "https://www.sebi.gov.in/sebi_data/attachdocs/a.pdf",
    ).decode()
    page += "<a href='https://x.test/sebi_data/commondocs/ap.pdf'>ap</a>"
    assert extract_pdf_urls(page, "https://www.sebi.gov.in/filings/x.html") == [
        "https://www.sebi.gov.in/sebi_data/attachdocs/a.pdf",
        "https://www.sebi.gov.in/sebi_data/attachdocs/b.pdf",
    ]


def test_download_fills_status_sha_pages(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/acme-2025.html"] = (200, filing(f"{site.base}/attachdocs/a.pdf"))
    site.routes["/attachdocs/a.pdf"] = (200, make_pdf(3))
    csv_path = universe(tmp_path, site, ["acme-2025"])
    out = tmp_path / "raw"
    report = run(csv_path, out, fast_fetcher(), log=quiet)
    assert report.downloaded == ["acme-2025"]
    row = load_universe(csv_path)[0]
    assert row.status == "downloaded"
    assert row.pages == 3
    assert row.sha256 == fetch.sha256_of(out / "acme-2025.pdf")
    assert not list(out.glob("*.part"))


def test_resume_does_not_refetch(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/a-2025.html"] = (200, filing(f"{site.base}/attachdocs/a.pdf"))
    site.routes["/attachdocs/a.pdf"] = (200, make_pdf(1))
    site.routes["/filing/b-2025.html"] = (200, filing(f"{site.base}/attachdocs/b.pdf"))
    site.routes["/attachdocs/b.pdf"] = (200, make_pdf(2))
    csv_path = universe(tmp_path, site, ["a-2025", "b-2025"])
    run(csv_path, tmp_path / "raw", fast_fetcher(), limit=1, log=quiet)
    first = len(site.log)
    report = run(csv_path, tmp_path / "raw", fast_fetcher(), log=quiet)
    assert report.downloaded == ["b-2025"]
    assert not {"/filing/a-2025.html", "/attachdocs/a.pdf"} & set(site.log[first:])  # a kept


def test_existing_file_is_adopted_not_downloaded(tmp_path: Path, site: Site) -> None:
    csv_path = universe(tmp_path, site, ["z-2025"])
    out = tmp_path / "raw"
    out.mkdir()
    (out / "z-2025.pdf").write_bytes(make_pdf(4))
    report = run(csv_path, out, fast_fetcher(), log=quiet)
    assert report.adopted == ["z-2025"]
    assert site.log == []
    assert load_universe(csv_path)[0].pages == 4


def test_4xx_is_tried_twice_then_goes_to_manual_list(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/gone-2025.html"] = (403, b"no")
    csv_path = universe(tmp_path, site, ["gone-2025"])
    report = run(csv_path, tmp_path / "raw", fast_fetcher(), log=quiet)
    assert site.log.count("/filing/gone-2025.html") == 2
    assert report.manual[0][0] == "gone-2025"
    row = load_universe(csv_path)[0]
    assert row.status == "failed"
    assert row.reason == "manual: HTTP 403"


def test_5xx_is_retried_three_times(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/sick-2025.html"] = (503, b"busy")
    csv_path = universe(tmp_path, site, ["sick-2025"])
    run(csv_path, tmp_path / "raw", fast_fetcher(), log=quiet)
    assert site.log.count("/filing/sick-2025.html") == 3


def test_html_instead_of_pdf_is_rejected(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/blk-2025.html"] = (200, filing(f"{site.base}/attachdocs/x.pdf"))
    site.routes["/attachdocs/x.pdf"] = (200, b"<html>Unauthorized Request Blocked</html>")
    csv_path = universe(tmp_path, site, ["blk-2025"])
    out = tmp_path / "raw"
    run(csv_path, out, fast_fetcher(), log=quiet)
    row = load_universe(csv_path)[0]
    assert row.status == "failed"
    assert "not a PDF" in (row.reason or "")
    assert not (out / "blk-2025.pdf").exists()


def test_no_pdf_link_goes_to_manual_list(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/nolink-2025.html"] = (200, b"<html>nothing</html>")
    csv_path = universe(tmp_path, site, ["nolink-2025"])
    report = run(csv_path, tmp_path / "raw", fast_fetcher(), log=quiet)
    assert report.manual[0][2] == "manual: no PDF link on the filing page"


def test_multi_part_is_merged_in_order(tmp_path: Path, site: Site) -> None:
    both = filing(f"{site.base}/attachdocs/p1.pdf", f"{site.base}/attachdocs/p2.pdf")
    site.routes["/filing/big-2025.html"] = (200, both)
    site.routes["/attachdocs/p1.pdf"] = (200, make_pdf(2))
    site.routes["/attachdocs/p2.pdf"] = (200, make_pdf(3))
    csv_path = universe(tmp_path, site, ["big-2025"])
    out = tmp_path / "raw"
    run(csv_path, out, fast_fetcher(), log=quiet)
    row = load_universe(csv_path)[0]
    assert row.pages == 5
    assert row.reason == "merged 2 parts"
    parts = json.loads((out / "big-2025.parts.json").read_text(encoding="utf-8"))
    assert len(parts["sha256"]) == 2
    assert not list(out.glob("*.part*.pdf"))


def test_rate_limit_is_respected() -> None:
    now = [0.0]
    naps: list[float] = []

    def sleep(s: float) -> None:
        naps.append(s)
        now[0] += s

    f = Fetcher(delay=4.0, sleep=sleep, clock=lambda: now[0])
    f._wait()
    f._wait()
    f._wait()
    assert naps == [4.0, 4.0]


def test_low_disk_stops_the_run(
    tmp_path: Path, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = universe(tmp_path, site, ["a-2025", "b-2025"])
    monkeypatch.setattr(fetch, "free_bytes", lambda p: 1024)
    report = run(csv_path, tmp_path / "raw", fast_fetcher(), log=quiet)
    assert "free disk" in report.stopped
    assert site.log == []
    assert {r.status for r in load_universe(csv_path)} == {"listed"}


def test_manual_rows_are_adopted_after_a_drop(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/m-2025.html"] = (404, b"")
    csv_path = universe(tmp_path, site, ["m-2025"])
    out = tmp_path / "raw"
    run(csv_path, out, fast_fetcher(), log=quiet)
    assert load_universe(csv_path)[0].status == "failed"
    (out / "m-2025.pdf").write_bytes(make_pdf(2))
    report = run(csv_path, out, fast_fetcher(), limit=0, log=quiet)
    assert report.adopted == ["m-2025"]
    assert load_universe(csv_path)[0].status == "downloaded"


def test_retry_flag_reopens_manual_rows(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/r-2025.html"] = (500, b"")
    csv_path = universe(tmp_path, site, ["r-2025"])
    run(csv_path, tmp_path / "raw", fast_fetcher(), log=quiet)
    site.routes["/filing/r-2025.html"] = (200, filing(f"{site.base}/attachdocs/r.pdf"))
    site.routes["/attachdocs/r.pdf"] = (200, make_pdf(1))
    run(csv_path, tmp_path / "raw", fast_fetcher(), retry=True, log=quiet)
    assert load_universe(csv_path)[0].status == "downloaded"


def test_showcase_pdf_is_copied_not_downloaded(tmp_path: Path, site: Site) -> None:
    local = tmp_path / "rhp" / "s.pdf"
    local.parent.mkdir()
    local.write_bytes(make_pdf(2))
    csv_path = universe(tmp_path, site, ["s-2025"])
    run(csv_path, tmp_path / "raw", fast_fetcher(), showcase_dirs={"s-2025": local}, log=quiet)
    assert site.log == []
    assert read_rows(csv_path)[0]["status"] == "downloaded"


def test_truncated_download_is_retried_and_never_kept(tmp_path: Path, site: Site) -> None:
    site.routes["/filing/cut-2025.html"] = (200, filing(f"{site.base}/attachdocs/c.pdf"))
    site.routes["/attachdocs/c.pdf"] = (200, make_pdf(2))
    site.overstate.add("/attachdocs/c.pdf")
    csv_path = universe(tmp_path, site, ["cut-2025"])
    out = tmp_path / "raw"
    run(csv_path, out, fast_fetcher(), log=quiet)
    assert site.log.count("/attachdocs/c.pdf") == 3
    row = load_universe(csv_path)[0]
    assert row.status == "failed"
    assert "network error" in (row.reason or "")
    assert not (out / "cut-2025.pdf").exists()
