"""The mainboard IPO universe from SEBI's public filings pages (C1.1, C02 §2–3).

SEBI lists every mainboard public issue's Red Herring Document (``smid=11``) and Final Offer
Document / Prospectus (``smid=12``) under *Filings → Public Issues*. SME issues are filed with the
exchanges, not SEBI, so they never appear (C-ADR-09). This module parses those listing pages,
drops addenda / corrigenda, picks one offer document per company (the RHP; the Prospectus when
there is no RHP), maps the showcase IPOs to their existing ids and returns rows for
``configs/ipo_universe.csv`` (``finsight.splits.UNIVERSE_COLUMNS``).

Honest limits: SEBI gives the *filing date* and the filing page, not the exchange or the listing
date. ``doc_date`` is therefore the SEBI posting date (a day or two after the cover date) until
C1.3 reads the cover; ``exchange`` is ``both`` unless known; ``listing_date`` stays empty.
"""

from __future__ import annotations

import difflib
import html
import http.cookiejar
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Protocol

from finsight.ingest.corpus import ipo_slug
from finsight.risks import company_key

SEBI_BASE = "https://www.sebi.gov.in"
SMID_RHP = 11  # "Red Herring Documents filed with ROC"
SMID_FINAL = 12  # "Final Offer Documents filed with ROC"
USER_AGENT = "FinSight-research/0.1 (student project; akshattmofficial@gmail.com)"
AMENDMENT = re.compile(
    r"addendum|corrigendum|errata|erratum|price band|notice|advertis|revised|extension|"
    r"abridged|supplement|clarification",
    re.I,
)
_DATE = re.compile(r"<td>([A-Z][a-z]{2} \d{1,2}, \d{4})</td>")
_HREF = re.compile(r"<td><a href=['\"]([^'\"]+)['\"]")
_TITLE = re.compile(r"class=['\"]points['\"]>(.*?)(?:<br>|</a>)", re.S)
_TOTAL = re.compile(r"of (\d+) records")
_SUFFIX = re.compile(
    r"\s*[-–—:]*\s*\(?\b(?:RHP|red herring (?:prospectus|document)|final offer document|"
    r"prospectus)\b\)?\s*$",
    re.I,
)


_PREFIX = re.compile(
    r"^(?:final offer document|red herring (?:prospectus|document)|prospectus|rhp)"
    r"\s*(?:of|[-:–—])\s*",
    re.I,
)


def listing_url(smid: int) -> str:
    """The listing page for one sub-section (also the Referer of its AJAX calls)."""
    return f"{SEBI_BASE}/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid={smid}"


@dataclass(frozen=True)
class Entry:
    """One row of a SEBI listing page."""

    posted: date
    title: str
    url: str  # the filing page, which links the PDF(s)
    smid: int


def parse_listing(page: str, smid: int) -> list[Entry]:
    """Rows (date, title, filing page) of one listing page or AJAX fragment."""
    out = []
    for chunk in re.split(r"<tr[ >]", page)[1:]:
        d, h, t = _DATE.search(chunk), _HREF.search(chunk), _TITLE.search(chunk)
        if not (d and h and t):
            continue  # header row, or a row without a filing link
        title = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t.group(1))).split())
        posted = datetime.strptime(d.group(1), "%b %d, %Y").date()
        out.append(Entry(posted, title, h.group(1), smid))
    return out


def parse_total(page: str) -> int:
    """Total number of records the listing reports (0 when absent)."""
    m = _TOTAL.search(page)
    return int(m.group(1)) if m else 0


def _decode(raw: bytes) -> str:
    """UTF-8 when valid, else Windows-1252 (SEBI titles carry cp1252 en dashes)."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


class Transport(Protocol):
    """What the crawler needs from HTTP (a fake in tests)."""

    def get(self, url: str) -> str: ...

    def post(self, url: str, data: dict[str, str], referer: str) -> str: ...


class UrllibTransport:
    """Polite stdlib HTTP with cookies: honest User-Agent, one request per ``delay`` seconds."""

    def __init__(self, delay: float = 3.0, timeout: float = 40.0) -> None:
        self.delay, self.timeout, self._last = delay, timeout, 0.0
        jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def _wait(self) -> None:
        gap = self.delay - (time.monotonic() - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()

    def _open(self, req: urllib.request.Request) -> str:
        last: Exception | None = None
        for attempt in range(3):  # retry with backoff on network errors / 5xx only
            self._wait()
            try:
                with self._opener.open(req, timeout=self.timeout) as resp:
                    return _decode(resp.read())
            except urllib.error.HTTPError as err:
                if err.code < 500:
                    raise
                last = err
            except OSError as err:
                last = err
            time.sleep(5 * 2**attempt)
        raise RuntimeError(f"request failed after retries: {last}")

    def get(self, url: str) -> str:
        return self._open(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}))

    def post(self, url: str, data: dict[str, str], referer: str) -> str:
        # The same headers the site's own page script sends with this AJAX call.
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": referer,
            "Origin": SEBI_BASE,
            "X-Requested-With": "XMLHttpRequest",
        }
        body = urllib.parse.urlencode(data).encode()
        return self._open(urllib.request.Request(url, data=body, headers=headers))


def _form(smid: int, page_index: int) -> dict[str, str]:
    return {
        "nextValue": str(max(page_index, 1)), "next": "n", "search": "", "fromDate": "",
        "toDate": "", "fromYear": "", "toYear": "", "deptId": "-1", "sid": "3", "ssid": "15",
        "smid": str(smid), "ssidhidden": "15", "intmid": "-1", "sText": "Filings",
        "ssText": "Public Issues", "smText": "", "doDirect": str(page_index),
    }  # fmt: skip


def crawl(
    transport: Transport,
    smid: int,
    since: date,
    max_pages: int = 60,
    log: Callable[[str], None] | None = None,
) -> list[Entry]:
    """All entries of a sub-section posted on or after ``since`` (newest first, stops early)."""
    first = transport.get(listing_url(smid))
    entries = parse_listing(first, smid)
    total = parse_total(first)
    pages = min(max_pages, -(-total // 25)) if total else 1
    page_index = 0
    while entries and entries[-1].posted >= since and page_index + 1 < pages:
        page_index += 1
        fragment = transport.post(
            f"{SEBI_BASE}/sebiweb/ajax/home/getnewslistinfo.jsp",
            _form(smid, page_index),
            listing_url(smid),
        )
        new = parse_listing(fragment, smid)
        if not new:
            break
        entries.extend(new)
        if log:
            log(f"smid {smid}: page {page_index + 1}/{pages}, {len(entries)} rows")
    return [e for e in entries if e.posted >= since]


def company_name(title: str) -> str:
    """``"Rentomojo Limited - RHP"`` -> ``"Rentomojo Limited"``."""
    name = _PREFIX.sub("", title.strip())
    name = _SUFFIX.sub("", name).strip(" -–—:")
    name = re.sub(r"[\s-]*\bIPO$", "", name, flags=re.I)
    return _SUFFIX.sub("", name).strip(" -–—:")


def name_key(name: str) -> str:
    """``company_key`` reading ``&`` as ``and`` (so "A & B" matches "A and B")."""
    return company_key(name.replace("&", " and "))


def _merge_keys(groups: dict[str, list[Entry]], threshold: float = 0.92) -> dict[str, list[Entry]]:
    """Merge near-identical names when at most one side has an RHP ("A One Steel" / "A ONE Steels").

    Two groups that both have an RHP stay apart: they are two separate filings.
    """
    merged: dict[str, list[Entry]] = {}
    for key, group in sorted(groups.items(), key=lambda kv: min(e.posted for e in kv[1])):
        has_rhp = any(e.smid == SMID_RHP for e in group)
        for other, og in merged.items():
            if difflib.SequenceMatcher(None, key, other).ratio() < threshold:
                continue
            if has_rhp and any(e.smid == SMID_RHP for e in og):
                continue
            og.extend(group)
            break
        else:
            merged[key] = list(group)
    return merged


@dataclass(frozen=True)
class UniverseCandidate:
    """One company's chosen offer document before it becomes a CSV row."""

    ipo_id: str
    company: str
    doc_type: Literal["rhp", "prospectus"]
    doc_date: date
    source_url: str


def is_offer_document(entry: Entry) -> bool:
    """True for the offer document itself, False for addenda, corrigenda and notices."""
    return not AMENDMENT.search(entry.title)


def build_candidates(
    entries: list[Entry],
    since: date,
    showcase: dict[str, str] | None = None,
) -> list[UniverseCandidate]:
    """One document per company: the earliest RHP, else the earliest Prospectus.

    Args:
        entries: Rows from both sub-sections.
        since: First day in scope. A company whose *first* filing is earlier is out (its IPO
            belongs to the previous period even if the Prospectus lands after ``since``).
        showcase: ``company_key -> existing ipo_id`` so showcase IPOs keep their ids.
    """
    showcase = showcase or {}
    by_company: dict[str, list[Entry]] = {}
    for e in entries:
        if is_offer_document(e):
            by_company.setdefault(name_key(company_name(e.title)), []).append(e)
    by_company = _merge_keys(by_company)
    out: list[UniverseCandidate] = []
    used: set[str] = set()
    for key, group in sorted(by_company.items(), key=lambda kv: min(e.posted for e in kv[1])):
        if min(e.posted for e in group) < since:
            continue
        rhps = [e for e in group if e.smid == SMID_RHP]
        pick = min(rhps or group, key=lambda e: e.posted)
        kind: Literal["rhp", "prospectus"] = "rhp" if rhps else "prospectus"
        name = company_name(pick.title)
        ipo_id = showcase.get(key) or ipo_slug(name, pick.posted.year)
        n = 2
        while ipo_id in used:  # two filings under one name in one year: name-2-YYYY
            ipo_id = ipo_slug(f"{name} {n}", pick.posted.year)
            n += 1
        used.add(ipo_id)
        out.append(UniverseCandidate(ipo_id, name, kind, pick.posted, pick.url))
    return out
