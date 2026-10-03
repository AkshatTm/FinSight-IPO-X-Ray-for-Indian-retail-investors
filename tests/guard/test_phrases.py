"""Forbidden phrases (B01 §6, B05 §9): every UI string passes; instruction-style phrases do not."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from finsight.guard import find_forbidden, is_clean

ROOT = Path(__file__).resolve().parents[2]
STRING = re.compile(r'\b(en|hi): "((?:\\.|[^"\\])*)"')


def ui_strings() -> list[tuple[str, str]]:
    files = [ROOT / "frontend/lib/i18n.ts", *sorted((ROOT / "frontend/lib/content").glob("*.ts"))]
    out = []
    for path in files:
        for match in STRING.finditer(path.read_text(encoding="utf-8")):
            out.append((f"{path.name}:{match.group(1)}", match.group(2).replace('\\"', '"')))
    return out


def test_there_are_ui_strings_to_check() -> None:
    assert len(ui_strings()) > 500


def test_every_ui_string_is_clean() -> None:
    dirty = [
        (where, text, find_forbidden(text)) for where, text in ui_strings() if not is_clean(text)
    ]
    assert dirty == []


@pytest.mark.parametrize(
    "text",
    [
        "You should apply for this IPO.",
        "Investors must not buy these shares.",
        "It is advisable to subscribe to the issue.",
        "Avoid this IPO.",
        "Buy this stock before listing.",
        "This is a strong IPO with a solid track record.",
        "The issue looks safe.",
        "Experts say it is worth investing.",
        "Guaranteed returns for every investor.",
        "Expect a listing gain of 20%.",
        "Analysts set a target price of ₹500.",
        "This is our recommended pick.",
        "आपको यह आईपीओ ज़रूर खरीदें",
        "इसमें निवेश करना चाहिए",
    ],
)
def test_instruction_style_phrases_are_blocked(text: str) -> None:
    assert find_forbidden(text), text


@pytest.mark.parametrize(
    "text",
    [
        "FinSight explains what IPO documents say. It won't tell you whether to apply or buy.",
        "The selling shareholders will receive the money from the offer for sale.",
        "Our loans are guaranteed by our Promoters, who may withdraw these guarantees.",
        "Investors may lose part of their investment if our revenue falls.",
        "We may not be able to sell our products at the prices we expect.",
        "Our strong dependence on a few customers is a risk.",
        "Any failure to apply for renewals of our licences in time could stop production.",
        "We rely on suppliers who may avoid long-term contracts.",
    ],
)
def test_document_language_passes(text: str) -> None:
    assert is_clean(text), find_forbidden(text)
