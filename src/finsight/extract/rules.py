"""Rung 1 of the ladder: regular-expression rules over SEBI's standard cover-page wording.

An RHP or Prospectus cover is boilerplate ("... a Fresh Issue of [●] Equity Shares aggregating
up to ₹ 4,720 million ..."), so a few patterns find most fields. A rule returns the first hit on
each page (the first authoritative occurrence, 05 section 2); earlier pages score higher.
Numbers go through ``normalize.parse_amount``, so ``₹ [●]`` becomes a Placeholder, never zero.

Rules were written against the three dev IPOs only (ADR-026); test IPOs are first scored in P2.6.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from finsight.core.schemas import (
    Candidate,
    Count,
    FieldSpec,
    ListValue,
    Money,
    ParsedDoc,
    Placeholder,
    Range,
    Section,
    Table,
    TextValue,
    Value,
)
from finsight.normalize import parse_amount

COVER_PAGES = 15  # the cover block, contacts and "The Offer" summary sit in the first pages
MAX_SECTION_PAGES = 40
_MARKS = re.compile(r"[\^*†‡]")  # footnote marks printed after numbers

_CI = re.IGNORECASE
_AMT = (
    r"(?:₹|Rs\.?|INR)\s?(?:\[\s*[●•]\s*\]|\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(?:million|crore|lakh|billion|mn|cr)\b)?"
)
_AGG = re.compile(rf"aggregating\s+(?:up\s+to\s+|to\s+)?(?P<amt>{_AMT})", _CI)
_OFS = re.compile(
    r"offer\s+for\s+sale\s+of\s+(?:up\s+to\s+)?(?P<n>\[\s*[●•]\s*\]|\d[\d,]*)\s+(?:equity\s+)?shares",
    _CI,
)
_FRESH = re.compile(rf"fresh\s+issue\s+of\s+(?:up\s+to\s+)?(?=\[|\d|{_AMT})", _CI)


@dataclass
class Hit:
    raw: str
    value: Value
    weight: float = 1.0  # rule confidence; multiplies the page score


def _squash(text: str) -> str:
    return " ".join(_MARKS.sub("", text).split())


def _money(text: str) -> Money | Placeholder | None:
    value = parse_amount(text)
    return value if isinstance(value, Money | Placeholder) else None


def _after(
    text: str, anchor: re.Pattern[str], size: int, stop: re.Pattern[str] | None = None
) -> list[str]:
    """Text windows that follow each anchor, cut at ``stop`` when it appears."""
    out = []
    for m in anchor.finditer(text):
        window = text[m.end() : m.end() + size]
        if stop and (cut := stop.search(window)):
            window = window[: cut.start()]
        out.append(window)
    return out


def _first_aggregate(windows: list[str]) -> Hit | None:
    for window in windows:
        m = _AGG.search(window)
        if m and (value := _money(m["amt"])) is not None:
            return Hit(m["amt"], value)
    return None


_STOP_FRESH = re.compile(r"offer\s+for\s+sale", _CI)
_STOP_OFS = re.compile(r"fresh\s+issue", _CI)


def fresh_issue_size(text: str) -> list[Hit]:
    hit = _first_aggregate(_after(text, _FRESH, 350, _STOP_FRESH))
    if hit is None:
        for m in re.finditer(rf"fresh\s+issue\s+of\s+(?:up\s+to\s+)?(?P<amt>{_AMT})", text, _CI):
            if (value := _money(m["amt"])) is not None:
                return [Hit(m["amt"], value)]
    return [hit] if hit else []


def ofs_shares(text: str) -> list[Hit]:
    for m in _OFS.finditer(text):
        n = m["n"]
        value: Value | None
        if "[" in n:
            value = Placeholder(raw=n)
        else:
            count = parse_amount(f"{n} equity shares")
            value = count if isinstance(count, Count) else None
        if value is not None:
            return [Hit(f"{n} equity shares", value)]
    return []


def ofs_amount(text: str) -> list[Hit]:
    hit = _first_aggregate(
        _after(text, re.compile(_OFS.pattern.split(r"\s+(?:equity")[0], _CI), 300, _STOP_OFS)
    )
    return [hit] if hit else []


_PRICE = re.compile(
    rf"(?:at\s+a\s+price\s+of|(?:final\s+)?offer\s+price\s+(?:is|of)|issue\s+price\s+of)\s*(?P<amt>{_AMT})",
    _CI,
)


def offer_price(text: str) -> list[Hit]:
    for m in _PRICE.finditer(text):
        if (value := _money(m["amt"])) is not None:
            return [Hit(m["amt"], value)]
    return []


_BAND = re.compile(r"price\s+band|floor\s+price", _CI)
_RANGE = re.compile(
    rf"(?P<lo>{_AMT})\s*(?:to|-|–|—|and)\s*(?P<hi>(?:₹|Rs\.?)?\s*\d[\d,]*(?:\.\d+)?)", _CI
)
_PLACEHOLDER = re.compile(r"(?:₹|Rs\.?)\s?\[\s*[●•]\s*\]", _CI)


def price_band(text: str) -> list[Hit]:
    for window in _after(text, _BAND, 140):
        if m := _RANGE.search(window):
            hi = m["hi"] if re.match(r"\s*(?:₹|Rs)", m["hi"], _CI) else f"₹ {m['hi'].strip()}"
            value = parse_amount(f"{m['lo']} to {hi}")
            if isinstance(value, Range):
                return [Hit(m.group(0), value)]
        if p := _PLACEHOLDER.search(window):
            return [Hit(p.group(0), Placeholder(raw=p.group(0)))]
    return []


_PUBLIC_OFFER = re.compile(r"public\s+offer(?:ing)?\b", _CI)
_STOP_TOTAL = re.compile(r"comprising|consisting", _CI)


def total_issue_size(text: str) -> list[Hit]:
    hit = _first_aggregate(_after(text, _PUBLIC_OFFER, 900, _STOP_TOTAL))
    return [hit] if hit else []


_FACE = re.compile(rf"face\s+value\s+(?:of\s+)?(?P<amt>{_AMT})", _CI)


def face_value(text: str) -> list[Hit]:
    for m in _FACE.finditer(text):
        if isinstance(value := _money(m["amt"]), Money):
            return [Hit(m["amt"], value)]
    return []


_PROMOTER = re.compile(r"promoters?(?:\s+of\s+our\s+company)?\s*:", _CI)
_STOP_PROMOTER = re.compile(
    r"\b(?:details\s+of\s+the|type\s+of|the\s+offer|offer\s+for|initial\s+public|fresh\s+issue|"
    r"bid\s*/|contact|issue\s+size|our\s+company|selling\s+shareholders?)\b|\.\s",
    _CI,
)


def _upper_run(window: str) -> str:
    """An all-capitals list of names ends where the capitals end ("... LIMITED Eligibility")."""
    words = window.split()
    if not words or not words[0].isupper():
        return window
    kept = []
    for word in words:
        if any(ch.islower() for ch in word):
            break
        kept.append(word)
    return " ".join(kept)


def promoters(text: str) -> list[Hit]:
    for window in _after(text, _PROMOTER, 220, _STOP_PROMOTER):
        window = _upper_run(window)
        names = [n.strip(" ,.;") for n in re.split(r",|\band\b", window, flags=_CI)]
        names = [n for n in names if n and len(n.split()) <= 6]
        if names:
            return [Hit(window.strip(), ListValue(items=names))]
    return []


_REGISTRAR = re.compile(r"registrar\s+to\s+the\s+(?:offer|issue)", _CI)
_REGISTRAR_HEADER = re.compile(
    r"NAME\s+OF\s+REGISTRAR|CONTACT\s+PERSON|TELEPHONE\s+AND\s+E-MAIL|BID\s*/\s*OFFER\s+PERIOD"
)
_KNOWN_REGISTRARS = re.compile(
    r"(?:KFin\s+Technologies|MUFG\s+Intime\s+India|Link\s+Intime\s+India|Bigshare\s+Services|"
    r"Cameo\s+Corporate\s+Services|Integrated\s+Registry\s+Management\s+Services|"
    r"Skyline\s+Financial\s+Services|Purva\s+Sharegistry\s+\(India\)|Maashitla\s+Securities|"
    r"MAS\s+Services)(?:\s+(?:Private|Pvt\.?))?\s+(?:Limited|Ltd\.?)",
    _CI,
)
_NAME_LIMITED = re.compile(
    r"[A-Z][\w&.'\-]*(?:\s+(?:[A-Z][\w&.'\-]*|\([^)]*\))){0,5}?\s+(?:Private\s+|Pvt\.?\s+)?(?:Limited|Ltd\.?)"
)


def registrar(text: str) -> list[Hit]:
    for window in _after(text, _REGISTRAR, 400):
        window = _REGISTRAR_HEADER.sub(" ", window)
        if m := _KNOWN_REGISTRARS.search(window):
            return [Hit(m.group(0), TextValue(text=" ".join(m.group(0).split())))]
        if m := _NAME_LIMITED.search(window):
            return [Hit(m.group(0), TextValue(text=" ".join(m.group(0).split())), 0.5)]
    return []


_BRLM = re.compile(r"book\s+running\s+lead\s+managers?", _CI)
_STOP_BRLM = re.compile(
    r"bid\s*/\s*offer\s+(?:opens|programme)|syndicate\s+member|credit\s+rating|escrow", _CI
)
# Indian BRLMs are a short list; a known name is returned in its full legal form.
_KNOWN_BRLMS = {
    r"Kotak\s+Mahindra\s+Capital": "Kotak Mahindra Capital Company Limited",
    r"Citigroup\s+Global\s+Markets\s+India": "Citigroup Global Markets India Private Limited",
    r"J\.?\s?P\.?\s+Morgan\s+India": "J.P. Morgan India Private Limited",
    r"HSBC\s+Securities\s+and\s+Capital\s+Markets": (
        "HSBC Securities and Capital Markets (India) Private Limited"
    ),
    r"IIFL\s+(?:Capital\s+Services|Securities)": "IIFL Capital Services Limited",
    r"Axis\s+Capital": "Axis Capital Limited",
    r"JM\s+Financial": "JM Financial Limited",
    r"Nomura\s+Financial\s+Advisory": (
        "Nomura Financial Advisory and Securities (India) Private Limited"
    ),
    r"Morgan\s+Stanley\s+India\s+Company": "Morgan Stanley India Company Private Limited",
    r"Goldman\s+Sachs\s+\(India\)\s+Securities": "Goldman Sachs (India) Securities Private Limited",
    r"ICICI\s+Securities": "ICICI Securities Limited",
    r"SBI\s+Capital\s+Markets": "SBI Capital Markets Limited",
    r"Motilal\s+Oswal\s+Investment\s+Advisors": "Motilal Oswal Investment Advisors Limited",
    r"Jefferies\s+India": "Jefferies India Private Limited",
    r"Nuvama\s+Wealth\s+Management": "Nuvama Wealth Management Limited",
    r"Ambit\s+Capital": "Ambit Capital Private Limited",
    r"DAM\s+Capital\s+Advisors": "DAM Capital Advisors Limited",
    r"Equirus\s+Capital": "Equirus Capital Private Limited",
    r"Elara\s+Capital\s+\(India\)": "Elara Capital (India) Private Limited",
    r"Anand\s+Rathi\s+Advisors": "Anand Rathi Advisors Limited",
    r"Avendus\s+Capital": "Avendus Capital Private Limited",
    r"CLSA\s+India": "CLSA India Private Limited",
    r"UBS\s+Securities\s+India": "UBS Securities India Private Limited",
    r"Centrum\s+Capital": "Centrum Capital Limited",
    r"Systematix\s+Corporate\s+Services": "Systematix Corporate Services Limited",
}
_KNOWN_BRLM_RE = [(re.compile(p, _CI), name) for p, name in _KNOWN_BRLMS.items()]


def _known_brlms(text: str) -> list[str]:
    found = [(m.start(), name) for pattern, name in _KNOWN_BRLM_RE if (m := pattern.search(text))]
    return [name for _, name in sorted(found)]


def book_running_lead_managers(text: str) -> list[Hit]:
    for window in _after(text, _BRLM, 4000, _STOP_BRLM):
        found = []
        for pattern, name in _KNOWN_BRLM_RE:
            if m := pattern.search(window):
                found.append((m.start(), name))
        if found:
            names = [name for _, name in sorted(found)]
            return [Hit(window.strip()[:300], ListValue(items=names))]
    return []


RULES: dict[str, Callable[[str], list[Hit]]] = {
    "fresh_issue_size": fresh_issue_size,
    "ofs_shares": ofs_shares,
    "ofs_amount": ofs_amount,
    "offer_price": offer_price,
    "price_band": price_band,
    "total_issue_size": total_issue_size,
    "face_value": face_value,
    "book_running_lead_managers": book_running_lead_managers,
    "registrar": registrar,
    "promoters": promoters,
}


def pages_to_search(doc: ParsedDoc, sections: list[Section], field: FieldSpec) -> list[int]:
    """PDF pages in search order: the cover block first, then the field's sections."""
    pages: list[int] = []
    if "cover" in field.sections:
        pages += range(1, min(COVER_PAGES, doc.n_pages) + 1)
    by_id = {s.id: s for s in sections}
    for section_id in field.sections:
        if section := by_id.get(section_id):
            end = min(section.end_page, section.start_page + MAX_SECTION_PAGES - 1)
            pages += [p for p in range(section.start_page, end + 1) if p not in pages]
    return pages


SPLIT_LIST_FIELDS = {"book_running_lead_managers"}  # the contact table runs over a page break


def _merge_split_list(candidates: list[Candidate], doc: ParsedDoc) -> list[Candidate]:
    """One list from a first hit and the hit on the next page (Hexaware: 3 + 2 BRLMs)."""
    lists = [c for c in candidates if isinstance(c.value, ListValue)]
    if not lists:
        return candidates
    first = min(lists, key=lambda c: c.page)
    assert isinstance(first.value, ListValue)
    items = list(first.value.items)
    run = [first]
    if first.page < doc.n_pages:  # the continuation page has names but no heading
        next_text = _squash(doc.pages[first.page].text)
        items += [i for i in _known_brlms(next_text) if i not in items]
        run += [c for c in lists if c.page == first.page + 1]
    merged = first.model_copy(update={"value": ListValue(items=items)})
    return [merged] + [c for c in candidates if c not in run]


def _score(page: int, in_cover: bool, weight: float) -> float:
    base = 0.95 - 0.02 * (page - 1) if in_cover else 0.7 - 0.005 * (page - 1)
    return round(max(base, 0.3) * weight, 4)


class RulesExtractor:
    """Implements ``core.interfaces.Extractor`` with the patterns above."""

    name = "rules"

    def extract(
        self,
        doc: ParsedDoc,
        sections: list[Section],
        tables: list[Table],
        field: FieldSpec,
    ) -> list[Candidate]:
        rule = RULES.get(field.id)
        if rule is None:
            return []
        candidates: list[Candidate] = []
        for number in pages_to_search(doc, sections, field):
            page = doc.pages[number - 1]
            hits = rule(_squash(page.text))
            if not hits:
                continue
            hit = hits[0]
            candidates.append(
                Candidate(
                    field_id=field.id,
                    extractor=self.name,
                    doc_type=doc.doc_type,
                    raw=hit.raw,
                    value=hit.value,
                    page=number,
                    printed_page=page.printed_page,
                    score=_score(number, number <= COVER_PAGES, hit.weight),
                )
            )
        if field.id in SPLIT_LIST_FIELDS:
            candidates = _merge_split_list(candidates, doc)
        return sorted(candidates, key=lambda c: (-c.score, c.page))
