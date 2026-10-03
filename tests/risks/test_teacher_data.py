import csv
import json
from pathlib import Path

from finsight.risks.teacher_data import (
    SHEET_COLUMNS,
    filter_file,
    main,
    original_text,
    quality_sheet,
    write_outputs,
    write_sheet,
)

BODY = "Our top ten customers contributed 62.48% of revenue in Fiscal 2024. Losing one may hurt us."


def answer(simple: str, category: str = "customers_suppliers") -> str:
    return json.dumps(
        {
            "category": category,
            "seriousness_1to5": 3,
            "hard_fact": False,
            "simple": simple,
            "numbers_copied": [],
        }
    )


def setup(tmp_path: Path, n: int = 6) -> tuple[Path, Path]:
    risks, raw = tmp_path / "risks.jsonl", tmp_path / "raw.jsonl"
    with risks.open("w", encoding="utf-8") as r, raw.open("w", encoding="utf-8") as a:
        for i in range(n):
            r.write(
                json.dumps(
                    {
                        "risk_id": f"r{i}",
                        "company": f"Co {i % 2}",
                        "title": "Customers",
                        "body": BODY,
                    }
                )
                + "\n"
            )
            simple = f"Customer {chr(65 + i)}: ten customers gave 62.48% of revenue; one may go."
            a.write(
                json.dumps(
                    {
                        "risk_id": f"r{i}",
                        "raw": answer(simple),
                        "model": "qwen-test",
                        "prompt_version": "teacher-v1",
                    }
                )
                + "\n"
            )
        a.write(json.dumps({"risk_id": "r0x", "raw": answer("unknown risk")}) + "\n")
        a.write(json.dumps({"risk_id": "r1", "raw": answer("It gave 99% of revenue.")}) + "\n")
    return risks, raw


def test_original_text_matches_the_prompt_layout() -> None:
    assert original_text({"title": "T", "body": " b "}) == "Title: T\n\nb"
    assert original_text({"title": None, "body": "b"}) == "b"


def test_filter_and_write_outputs(tmp_path: Path) -> None:
    risks, raw = setup(tmp_path)
    report, meta = filter_file(risks, raw)
    assert len(report.kept) == 6
    assert report.counts["number_mismatch"] == 1  # the second r1 answer; the unknown id is skipped
    paths = write_outputs(report, meta, risks, tmp_path / "out")
    labels = [json.loads(x) for x in paths["labels"].read_text(encoding="utf-8").splitlines()]
    assert labels[0]["label_source"] == "teacher:qwen-test:teacher-v1"
    assert labels[1]["company"] == "Co 1"
    simple = json.loads(paths["simplify"].read_text(encoding="utf-8").splitlines()[0])
    assert simple["original"].startswith("Title: Customers")
    assert json.loads(paths["report"].read_text(encoding="utf-8"))["kept"] == 6


def test_quality_sheet_is_seeded_with_blank_ratings(tmp_path: Path) -> None:
    risks, raw = setup(tmp_path, n=12)
    report, meta = filter_file(risks, raw)
    a = quality_sheet(report.kept, {}, meta, n=5)
    b = quality_sheet(report.kept, {}, meta, n=5)
    assert [r["risk_id"] for r in a] == [r["risk_id"] for r in b]
    assert len(a) == 5
    assert all(r["faithful"] == r["category_correct"] == "" for r in a)
    write_sheet(a, tmp_path / "sheet.csv")
    with (tmp_path / "sheet.csv").open(encoding="utf-8") as f:
        assert tuple(csv.DictReader(f).fieldnames or ()) == SHEET_COLUMNS


def test_cli_filter_and_sheet(tmp_path: Path) -> None:
    setup(tmp_path)
    main(["filter", "--dir", str(tmp_path)])
    main(["sheet", "--dir", str(tmp_path), "-n", "3"])
    assert (tmp_path / "labels.jsonl").exists()
    with (tmp_path / "quality_sheet.csv").open(encoding="utf-8", newline="") as f:
        assert len(list(csv.DictReader(f))) == 3
