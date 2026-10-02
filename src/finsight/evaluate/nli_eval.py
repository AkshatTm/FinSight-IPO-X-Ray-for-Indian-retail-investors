"""P5.5: can an NLI model check the claims that carry no number? (inference only)

    uv run python -m finsight.evaluate.nli_eval [--limit N]

Items are built, not collected, like E5 (``evaluate/verifier``): from the gold rows of three name
fields (registrar, promoters, book-running lead managers) the premise is the gold quote, and the
hypothesis is one sentence in English or Hindi that is

- ``entailed``: states a name the quote contains;
- ``contradicted``: states a name taken from another IPO's gold for the same field;
- ``neutral``: states something the quote does not say (a promoter against a registrar quote, a
  registrar against a promoter quote), so the right mark is "unverifiable".

Dev IPOs and test IPOs are scored separately (ADR-026), dev first. High scores are expected by
construction: this measures whether the model can do the easy, templated version of the job, and
says nothing about free LLM text. The model is ``mDeBERTa-v3-base-xnli-multilingual-nli-2mil7``
(MIT, 278 M parameters, Hindi among its 100 languages), run on the laptop only for this
evaluation; it is not loaded by the API and ``verify.nli`` stays off (``deploy_cpu`` too).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from finsight.evaluate.metrics import wilson_interval
from finsight.verify.nli import LABELS, Scorer, decide

MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
FIELDS = ("registrar", "promoters", "book_running_lead_managers")
SENTENCE = {
    "en": {
        "registrar": "The registrar to the offer is {name}.",
        "promoters": "{name} is a promoter of the company.",
        "book_running_lead_managers": "{name} is a book running lead manager of the offer.",
    },
    "hi": {
        "registrar": "ऑफ़र के रजिस्ट्रार {name} हैं।",
        "promoters": "{name} कंपनी के प्रमोटर हैं।",
        "book_running_lead_managers": "{name} इस ऑफ़र के बुक रनिंग लीड मैनेजर हैं।",
    },
}
CROSS = {  # the field whose sentence is NOT supported by this field's quote
    "registrar": "promoters",
    "promoters": "registrar",
    "book_running_lead_managers": "promoters",
}


def names_of(row: dict[str, Any]) -> list[str]:
    value = row["value_raw"]
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def build_items(gold: list[dict[str, Any]], splits: dict[str, str]) -> list[dict[str, Any]]:
    """Seeded items from gold rows (``status == "present"``, one RHP row per IPO and field)."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in gold:
        if row["field_id"] in FIELDS and row["status"] == "present" and row["doc"] == "rhp":
            by_key[(row["ipo_id"], row["field_id"])] = row
    ipos = sorted({ipo for ipo, _ in by_key})
    items: list[dict[str, Any]] = []
    for ipo in ipos:
        for field in FIELDS:
            row = by_key.get((ipo, field))
            if row is None:
                continue
            own = {n.casefold() for n in names_of(row)}
            wrong = _other_name(by_key, ipos, ipo, field, own)
            cross_row = by_key.get((ipo, CROSS[field]))
            cross = names_of(cross_row)[0] if cross_row else None
            for lang in ("en", "hi"):
                make = SENTENCE[lang]
                base = {"ipo_id": ipo, "split": splits[ipo], "field": field, "language": lang}
                prem = row["quote"]
                items.append({**base, "premise": prem, "label": "entailed",
                              "hypothesis": make[field].format(name=names_of(row)[0])})  # fmt: skip
                if wrong:
                    items.append({**base, "premise": prem, "label": "contradicted",
                                  "hypothesis": make[field].format(name=wrong)})  # fmt: skip
                if cross:
                    items.append({**base, "premise": prem, "label": "neutral",
                                  "hypothesis": make[CROSS[field]].format(name=cross)})  # fmt: skip
    return items


def _other_name(
    by_key: dict[tuple[str, str], dict[str, Any]],
    ipos: list[str],
    ipo: str,
    field: str,
    own: set[str],
) -> str | None:
    start = ipos.index(ipo)
    for step in range(1, len(ipos)):
        other = by_key.get((ipos[(start + step) % len(ipos)], field))
        if other is None:
            continue
        for name in names_of(other):
            if name.casefold() not in own:
                return name
    return None


def rate(hits: int, n: int) -> dict[str, Any]:
    low, high = wilson_interval(hits, n)
    return {"rate": round(hits / n, 4) if n else None, "hits": hits, "n": n,
            "wilson_95": [round(low, 4), round(high, 4)]}  # fmt: skip


def score_items(
    items: list[dict[str, Any]], scorer: Scorer, min_prob: float
) -> list[dict[str, Any]]:
    out = []
    for it in items:
        label, prob = decide(scorer(it["premise"], it["hypothesis"]), min_prob)
        out.append({**{k: it[k] for k in ("ipo_id", "split", "field", "language", "label")},
                    "predicted": label, "probability": round(prob, 4),
                    "hypothesis": it["hypothesis"]})  # fmt: skip
    return out


def summarise(scored: list[dict[str, Any]]) -> dict[str, Any]:
    def block(rows: list[dict[str, Any]]) -> dict[str, Any]:
        per_label = {
            lab: rate(sum(r["predicted"] == lab for r in rows if r["label"] == lab),
                      sum(r["label"] == lab for r in rows))
            for lab in LABELS
        }  # fmt: skip
        confusion = Counter((r["label"], r["predicted"]) for r in rows)
        return {
            "accuracy": rate(sum(r["predicted"] == r["label"] for r in rows), len(rows)),
            "recall_by_label": per_label,
            "confusion": {f"{a}->{b}": n for (a, b), n in sorted(confusion.items())},
        }

    out: dict[str, Any] = {}
    for split in ("dev", "test"):  # dev first, then test
        rows = [r for r in scored if r["split"] == split]
        by_lang: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_lang[r["language"]].append(r)
        out[split] = {
            **block(rows),
            "by_language": {k: block(v) for k, v in sorted(by_lang.items())},
        }
    return out


def load_scorer() -> Scorer:
    """The NLI model, fp16 on the GPU when there is one, otherwise float32 on the CPU."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    net = AutoModelForSequenceClassification.from_pretrained(MODEL).eval().to(device)
    if device == "cuda":
        net = net.half()
    names = {int(i): str(n).lower() for i, n in net.config.id2label.items()}
    mapping = {"entailment": "entailed", "contradiction": "contradicted", "neutral": "neutral"}

    def score(premise: str, hypothesis: str) -> dict[str, float]:
        enc = tok(premise, hypothesis, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            logits = net(**{k: v.to(device) for k, v in enc.items()}).logits.float()
        probs = logits.softmax(-1)[0].tolist()
        return {mapping[names[i]]: p for i, p in enumerate(probs)}

    return score


def run(
    gold_path: Path, config_path: Path, scorer: Scorer, min_prob: float,
    limit: int | None = None,
) -> dict[str, Any]:  # fmt: skip
    splits = {
        r["ipo_id"]: r["split"] for r in yaml.safe_load(config_path.read_text("utf-8"))["ipos"]
    }
    gold = [json.loads(x) for x in gold_path.read_text("utf-8").splitlines() if x.strip()]
    items = build_items(gold, splits)
    if limit:
        items = items[:limit]
    scored = score_items(items, scorer, min_prob)
    return {
        "experiment": "P5.5",
        "name": "nli_non_numeric_claims",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": MODEL,
        "min_prob": min_prob,
        "data": {
            "n_items": len(items),
            "label_source": "built from gold quotes (seeded, templated)",
            "fields": list(FIELDS),
            "languages": ["en", "hi"],
        },
        **summarise(scored),
        "misses": [s for s in scored if s["label"] != s["predicted"]],
        "notes": (
            "Seeded, templated items built from the AI-assisted gold quotes (ADR-035): a high "
            "score shows the model can do the easy version of the job, not that it can check "
            "free LLM text. Dev IPOs and test IPOs are reported separately; nothing was tuned "
            "on either."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from finsight.core.config import get_settings

    paths = get_settings().paths
    parser = argparse.ArgumentParser(prog="finsight.evaluate.nli_eval")
    parser.add_argument("--min-prob", type=float, default=0.5)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    result = run(
        Path(paths.gold_dir) / "gold_values.jsonl",
        Path("configs/demo_ipos.yaml"),
        load_scorer(),
        args.min_prob,
        args.limit,
    )
    for split in ("dev", "test"):
        acc = result[split]["accuracy"]
        print(f"{split}: accuracy {acc['hits']}/{acc['n']} {acc['wilson_95']}")
    out = Path(paths.eval_dir) / "nli.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + chr(10), encoding="utf-8",
                   newline=chr(10))  # fmt: skip
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
