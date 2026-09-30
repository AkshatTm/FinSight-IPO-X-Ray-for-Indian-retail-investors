"""Turn Indian-format amounts in text into typed values (02_ARCHITECTURE.md section 10.4).

"₹ 1,250.5 crore", "Rs. 12,499.8 mn", "(1,234.50)" under a "₹ in million" header,
"₹ ८०० करोड़", "[●]", "12.5%", "150 bps", "₹ 440 to ₹ 463" and "12 million Equity Shares"
all become ``Money`` / ``Percent`` / ``Placeholder`` / ``Range`` / ``Count``.

Rules in plain words:
- An amount needs a signal: a currency, a scale word, %, bps or a share unit. Bare numbers
  in running text (years, page numbers) are skipped; only a whole table cell may be bare.
- Money is exact: ``Decimal`` digits times the scale, never a float. ``precision`` is the
  number of decimals as printed, which ``equal`` uses as the tolerance.
- A scale word without a currency is taken as rupees ("4,720 million").
- ``[●]`` is always a ``Placeholder``, never zero.
- Devanagari digits and Hindi scale words are read (ADR-028); spans index the original text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from finsight.core.schemas import Amount, Count, Money, Percent, Placeholder, Range

Currency = Literal["INR", "USD", "OTHER"]

MULTIPLIER: dict[str, Decimal] = {
    "thousand": Decimal(10) ** 3,
    "lakh": Decimal(10) ** 5,
    "million": Decimal(10) ** 6,
    "crore": Decimal(10) ** 7,
    "billion": Decimal(10) ** 9,
    "trillion": Decimal(10) ** 12,
    "lakh crore": Decimal(10) ** 12,
}

# Devanagari scale words; nukta letters may be precomposed (U+095B/U+095C), decomposed
# (letter + U+093C) or dropped.
_NUKTA = "़"
_HI_THOUSAND = f"ह(?:ज़|ज{_NUKTA}?)ार"  # हज़ार
_HI_LAKH = "लाख"  # लाख
_HI_CRORE = f"करो(?:ड़|ड{_NUKTA}?)"  # करोड़
_HI_ARAB = "अरब"  # अरब
_HI_RUPEES = "रुप(?:ये|ए)"  # रुपये / रुपए
_HI_RU = "रु\\."  # रु.
_HI_PERCENT = "प्रतिशत"  # प्रतिशत
_HI_SE = "से"  # से
_HI_EQUITY = "इक्विटी"  # इक्विटी
_HI_SHARE = "शेयर(?:ों)?"  # शेयर / शेयरों

_SCALE_WORDS = [
    (r"lakh\s+crores?", "lakh crore"),
    (r"lakhs?|lacs?", "lakh"),
    (r"crores?|crs?\.?", "crore"),
    (r"millions?|mn", "million"),
    (r"billions?|bn", "billion"),
    (r"trillions?|tn", "trillion"),
    (r"thousands?", "thousand"),
    (_HI_THOUSAND, "thousand"),
    (_HI_LAKH, "lakh"),
    (_HI_CRORE, "crore"),
    (_HI_ARAB, "billion"),
]
_SCALE_RES = [(re.compile(rf"^(?:{p})$", re.IGNORECASE), name) for p, name in _SCALE_WORDS]
_SCALE = "|".join(p for p, _ in _SCALE_WORDS)

_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d{1,3}(?:,\d{2})*,\d{3}|\d+)(?:\.\d+)?"
_CUR_PRE = rf"(?<![A-Za-z])(?:US\$|USD|INR|Rupees|Rs\.?|Re\.?)|₹|\$|{_HI_RU}"
_CUR_POST = rf"(?<![A-Za-z])(?:rupees|INR)(?![A-Za-z])|{_HI_RUPEES}"
_PLACEHOLDER = r"\[\s*[●•]\s*\]"

_ATOM = re.compile(
    rf"""
    (?:(?P<cur>{_CUR_PRE})\s*)?
    (?:
        (?P<ph>{_PLACEHOLDER})
      | (?P<sign>(?<![\w.])[-−](?=\d))?(?P<num>(?<![A-Za-z\d,])(?<!\d\.){_NUM})(?!\d)
    )
    (?:\s*(?P<scale>(?:{_SCALE}))(?![A-Za-zऀ-ॿ]))?
    (?:\s*(?P<curpost>{_CUR_POST}))?
    """,
    re.IGNORECASE | re.VERBOSE,
)
_PAREN_PERCENT = re.compile(
    rf"\((?P<num>{_NUM})\)\s*(?:%|per\s?cent|percent|{_HI_PERCENT})", re.IGNORECASE
)
_PERCENT_SUFFIX = re.compile(rf"\s*(?:%|per\s?cent(?![a-z])|percent|{_HI_PERCENT})", re.IGNORECASE)
_BPS_SUFFIX = re.compile(r"\s*(?:bps|basis\s+points?)(?![a-z])", re.IGNORECASE)
_SHARES_SUFFIX = re.compile(
    rf"\s*(?P<unit>(?P<eq>equity\s+|{_HI_EQUITY}\s*)?(?:shares?(?![a-z])|{_HI_SHARE}))",
    re.IGNORECASE,
)
_RANGE_CONNECTOR = re.compile(rf"^\s*(?:to|-|–|—|{_HI_SE})\s*$", re.IGNORECASE)
_FROM_BEFORE = re.compile(r"\bfrom\s*$", re.IGNORECASE)
_FOOTNOTE = re.compile(r"(?<=\S)\s*(?:\(\d{1,2}\)|\*+)$")
_BARE_CELL = re.compile(rf"^(?P<open>\()?(?P<sign>[-−])?\s*(?P<num>{_NUM})(?P<close>\))?$")

_SPACES = str.maketrans({" ": " ", " ": " ", " ": " ", " ": " "})
_DEVANAGARI_DIGITS = str.maketrans({chr(0x0966 + d): str(d) for d in range(10)})


@dataclass(frozen=True)
class AmountSpan:
    """An amount and where it sits in the text (``text[start:end] == amount.raw``)."""

    amount: Amount
    start: int
    end: int


def _prepare(text: str) -> str:
    """Same length as ``text`` so spans stay valid: Western digits, plain spaces."""
    return text.translate(_SPACES).translate(_DEVANAGARI_DIGITS)


def scale_name(word: str) -> str:
    """Canonical scale ("crore") for a scale word as written ("Crs.", "करोड़")."""
    word = " ".join(word.split())
    for pattern, name in _SCALE_RES:
        if pattern.match(word):
            return name
    raise ValueError(f"not a scale word: {word!r}")


def _currency(token: str | None) -> Currency:
    if token and ("$" in token or token.upper() == "USD"):
        return "USD"
    return "INR"


def _decimal(num: str) -> tuple[Decimal, int]:
    digits = num.replace(",", "")
    precision = len(digits.split(".")[1]) if "." in digits else 0
    return Decimal(digits), precision


def _money(
    num: str, scale: str | None, currency: Currency, raw: str, negative: bool = False
) -> Money:
    value, precision = _decimal(num)
    if scale is not None:
        value *= MULTIPLIER[scale]
    return Money(value_inr=-value if negative else value, currency=currency, raw=raw,
                 scale_word=scale, precision=precision)  # fmt: skip


@dataclass
class _Atom:
    start: int
    end: int
    kind: Literal["money", "count", "percent", "placeholder", "bare"]
    num: str | None
    scale: str | None
    currency: Currency
    has_currency: bool
    negative: bool
    unit: str | None = None
    is_bps: bool = False


def _atoms(text: str) -> list[_Atom]:
    atoms: list[_Atom] = []
    covered = 0
    for m in _PAREN_PERCENT.finditer(text):
        atoms.append(_Atom(m.start(), m.end(), "percent", m["num"], None, "INR", False, True))
    for m in _ATOM.finditer(text):
        if any(a.start <= m.start() < a.end for a in atoms):
            continue
        cur = m["cur"] or m["curpost"]
        scale = scale_name(m["scale"]) if m["scale"] else None
        end = m.end()
        atom = _Atom(m.start(), end, "bare", m["num"], scale, _currency(cur), cur is not None,
                     m["sign"] is not None)  # fmt: skip
        if m["ph"]:
            atom.kind = "placeholder"
            if shares := _SHARES_SUFFIX.match(text, end):
                atom.end = shares.end()
        elif cur is None and (pct := _PERCENT_SUFFIX.match(text, end)) and not scale:
            atom.kind, atom.end = "percent", pct.end()
        elif cur is None and (bps := _BPS_SUFFIX.match(text, end)) and not scale:
            atom.kind, atom.end, atom.is_bps = "percent", bps.end(), True
        elif cur is None and (shares := _SHARES_SUFFIX.match(text, end)):
            atom.kind, atom.end = "count", shares.end()
            atom.unit = "equity shares" if shares["eq"] else "shares"
        elif cur is not None or scale is not None:
            atom.kind = "money"
        if atom.start >= covered:
            atoms.append(atom)
            covered = atom.end
    return sorted(atoms, key=lambda a: a.start)


def _to_amount(atom: _Atom, raw: str) -> Amount | None:
    if atom.kind == "placeholder":
        return Placeholder(raw=raw)
    assert atom.num is not None
    if atom.kind == "percent":
        value, _ = _decimal(atom.num)
        if atom.is_bps:
            value /= Decimal(100)
        return Percent(value=-value if atom.negative else value, raw=raw, is_bps=atom.is_bps)
    if atom.kind == "count":
        value, _ = _decimal(atom.num)
        value *= MULTIPLIER[atom.scale] if atom.scale else Decimal(1)
        if value != value.to_integral_value():
            return None
        return Count(value=int(value), raw=raw, unit=atom.unit)
    if atom.kind == "money":
        return _money(atom.num, atom.scale, atom.currency, raw, atom.negative)
    return None


def _as_range(text: str, low: _Atom, high: _Atom) -> Range | None:
    """``low``-``high`` as a price band ("₹ 440 to ₹ 463", "₹ 1,000 to 1,200 crore")."""
    if low.kind not in ("money", "bare") or high.kind not in ("money", "bare"):
        return None
    if not (low.has_currency or high.has_currency) or low.num is None or high.num is None:
        return None
    if not _RANGE_CONNECTOR.match(text[low.end : high.start]):
        return None
    if _FROM_BEFORE.search(text[: low.start]):
        return None  # "from ₹ 100 crore to ₹ 200 crore" is a change, not a band
    currency = low.currency if low.has_currency else high.currency
    low_scale = low.scale or high.scale
    lo = _money(low.num, low_scale, currency, text[low.start : low.end])
    hi = _money(high.num, high.scale or low.scale, currency, text[high.start : high.end])
    if lo.value_inr is None or hi.value_inr is None or lo.value_inr > hi.value_inr:
        return None
    return Range(low=lo, high=hi, raw=text[low.start : high.end])


def parse_amounts(text: str) -> list[AmountSpan]:
    """Every amount in running text, in order; bare numbers (years, pages) are skipped."""
    clean = _prepare(text)
    atoms = _atoms(clean)
    found: list[AmountSpan] = []
    i = 0
    while i < len(atoms):
        atom = atoms[i]
        if i + 1 < len(atoms) and (band := _as_range(clean, atom, atoms[i + 1])):
            band = band.model_copy(update={"raw": text[atom.start : atoms[i + 1].end]})
            found.append(AmountSpan(band, atom.start, atoms[i + 1].end))
            i += 2
            continue
        amount = _to_amount(atom, text[atom.start : atom.end])
        if amount is not None:
            found.append(AmountSpan(amount, atom.start, atom.end))
        i += 1
    return found


def _header_unit(header_scale: str) -> tuple[Currency, str | None]:
    """("INR", "million") for a table header unit such as "₹ in million" or "$ in million"."""
    currency: Currency = "USD" if "$" in header_scale else "INR"
    words = header_scale.replace("₹", " ").replace("$", " ").split()
    scale_words = [w for w in words if w.lower() != "in"]
    return currency, scale_name(" ".join(scale_words)) if scale_words else None


def parse_amount(text: str, header_scale: str | None = None) -> Amount | None:
    """The amount in one table cell or candidate string.

    A bare number is allowed only when it is the whole cell: with ``header_scale`` (e.g.
    "₹ in million", from ``parse.tables``) it becomes money in that unit, with "(1,234)" or
    "-1,234" negative; without a header an integer is a ``Count``. Footnote marks such as
    "(1)" or "**" after the value are ignored.
    """
    cell = _FOOTNOTE.sub("", _prepare(text).strip())
    while (stripped := _FOOTNOTE.sub("", cell)) != cell:
        cell = stripped
    bare = _BARE_CELL.match(cell)
    if bare and bool(bare["open"]) == bool(bare["close"]):
        negative = bool(bare["open"]) or bool(bare["sign"])
        if header_scale:
            currency, scale = _header_unit(header_scale)
            return _money(bare["num"], scale, currency, text.strip(), negative)
        value, precision = _decimal(bare["num"])
        if precision or negative:
            return None
        return Count(value=int(value), raw=text.strip())
    found = parse_amounts(text)
    return found[0].amount if found else None
