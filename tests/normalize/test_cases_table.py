"""Table-driven cases for the numeral normalizer (02_ARCHITECTURE.md section 10.4, ADR-028).

Each expected value is a compact tuple:
    ("money", value, currency, scale_word, precision)
    ("count", value, unit)
    ("percent", value, is_bps)
    ("placeholder",)
    ("range", low_value, high_value, currency)
    None  -> not an amount
"""

from decimal import Decimal

import pytest

from finsight.core.schemas import Count, Money, Percent, Placeholder, Range
from finsight.normalize import parse_amount, parse_amounts

Expected = tuple[object, ...] | None


def _shape(amount: object) -> Expected:
    if amount is None:
        return None
    if isinstance(amount, Money):
        return ("money", amount.value_inr, amount.currency, amount.scale_word, amount.precision)
    if isinstance(amount, Count):
        return ("count", amount.value, amount.unit)
    if isinstance(amount, Percent):
        return ("percent", amount.value, amount.is_bps)
    if isinstance(amount, Placeholder):
        return ("placeholder",)
    if isinstance(amount, Range):
        return ("range", amount.low.value_inr, amount.high.value_inr, amount.low.currency)
    raise AssertionError(type(amount))


def M(value: str, scale: str | None = None, prec: int = 0, cur: str = "INR") -> Expected:
    return ("money", Decimal(value), cur, scale, prec)


def C(value: int, unit: str | None = None) -> Expected:
    return ("count", value, unit)


def P(value: str, bps: bool = False) -> Expected:
    return ("percent", Decimal(value), bps)


def R(low: str, high: str, cur: str = "INR") -> Expected:
    return ("range", Decimal(low), Decimal(high), cur)


PH: Expected = ("placeholder",)

# ----------------------------------------------------------------------------- English money
MONEY = [
    ("₹ 800 crore", M("8000000000", "crore")),
    ("₹800.00 crore", M("8000000000", "crore", 2)),
    ("Rs. 800 crores", M("8000000000", "crore")),
    ("Rs 1,250.5 crore", M("12505000000", "crore", 1)),
    ("INR 4,720 million", M("4720000000", "million")),
    ("Rupees 50 lakh", M("5000000", "lakh")),
    ("₹ 50 lakhs", M("5000000", "lakh")),
    ("₹ 50 lac", M("5000000", "lakh")),
    ("₹ 5 Lacs", M("500000", "lakh")),
    ("₹ 2.5 cr", M("25000000", "crore", 1)),
    ("₹ 2.5 Cr.", M("25000000", "crore", 1)),
    ("₹ 10 mn", M("10000000", "million")),
    ("₹ 1.2 bn", M("1200000000", "billion", 1)),
    ("₹ 3 billion", M("3000000000", "billion")),
    ("₹ 12 thousand", M("12000", "thousand")),
    ("₹ 1,23,45,678", M("12345678")),
    ("₹ 12,345,678", M("12345678")),
    ("₹ 1,00,000.50", M("100000.50", None, 2)),
    ("Re. 1", M("1")),
    ("₹ 10 each", M("10")),
    ("₹ 440 per Equity Share", M("440")),
    ("US$ 25 million", M("25000000", "million", cur="USD")),
    ("$ 1.5 billion", M("1500000000", "billion", 1, cur="USD")),
    ("USD 300 million", M("300000000", "million", cur="USD")),
    ("₹ 800 crore", M("8000000000", "crore")),
    ("₹ 800 crore", M("8000000000", "crore")),
    ("₹800crore", M("8000000000", "crore")),
    ("Rs.800 crore", M("8000000000", "crore")),
    ("800 crore", M("8000000000", "crore")),
    ("₹ 0.50 crore", M("5000000", "crore", 2)),
    ("₹ 1 lakh crore", M("1000000000000", "lakh crore")),
    ("₹ 7,278.02 million", M("7278020000", "million", 2)),
    ("4,720 million rupees", M("4720000000", "million")),
]

# ----------------------------------------------------------------------------- table cells
CELLS = [
    ("4,720", "₹ in million", M("4720000000", "million")),
    ("(1,234.50)", "₹ in million", M("-1234500000", "million", 2)),
    ("-1,234", "₹ in lakh", M("-123400000", "lakh")),
    ("−56.7", "₹ in crore", M("-567000000", "crore", 1)),
    ("1,900.00 (1)", "₹ in million", M("1900000000", "million", 2)),
    ("4,720", "$ in million", M("4720000000", "million", cur="USD")),
    ("12", "in million", M("12000000", "million")),
    ("250", "₹", M("250")),
    ("[●](1)", "₹ in million", PH),
    ("[●]**", "₹ in million", PH),
    ("4,720", None, C(4720)),
    ("12.5", None, None),
    ("–", "₹ in million", None),
    ("N.A.", "₹ in million", None),
    ("", "₹ in million", None),
]

# ----------------------------------------------------------------------------- other kinds
OTHER = [
    ("[●]", PH),
    ("[•]", PH),
    ("[ ● ]", PH),
    ("₹[●]", PH),
    ("₹ [●] crore", PH),
    ("[●] Equity Shares", PH),
    ("101,815,859 equity shares", C(101815859, "equity shares")),
    ("4,32,12,345 Equity Shares", C(43212345, "equity shares")),
    ("12 million Equity Shares", C(12000000, "equity shares")),
    ("2.5 crore equity shares", C(25000000, "equity shares")),
    ("10,000 shares", C(10000, "shares")),
    ("12.5%", P("12.5")),
    ("12.5 %", P("12.5")),
    ("12.50 per cent", P("12.50")),
    ("8 percent", P("8")),
    ("(2.3)%", P("-2.3")),
    ("-4.2%", P("-4.2")),
    ("150 bps", P("1.50", True)),
    ("25 basis points", P("0.25", True)),
    ("₹ 440 to ₹ 463", R("440", "463")),
    ("₹440-₹463", R("440", "463")),
    ("₹ 440 – 463", R("440", "463")),
    ("₹ 95—100", R("95", "100")),
    ("₹ 1,000 to 1,200 crore", R("10000000000", "12000000000")),
    ("Rs. 5 lakh to Rs. 10 lakh", R("500000", "1000000")),
    ("FY2024", None),
    ("Fiscal 2025", None),
    ("Particulars", None),
    ("page 163", None),
    ("Q3FY25", None),
]

# ----------------------------------------------------------------------------- Hindi (ADR-028)
HINDI = [
    ("₹ 800 करोड़", M("8000000000", "crore")),  # precomposed ड़
    ("₹ 800 करोड़", M("8000000000", "crore")),  # ड + nukta
    ("₹ 800 करोड", M("8000000000", "crore")),  # nukta dropped
    ("800 करोड़ रुपये", M("8000000000", "crore")),
    ("₹ 800 करोड़ रुपए", M("8000000000", "crore")),
    ("रु. 50 लाख", M("5000000", "lakh")),
    ("₹ ८०० करोड़", M("8000000000", "crore")),
    ("५० लाख रुपये", M("5000000", "lakh")),
    ("८,००० करोड़ रुपये", M("80000000000", "crore")),
    ("₹ ४४०", M("440")),
    ("₹ 12 हज़ार", M("12000", "thousand")),  # हज़ार precomposed
    ("₹ 12 हजार", M("12000", "thousand")),  # हजार
    ("₹ 2 अरब", M("2000000000", "billion")),
    ("₹ 1,250.5 करोड़", M("12505000000", "crore", 1)),
    ("12.5 प्रतिशत", P("12.5")),
    ("₹ 440 से ₹ 463", R("440", "463")),
    ("₹ [●] करोड़", PH),
    ("5 करोड़ इक्विटी शेयर", C(50000000, "equity shares")),
]


@pytest.mark.parametrize(("text", "expected"), MONEY + OTHER + HINDI)
def test_parse_amount(text: str, expected: Expected) -> None:
    assert _shape(parse_amount(text)) == expected


@pytest.mark.parametrize(("cell", "header", "expected"), CELLS)
def test_parse_table_cell(cell: str, header: str | None, expected: Expected) -> None:
    assert _shape(parse_amount(cell, header_scale=header)) == expected


def test_case_counts() -> None:
    assert len(MONEY) + len(CELLS) + len(OTHER) + len(HINDI) >= 80
    assert len(HINDI) >= 12


# ----------------------------------------------------------------------------- sentences
def test_sentence_with_two_amounts_and_spans() -> None:
    text = "a Fresh Issue of ₹ 4,720 million and an Offer for Sale of ₹ 14,280 million."
    found = parse_amounts(text)
    assert [_shape(f.amount) for f in found] == [
        M("4720000000", "million"), M("14280000000", "million"),
    ]  # fmt: skip
    assert [text[f.start : f.end] for f in found] == ["₹ 4,720 million", "₹ 14,280 million"]
    assert all(f.amount.raw == text[f.start : f.end] for f in found)  # type: ignore[union-attr]


def test_years_page_numbers_and_bare_numbers_are_skipped() -> None:
    text = "In FY2024 revenue grew 12.5% to ₹ 1,250 crore; see pages 21, 87 and 453 of 2024."
    assert [_shape(f.amount) for f in parse_amounts(text)] == [
        P("12.5"), M("12500000000", "crore"),
    ]  # fmt: skip


def test_placeholder_and_money_in_the_offer_sentence() -> None:
    text = "Fresh Issue of up to [●] Equity Shares aggregating up to ₹ 800.00 crore"
    assert [_shape(f.amount) for f in parse_amounts(text)] == [
        PH, M("8000000000", "crore", 2),
    ]  # fmt: skip


def test_price_band_is_one_range() -> None:
    found = parse_amounts("the price band of ₹ 440 to ₹ 463 per Equity Share")
    assert [_shape(f.amount) for f in found] == [R("440", "463")]


def test_from_to_is_a_change_not_a_range() -> None:
    found = parse_amounts("revenue rose from ₹ 100 crore to ₹ 200 crore")
    assert [_shape(f.amount) for f in found] == [
        M("1000000000", "crore"), M("2000000000", "crore"),
    ]  # fmt: skip


def test_hindi_sentence() -> None:
    text = "कंपनी फ्रेश इश्यू से ₹ ८०० करोड़ जुटाएगी।"
    found = parse_amounts(text)
    assert [_shape(f.amount) for f in found] == [M("8000000000", "crore")]
    assert text[found[0].start : found[0].end] == "₹ ८०० करोड़"


def test_share_count_and_face_value_in_one_sentence() -> None:
    text = "Offer for Sale of up to 101,815,859 equity shares of face value of ₹ 10 each"
    assert [_shape(f.amount) for f in parse_amounts(text)] == [
        C(101815859, "equity shares"), M("10"),
    ]  # fmt: skip


@pytest.mark.parametrize(
    "text",
    [
        "Reserved 5% for employees at a discount of ₹ 44 per share",
        "retail 35.00% and QIB 50%, 12 million Equity Shares, 150 bps, Rest 10 crore",
    ],
)
def test_spans_are_tight(text: str) -> None:
    found = parse_amounts(text)
    assert found
    for f in found:
        raw = text[f.start : f.end]
        assert raw == raw.strip()
        assert f.amount.raw == raw  # type: ignore[union-attr]
