"""Teacher prompt and output schema (B03 §3.2): one call per corpus risk, JSON out.

The notebook (``notebooks/b2_teacher_kaggle.ipynb``) sends ``messages(risk)`` to the teacher
through vLLM with ``OUTPUT_SCHEMA`` as guided JSON; ``parse_output`` reads the answer back.
"""

from __future__ import annotations

import json
import re
from typing import Any, get_args

from pydantic import BaseModel, Field, ValidationError

from finsight.core.schemas import RiskCategory

CATEGORIES: tuple[str, ...] = get_args(RiskCategory)
PROMPT_VERSION = "teacher-v1"

CATEGORY_HELP = {
    "financial": "losses, falling revenue or margins, cash flow, working capital",
    "debt_liquidity": "borrowings, repayment, covenants, liquidity, interest rates on our loans",
    "customers_suppliers": "dependence on few customers, suppliers or distributors",
    "competition": "competitors, pricing pressure, market share",
    "legal_litigation": "court cases, claims, penalties, tax disputes",
    "regulatory": "laws, licences, approvals, government policy, SEBI/RBI rules",
    "promoters_governance": (
        "promoters, related parties, management, control, conflicts of interest"
    ),
    "operations": "plants, capacity, people, projects, insurance, supply disruptions",
    "technology_data": "IT systems, cyber security, data protection, intellectual property",
    "market_macro": "economy, industry cycles, currency, share price after listing",
}

SYSTEM = f"""You label risk factors from Indian IPO offer documents and rewrite them in plain
English. Answer with one JSON object and nothing else.

Fields:
- "category": exactly one of {", ".join(CATEGORIES)}.
- "seriousness_1to5": 1 = routine boilerplate, 5 = a specific, material problem the company
  already has.
- "hard_fact": true if the risk describes something that has already happened (a loss, a case, a
  default), false if it only describes something that may happen.
- "simple": the risk in plain English for a first-time investor, at most 60 words, sentences under
  20 words. Keep every number exactly as written, with its unit. Keep how certain it is: "may" stays
  "may", "has" stays "has". Add no facts. Never tell anyone to buy, sell, apply, invest or avoid,
  and never judge the IPO as good, bad, safe or worth it.
- "numbers_copied": every number you used in "simple", copied exactly.

Categories: {"; ".join(f"{k} = {v}" for k, v in CATEGORY_HELP.items())}."""


class TeacherOutput(BaseModel):
    category: RiskCategory
    seriousness_1to5: int = Field(ge=1, le=5)
    hard_fact: bool
    simple: str = Field(min_length=1)
    numbers_copied: list[str] = Field(default_factory=list)


OUTPUT_SCHEMA: dict[str, Any] = TeacherOutput.model_json_schema()


def messages(title: str, body: str) -> list[dict[str, str]]:
    """Chat messages for one risk (title may be empty for untitled risks)."""
    text = f"Title: {title.strip()}\n\n{body.strip()}" if title.strip() else body.strip()
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]


class ParseError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason  # invalid_json | bad_category | bad_schema


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_output(raw: str) -> TeacherOutput:
    """The teacher's JSON, tolerating code fences and a ``<think>`` block before it."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    text = _FENCE.sub("", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ParseError("invalid_json")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as err:
        raise ParseError("invalid_json") from err
    if not isinstance(data, dict):
        raise ParseError("invalid_json")
    if data.get("category") not in CATEGORIES:
        raise ParseError("bad_category")
    try:
        return TeacherOutput.model_validate(data)
    except ValidationError as err:
        raise ParseError("bad_schema") from err
