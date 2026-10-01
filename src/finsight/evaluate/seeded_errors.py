"""E5: the seeded-error benchmark for the number verifier (05 section 6).

    uv run python -m finsight.evaluate.seeded_errors [--split dev|test|all]

This is a **unit benchmark**: answers are written from gold values with templates (English and
Hindi), the evidence is the real passage of the demo document that states the value, and one
number per answer is corrupted by a known rule. High recall is expected by design; evidence on
natural errors comes from real LLM answers (E7) and frontier answers (E9).

| type                 | construction                                   | expected       |
| scale_lakh_crore     | the crore figure printed with "lakh" (100x)    | scale_mismatch |
| scale_million_crore  | same digits, million -> crore (10x)            | scale_mismatch |
| digit                | one digit changed                              | wrong_value    |
| swap_metric          | another field's value in this field's sentence | wrong_metric   |
| invented             | an extra sentence with a number not in evidence| not_found      |
| rounding_ok (correct)| the value in another unit, rounded as printed  | verified       |

Detection = the corrupted number is not ✅. False alarm = any number of a correct answer is
not ✅. Rules are tuned on the dev IPOs only; the report shows dev and test separately.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.core.schemas import Amount, Count, Money, Passage
from finsight.evaluate.metrics import wilson_interval
from finsight.ingest.registry import list_demo_ipos
from finsight.normalize import group_digits, parse_amount, parse_amounts
from finsight.retrieve import IpoIndex, index_dir
from finsight.verify import evidence_amounts, same_value, verify_answer

SEED = 2026
N_PER_TYPE = 20
N_CORRECT = 100
MAX_EVIDENCE = 5
ERROR_TYPES = ("scale_lakh_crore", "scale_million_crore", "digit", "swap_metric", "invented")
EXPECTED = {
    "scale_lakh_crore": "scale_mismatch",
    "scale_million_crore": "scale_mismatch",
    "digit": "wrong_value",
    "swap_metric": "wrong_metric",
    "invented": "not_found",
    "correct": "verified",
    "rounding_ok": "verified",
}
# Kept for honesty: the first run on all 10 IPOs, with rules frozen after tuning on the 3 dev
# IPOs (1 Oct 2026). Five rounded unit slips on test IPOs were caught as wrong_value, not
# scale_mismatch; the power-of-ten check was then made precision-aware. See ADR-044.
FIRST_RUN = {
    "rules": "frozen on dev IPOs",
    "detection": "100/100",
    "false_alarm": "0/100",
    "scale_mismatch_recall": "35/40",
    "exact_reason": "95/100",
    "misses": "5 scale_lakh_crore items on test IPOs, flagged as wrong_value",
}
TEMPLATES = {
    "fresh_issue_size": ("The fresh issue is of {v} [1].", "फ्रेश इश्यू {v} का है [1]।"),
    "ofs_shares": ("The offer for sale is of {v} [1].", "ऑफर फॉर सेल {v} का है [1]।"),
    "ofs_amount": ("The offer for sale amounts to {v} [1].", "ऑफर फॉर सेल की राशि {v} है [1]।"),
    "offer_price": (
        "The offer price is {v} per equity share [1].",
        "ऑफर प्राइस {v} प्रति इक्विटी शेयर है [1]।",
    ),
    "total_issue_size": ("The total issue size is {v} [1].", "कुल इश्यू {v} का है [1]।"),
    "face_value": (
        "The face value is {v} per equity share [1].",
        "फेस वैल्यू {v} प्रति इक्विटी शेयर है [1]।",
    ),
}
INVENTED = (
    " The company also plans to spend {v} on marketing [1].",
    " कंपनी मार्केटिंग पर {v} खर्च करेगी [1]।",
)
SWAPS = {  # fields whose values can stand in for each other in a sentence
    "fresh_issue_size": ("ofs_amount", "total_issue_size"),
    "ofs_amount": ("fresh_issue_size", "total_issue_size"),
    "total_issue_size": ("fresh_issue_size", "ofs_amount"),
    "offer_price": ("face_value",),
    "face_value": ("offer_price",),
}


@dataclass(frozen=True)
class Base:
    """One gold value with the real passages that state it and its sibling values."""

    ipo_id: str
    split: str
    field_id: str
    amount: Amount
    evidence: list[Passage]


@dataclass(frozen=True)
class Item:
    ipo_id: str
    split: str
    field_id: str
    language: str
    kind: str  # "correct", "rounding_ok" or an error type
    answer: str
    target: int  # index of the number under test in the answer
    evidence: list[Passage]


# ----------------------------------------------------------------------------- writing values
def _unit(amount: Money) -> str:
    return f" {amount.scale_word}" if amount.scale_word else ""


def _number(amount: Money) -> Decimal:
    assert amount.value_inr is not None
    scale = parse_amount(f"₹ 1 {amount.scale_word}") if amount.scale_word else None
    one = scale.value_inr if isinstance(scale, Money) and scale.value_inr else Decimal(1)
    return (amount.value_inr / one).quantize(Decimal(10) ** -amount.precision)


def show(amount: Amount) -> str:
    """The value as an answer would print it: "₹ 26,260 million", "11,051,746 equity shares"."""
    if isinstance(amount, Money):
        indian = amount.scale_word in ("lakh", "crore")
        return f"₹ {group_digits(_number(amount), indian)}{_unit(amount)}"
    if isinstance(amount, Count):
        return f"{amount.value:,} equity shares"
    return amount.raw


def _in_unit(amount: Money, unit: str, decimals: int) -> str:
    assert amount.value_inr is not None
    one = parse_amount(f"₹ 1 {unit}")
    assert isinstance(one, Money)
    assert one.value_inr
    step = Decimal(10) ** -decimals
    value = (amount.value_inr / one.value_inr).quantize(step, rounding=ROUND_HALF_UP)
    return f"₹ {group_digits(value, unit in ('lakh', 'crore'))} {unit}"


def rounded(amount: Amount) -> str | None:
    """The same value in another unit, rounded: must still be ✅ (None when nothing to round)."""
    if isinstance(amount, Money) and amount.scale_word == "million":
        return _in_unit(amount, "crore", 0)
    if isinstance(amount, Money) and amount.scale_word == "crore":
        return _in_unit(amount, "million", 0)
    if isinstance(amount, Count) and amount.value >= 10_000_000:
        crore = (Decimal(amount.value) / Decimal(10_000_000)).quantize(Decimal("0.01"))
        return f"{crore} crore equity shares"
    return None


# ----------------------------------------------------------------------------- corruptions
def scale_lakh_crore(amount: Amount) -> str | None:
    if not isinstance(amount, Money) or amount.scale_word not in ("million", "crore"):
        return None
    crore = _in_unit(amount, "crore", 1 if amount.scale_word == "million" else amount.precision)
    return crore.replace(" crore", " lakh")  # the crore digits, 100x too small


def scale_million_crore(amount: Amount) -> str | None:
    if not isinstance(amount, Money) or amount.scale_word not in ("million", "crore"):
        return None
    other = "crore" if amount.scale_word == "million" else "million"
    return show(amount).replace(f" {amount.scale_word}", f" {other}")  # same digits, 10x apart


def change_digit(amount: Amount, rng: random.Random) -> str | None:
    text = show(amount)
    places = [i for i, ch in enumerate(text) if ch.isdigit()]
    integer_part = [i for i in places if "." not in text[:i]]
    if not integer_part:
        return None
    i = rng.choice(integer_part)
    choices = [d for d in "123456789" if d != text[i]]
    return text[:i] + rng.choice(choices) + text[i + 1 :]


def invent(amount: Amount, evidence: list[Passage], rng: random.Random) -> str | None:
    """A plausible amount that no passage states, in any unit."""
    known = [e.amount for e in evidence_amounts(evidence)]
    for _ in range(50):
        text = f"₹ {rng.randrange(1_103, 9_897):,}.{rng.randrange(1, 9)}7 million"
        made = parse_amount(text)
        assert made is not None
        clash = any(same_value(made, k) for k in known)
        if not clash and verify_answer(f"It is {text}.", evidence).verdicts[0].check.status != (
            "contradicted"
        ):
            return text
    return None


# ----------------------------------------------------------------------------- building items
def _states(passage: Passage, amount: Amount) -> bool:
    return any(same_value(amount, s.amount) for s in parse_amounts(passage.text))


def load_bases(
    gold_rows: list[dict[str, Any]], passages: dict[str, list[Passage]], splits: dict[str, str]
) -> tuple[list[Base], list[str]]:
    """Gold values that a real passage states, with the passages of their sibling fields."""
    found: dict[tuple[str, str], tuple[Amount, Passage]] = {}
    skipped = []
    for row in gold_rows:
        key = (row["ipo_id"], row["field_id"])
        if row["field_id"] not in TEMPLATES or row["status"] != "present":
            continue
        amount = parse_amount(str(row["value_raw"]))
        if not isinstance(amount, Money | Count) or (
            isinstance(amount, Money) and amount.value_inr is None
        ):
            skipped.append(f"{key[0]}:{key[1]} (value not an amount)")
            continue
        doc = "prospectus" if row["doc"] in ("prospectus", "pro") else "rhp"
        on_page = [
            p
            for p in passages.get(row["ipo_id"], [])
            if p.doc_type == doc and p.page_start <= row["page"] <= p.page_end
        ]
        home = next((p for p in on_page if _states(p, amount)), None)
        if home is None:
            skipped.append(f"{key[0]}:{key[1]} (no passage on the gold page states it)")
            continue
        found[key] = (amount, home)
    bases = []
    for (ipo_id, field_id), (amount, home) in found.items():
        evidence = [home]
        for (other_ipo, _), (_, passage) in found.items():
            if other_ipo == ipo_id and passage not in evidence and len(evidence) < MAX_EVIDENCE:
                evidence.append(passage)
        bases.append(Base(ipo_id, splits.get(ipo_id, "test"), field_id, amount, evidence))
    return bases, skipped


def _item(base: Base, lang: int, kind: str, value: str, extra: str = "") -> Item:
    answer = TEMPLATES[base.field_id][lang].format(v=value) + extra
    language = ("en", "hi")[lang]
    return Item(base.ipo_id, base.split, base.field_id, language, kind, answer, 1 if extra else 0,
                base.evidence)  # fmt: skip


def build_items(bases: list[Base], seed: int = SEED) -> list[Item]:
    """Up to ``N_CORRECT`` correct answers and ``N_PER_TYPE`` of each error type, reproducibly."""
    rng = random.Random(seed)
    by_key = {(b.ipo_id, b.field_id): b for b in bases}
    plain = [_item(b, lang, "correct", show(b.amount)) for b in bases for lang in (0, 1)]
    easy = [
        _item(b, lang, "rounding_ok", text)
        for b in bases
        for lang in (0, 1)
        if (text := rounded(b.amount)) is not None
    ]
    rng.shuffle(easy)
    correct = plain[:N_CORRECT] + easy[: max(0, N_CORRECT - len(plain))]

    pools: dict[str, list[Item]] = {t: [] for t in ERROR_TYPES}
    for b in bases:
        for lang in (0, 1):
            for kind, text in (
                ("scale_lakh_crore", scale_lakh_crore(b.amount)),
                ("scale_million_crore", scale_million_crore(b.amount)),
                ("digit", change_digit(b.amount, rng)),
            ):
                if text is not None:
                    pools[kind].append(_item(b, lang, kind, text))
            for other_field in SWAPS.get(b.field_id, ()):
                other = by_key.get((b.ipo_id, other_field))
                if other is not None and not same_value(other.amount, b.amount):
                    pools["swap_metric"].append(_item(b, lang, "swap_metric", show(other.amount)))
            made = invent(b.amount, b.evidence, rng)
            if made is not None:
                extra = INVENTED[lang].format(v=made)
                item = _item(b, lang, "invented", show(b.amount), extra)
                pools["invented"].append(item)
    corrupted = []
    for kind in ERROR_TYPES:
        rng.shuffle(pools[kind])
        corrupted += pools[kind][:N_PER_TYPE]
    return correct + corrupted


# ----------------------------------------------------------------------------- scoring
def _rate(hits: int, n: int) -> dict[str, Any]:
    low, high = wilson_interval(hits, n)
    return {
        "rate": round(hits / n, 4) if n else None,
        "hits": hits,
        "n": n,
        "wilson_95": [round(low, 4), round(high, 4)],
    }


def run_item(item: Item) -> dict[str, Any]:
    verdict = verify_answer(item.answer, item.evidence)
    codes = [v.check.reason_code for v in verdict.verdicts]
    target = codes[item.target] if item.target < len(codes) else "no_number"
    is_correct = item.kind in ("correct", "rounding_ok")
    flagged = any(c != "verified" for c in codes) or not codes
    return {
        "ipo_id": item.ipo_id,
        "split": item.split,
        "field_id": item.field_id,
        "language": item.language,
        "kind": item.kind,
        "answer": item.answer,
        "expected": EXPECTED[item.kind],
        "got": target,
        "all_codes": codes,
        "ok": (not flagged) if is_correct else target != "verified",
        "exact": target == EXPECTED[item.kind],
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    wrong = [r for r in rows if r["kind"] not in ("correct", "rounding_ok")]
    right = [r for r in rows if r["kind"] in ("correct", "rounding_ok")]
    scale = [r for r in wrong if r["kind"].startswith("scale_")]
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_kind[r["kind"]].append(r)
    return {
        "detection": _rate(sum(r["ok"] for r in wrong), len(wrong)),
        "scale_mismatch_recall": _rate(sum(r["exact"] for r in scale), len(scale)),
        "exact_reason": _rate(sum(r["exact"] for r in wrong), len(wrong)),
        "false_alarm": _rate(sum(not r["ok"] for r in right), len(right)),
        "per_type": {
            kind: {
                "n": len(items),
                "ok": sum(r["ok"] for r in items),
                "exact": sum(r["exact"] for r in items),
                "got": dict(Counter(r["got"] for r in items)),
            }
            for kind, items in sorted(by_kind.items())
        },
    }


def _git_sha() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, check=True)  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def report(rows: list[dict[str, Any]], skipped: list[str], n_bases: int) -> dict[str, Any]:
    out: dict[str, Any] = {
        "experiment": "E5",
        "name": "verifier_seeded_errors",
        "seed": SEED,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "data": {
            "gold_version": "v1",
            "n_ipos": len({r["ipo_id"] for r in rows}),
            "n_base_values": n_bases,
            "n_items": len(rows),
            "skipped_gold_values": skipped,
        },
        "metrics": summarise(rows),
        "by_split": {s: summarise([r for r in rows if r["split"] == s]) for s in ("dev", "test")},
        "by_language": {
            lang: summarise([r for r in rows if r["language"] == lang]) for lang in ("en", "hi")
        },
        "misses": [
            {k: r[k] for k in ("ipo_id", "split", "kind", "language", "answer", "expected", "got")}
            for r in rows
            if not r["ok"] or not r["exact"]
        ],
        "first_run": FIRST_RUN,
        "notes": (
            "Unit benchmark: errors are constructed by known rules on templated answers, so high "
            "recall is expected by design. Rules were tuned on the dev IPOs, then one rule was "
            "generalised after the first full run (see first_run and ADR-044)."
        ),
    }
    return out


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.evaluate.seeded_errors")
    parser.add_argument("--split", choices=("dev", "test", "all"), default="all")
    parser.add_argument("--show-misses", action="store_true")
    args = parser.parse_args(argv)
    paths = get_settings().paths
    splits = {i.ipo_id: i.split for i in list_demo_ipos()}
    keep = [i for i, s in splits.items() if args.split in ("all", s)]
    gold_file = paths.gold_dir / "gold_values.jsonl"
    gold = [json.loads(x) for x in gold_file.read_text(encoding="utf-8").splitlines() if x]
    gold = [r for r in gold if r["ipo_id"] in keep]
    passages = {i: IpoIndex.load(index_dir(paths.processed_dir, i)).passages for i in keep}
    bases, skipped = load_bases(gold, passages, splits)
    rows = [run_item(item) for item in build_items(bases)]
    result = report(rows, skipped, len(bases))
    m = result["metrics"]
    for name in ("detection", "scale_mismatch_recall", "exact_reason", "false_alarm"):
        print(f"{name:22} {m[name]['hits']}/{m[name]['n']}  {m[name]['wilson_95']}")
    for kind, row in m["per_type"].items():
        print(f"  {kind:20} n={row['n']:3} ok={row['ok']:3} exact={row['exact']:3} {row['got']}")
    print(f"base values: {len(bases)}; skipped: {len(skipped)}")
    if args.show_misses:
        for miss in result["misses"]:
            print("MISS", json.dumps(miss, ensure_ascii=False))
    if args.split == "all":
        out = Path(paths.eval_dir) / "verifier.json"
        out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                       newline="\n")  # fmt: skip
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
