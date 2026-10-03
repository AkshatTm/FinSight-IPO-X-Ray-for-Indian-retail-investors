import json
import random
from pathlib import Path

import pytest

from finsight.risks.classify import (
    Example,
    TfidfBaseline,
    evaluate,
    load_examples,
    main,
    predict,
    split_by_company,
    write_split,
)
from finsight.risks.clf_metrics import company_bucket, scores
from finsight.risks.teacher import CATEGORIES

WORDS = {
    "financial": "losses revenue margins profit decline",
    "debt_liquidity": "borrowings loans repayment covenants lenders",
    "customers_suppliers": "customers suppliers distributors dependence concentration",
    "competition": "competitors pricing market share rivals",
    "legal_litigation": "litigation court proceedings claims penalties",
    "regulatory": "regulations licences approvals sebi policy",
    "promoters_governance": "promoters related party management control conflicts",
    "operations": "plants capacity manufacturing disruption insurance",
    "technology_data": "cyber security data systems technology",
    "market_macro": "economy inflation currency listing volatility",
}
FILLER = [
    "our",
    "company",
    "the",
    "business",
    "may",
    "be",
    "adversely",
    "affected",
    "and",
    "results",
    "of",
    "operations",
]


def fake_set(n_per_class: int = 30, seed: int = 1) -> list[Example]:
    rng = random.Random(seed)
    out = []
    for label, words in WORDS.items():
        vocab = words.split()
        for i in range(n_per_class):
            text = " ".join(rng.choices(vocab, k=4) + rng.choices(FILLER, k=8))
            out.append(Example(f"{label}-{i}", f"Company {label} {i}", text, label))
    return out


# ------------------------------------------------------------------ metrics
def test_scores_macro_f1_and_confusion() -> None:
    s = scores(["a", "a", "b", "b"], ["a", "b", "b", "b"], ["a", "b", "c"])
    assert s["accuracy"] == 0.75
    assert s["per_class"]["a"]["f1"] == pytest.approx(2 / 3)
    assert s["per_class"]["b"]["f1"] == pytest.approx(0.8)
    assert "c" not in s["per_class"]  # no support, never predicted
    assert s["macro_f1"] == pytest.approx((2 / 3 + 0.8) / 2)
    assert s["confusion"] == [[1, 1, 0], [0, 2, 0], [0, 0, 0]]
    with pytest.raises(ValueError, match="length"):
        scores(["a"], [], ["a"])


def test_company_bucket_is_stable_and_case_blind() -> None:
    assert company_bucket("Acme Ltd") == company_bucket(" acme ltd ")
    assert 0 <= company_bucket("x") < 1
    assert company_bucket("x", seed=1) != company_bucket("x", seed=2)


# ------------------------------------------------------------------ split
def test_split_keeps_each_company_on_one_side() -> None:
    examples = [Example(f"r{i}", f"Co {i % 40}", "t", "financial") for i in range(400)]
    train, dev = split_by_company(examples)
    assert not {e.company for e in train} & {e.company for e in dev}
    assert 0 < len(dev) < len(train)


def test_load_examples_and_write_split(tmp_path: Path) -> None:
    (tmp_path / "risks.jsonl").write_text(
        json.dumps({"risk_id": "r1", "company": "A", "title": "T", "body": "b"})
        + "\n"
        + json.dumps({"risk_id": "r2", "company": "B", "title": "", "body": "c"})
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "labels.jsonl").write_text(
        json.dumps({"risk_id": "r1", "category": "financial"})
        + "\n"
        + json.dumps({"risk_id": "r2", "category": "weather"})
        + "\n"
        + json.dumps({"risk_id": "r9", "category": "financial"})
        + "\n",
        encoding="utf-8",
    )
    ex = load_examples(tmp_path / "labels.jsonl", tmp_path / "risks.jsonl")
    assert ex == [Example("r1", "A", "Title: T\n\nb", "financial")]
    folder = write_split(ex, [], tmp_path / "split")
    assert json.loads((folder / "labels.json").read_text()) == list(CATEGORIES)
    assert json.loads((folder / "train.jsonl").read_text())["risk_id"] == "r1"


# ------------------------------------------------------------------ baseline
def test_baseline_learns_the_fake_set_and_round_trips(tmp_path: Path) -> None:
    clf = TfidfBaseline().fit([e.text for e in fake_set()], [e.label for e in fake_set()])
    held_out = fake_set(n_per_class=10, seed=99)
    result = evaluate(clf, held_out)
    assert result["macro_f1"] > 0.9
    probs = clf.predict_proba([held_out[0].text])[0]
    assert len(probs) == len(CATEGORIES)
    assert sum(probs) == pytest.approx(1.0)
    clf.save(tmp_path / "m.joblib")
    again = TfidfBaseline.load(tmp_path / "m.joblib")
    assert predict(again, [held_out[0].text]) == predict(clf, [held_out[0].text])


def test_empty_set_scores_zero() -> None:
    clf = TfidfBaseline().fit([e.text for e in fake_set()], [e.label for e in fake_set()])
    assert evaluate(clf, [])["n"] == 0


def test_unseen_class_gets_probability_zero() -> None:
    train = [e for e in fake_set() if e.label != "market_macro"]
    clf = TfidfBaseline().fit([e.text for e in train], [e.label for e in train])
    probs = clf.predict_proba(["economy inflation currency"])[0]
    assert probs[list(CATEGORIES).index("market_macro")] == 0.0


def test_cli_split_then_baseline(tmp_path: Path) -> None:
    teacher = tmp_path / "teacher"
    teacher.mkdir()
    examples = fake_set()
    with (teacher / "risks.jsonl").open("w") as r, (teacher / "labels.jsonl").open("w") as lab:
        for e in examples:
            r.write(json.dumps({"risk_id": e.risk_id, "company": e.company, "body": e.text}) + "\n")
            lab.write(json.dumps({"risk_id": e.risk_id, "category": e.label}) + "\n")
    split = tmp_path / "split"
    main(["split", "--teacher-dir", str(teacher), "--split-dir", str(split)])
    out = tmp_path / "b" / "classifier_tfidf.json"
    main(
        [
            "baseline",
            "--split-dir",
            str(split),
            "--out",
            str(out),
            "--model-out",
            str(tmp_path / "m.joblib"),
            "--gold",
            str(split / "dev.jsonl"),
        ]
    )
    result = json.loads(out.read_text())
    assert result["model"] == "tfidf-logreg"
    assert result["dev"]["macro_f1"] == result["gold"]["macro_f1"]
