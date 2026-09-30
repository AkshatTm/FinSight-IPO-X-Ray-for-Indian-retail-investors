import pytest

from finsight.parse.tables import detect_header_scale


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(in ₹ million)", "₹ in million"),
        ("(₹ in million, except per share data)", "₹ in million"),
        ("Estimated Amount (in ₹ million)", "₹ in million"),
        ("(₹ million)", "₹ in million"),
        ("(Amount in ₹ crores)", "₹ in crore"),
        ("(₹ in crore)", "₹ in crore"),
        ("(Rs. in lakhs)", "₹ in lakh"),
        ("(Rs in Lacs)", "₹ in lakh"),
        ("(INR in billion)", "₹ in billion"),
        ("(in ₹ bn)", "₹ in billion"),
        ("(in ₹ mn)", "₹ in million"),
        ("(Rupees in thousands)", "₹ in thousand"),
        ("(₹ ’000)", "₹ in thousand"),
        ("Amount (in ₹)", "₹"),
        ("(in US$ million)", "$ in million"),
        ("(in million)", "in million"),
        ("Particulars", None),
        ("Gross Proceeds of the Fresh Issue", None),
        ("1 million Equity Shares", None),  # a count, not a unit header
    ],
)
def test_detect_header_scale(text: str, expected: str | None) -> None:
    assert detect_header_scale(text) == expected


def test_first_scale_in_a_multi_line_header_wins() -> None:
    assert detect_header_scale("Particulars\nEstimated Amount\n(in ₹ million)\n(₹ in crore)") == (
        "₹ in million"
    )
