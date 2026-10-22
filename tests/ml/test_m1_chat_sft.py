# ruff: noqa: E501
"""Tests for M1 chat SFT builder (`ml/m1_student_v2/chat_sft_builder.py`) and `ml/notebooks/m1_teacher_gen.ipynb`."""

from __future__ import annotations

import ast
import gzip
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.m1_student_v2.chat_sft_builder import (  # noqa: E402
    ABSTAIN_EN,
    ABSTAIN_HI,
    build_scripted_near_miss_unanswerables,
    filter_teacher_chat_rows,
    mix_rewrite_and_chat_sft,
    render_chat_prompt,
)

BUILDER_PATH = ROOT / "ml" / "m1_student_v2" / "chat_sft_builder.py"
NB_PATH = ROOT / "ml" / "notebooks" / "m1_teacher_gen.ipynb"
HANDOFF_DATA = ROOT / "ml" / "handoff" / "data"


def test_m1_builder_no_product_imports_and_frozen_templates() -> None:
    tree = ast.parse(BUILDER_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("finsight."), f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("finsight."), f"Forbidden import: {node.module}"

    passages = [
        {
            "page": 72,
            "doc_type": "RHP",
            "text": "In Fiscal 2024, our revenue from operations was ₹ 4,720.00 million.",
        },
        {
            "page": 73,
            "doc_type": "RHP",
            "text": "Our restated profit after tax was ₹ 512.40 million in Fiscal 2024.",
        },
    ]
    prompt_en = render_chat_prompt(
        "What was the revenue from operations in Fiscal 2024?", passages, lang="en"
    )
    assert "<<<DATA\n[1] (RHP page 72)\nIn Fiscal 2024" in prompt_en
    assert "\n\n[2] (RHP page 73)\nOur restated profit" in prompt_en
    assert prompt_en.count("Question: What was the revenue from operations in Fiscal 2024?") == 2
    assert prompt_en.endswith("Answer:")
    assert ABSTAIN_EN in prompt_en

    prompt_hi = render_chat_prompt("वित्तीय वर्ष 2024 में परिचालन से राजस्व क्या था?", passages, lang="hi")
    assert prompt_hi.count("प्रश्न: वित्तीय वर्ष 2024 में परिचालन से राजस्व क्या था?") == 2
    assert prompt_hi.endswith("उत्तर:")
    assert ABSTAIN_HI in prompt_hi


def test_scripted_near_miss_unanswerables_zero_leakage() -> None:
    excluded_obj = json.loads((HANDOFF_DATA / "excluded_ipos.json").read_text(encoding="utf-8"))
    excluded_set = set(excluded_obj["ipos"].keys())

    with gzip.open(HANDOFF_DATA / "classifier_dev.jsonl.gz", "rt", encoding="utf-8") as f:
        dev_rows = [json.loads(line) for line in f if line.strip()]
    for r in dev_rows:
        r["split"] = "dev"

    scripted = build_scripted_near_miss_unanswerables(
        risk_rows=dev_rows,
        excluded_ipos=excluded_set,
        target_count=40,
        seed=42,
    )
    assert len(scripted) == 40
    langs = {r["lang"] for r in scripted}
    assert "en" in langs
    assert "hi" in langs

    for r in scripted:
        assert r["ipo_id"] not in excluded_set
        assert r["label_source"] == "rule"
        assert r["task_type"] == "chat_unanswerable_scripted"
        expected_abstain = ABSTAIN_HI if r["lang"] == "hi" else ABSTAIN_EN
        assert r["answer"] == expected_abstain
        assert r["messages"][1]["content"] == expected_abstain
        assert "<<<DATA\n[1] (RHP page " in r["messages"][0]["content"]


def test_numkeep_filter_and_mixer() -> None:
    excluded_set = {"jio-platforms-2026", "groww-2025"}
    raw_teacher = [
        {
            "id": "t_ok_1",
            "ipo_id": "adani-wilmar-2022",
            "company": "Adani Wilmar Limited",
            "split": "train",
            "task_type": "chat_answerable_teacher",
            "lang": "en",
            "question": "How much does the company plan to invest from Net Proceeds in food processing capacities?",
            "passage_objs": [
                {
                    "page": 72,
                    "doc_type": "RHP",
                    "text": "We plan to invest approximately ₹19,000 million from the Net Proceeds as capital expenditure for expanding our food processing capacities across India.",
                }
            ],
            "answer": "The company plans to invest approximately ₹19,000 million from the Net Proceeds to expand its food processing capacities across India [1].",
        },
        {
            "id": "t_bad_num",
            "ipo_id": "adani-wilmar-2022",
            "company": "Adani Wilmar Limited",
            "split": "train",
            "task_type": "chat_answerable_teacher",
            "lang": "en",
            "question": "How much does the company plan to invest?",
            "passage_objs": [
                {
                    "page": 72,
                    "doc_type": "RHP",
                    "text": "We plan to invest approximately ₹19,000 million from the Net Proceeds.",
                }
            ],
            "answer": "The company plans to invest ₹24,500 million from the Net Proceeds [1].",
        },
        {
            "id": "t_bad_no_cite",
            "ipo_id": "adani-wilmar-2022",
            "company": "Adani Wilmar Limited",
            "split": "train",
            "task_type": "chat_answerable_teacher",
            "lang": "en",
            "question": "How much does the company plan to invest?",
            "passage_objs": [
                {
                    "page": 72,
                    "doc_type": "RHP",
                    "text": "We plan to invest approximately ₹19,000 million from the Net Proceeds.",
                }
            ],
            "answer": "The company plans to invest approximately ₹19,000 million from the Net Proceeds.",
        },
        {
            "id": "t_ok_unans",
            "ipo_id": "adani-wilmar-2022",
            "company": "Adani Wilmar Limited",
            "split": "dev",
            "task_type": "chat_unanswerable_teacher",
            "lang": "en",
            "question": "What was the company's RoNW in Fiscal 2015?",
            "passage_objs": [
                {
                    "page": 72,
                    "doc_type": "RHP",
                    "text": "We plan to invest approximately ₹19,000 million from the Net Proceeds.",
                }
            ],
            "answer": ABSTAIN_EN,
        },
    ]

    kept, rejected, stats = filter_teacher_chat_rows(raw_teacher, excluded_ipos=excluded_set)
    assert len(kept) == 2
    assert len(rejected) == 2
    assert stats["reasons"]["unmatched_numbers"] == 1
    assert stats["reasons"]["missing_citation"] == 1

    rw_train = [
        {
            "ipo_id": "adani-wilmar-2022",
            "label_source": "ai",
            "messages": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}],
        }
    ]
    rw_dev = [
        {
            "ipo_id": "adani-wilmar-2022",
            "label_source": "ai",
            "messages": [{"role": "user", "content": "x2"}, {"role": "assistant", "content": "y2"}],
        }
    ]
    c_train, c_dev, mix_stats = mix_rewrite_and_chat_sft(rw_train, rw_dev, kept, excluded_set)
    assert len(c_train) == 2
    assert len(c_dev) == 2
    assert mix_stats["chat_train"] == 1
    assert mix_stats["chat_dev"] == 1


def test_m1_teacher_gen_notebook_structure() -> None:
    assert NB_PATH.exists(), "ml/notebooks/m1_teacher_gen.ipynb must exist"
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    cells = nb["cells"]
    assert len(cells) >= 4

    header_src = "".join(cells[0]["source"])
    assert "DEBUG = True" in header_src
    assert "13.07 G4 units" in header_src

    all_code = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
    for c in cells:
        if c["cell_type"] == "code":
            ast.parse("".join(c["source"]))
    assert 'JOB = "m1_teacher_gen"' in all_code
    assert "DEBUG = True" in all_code
    assert "SEEDS = [13, 42, 2026]" in all_code
    assert "RESUME = True" in all_code
    assert 'HF_REVISION = "a285902d91a5557cf6d6d7cf23a9e266410d6c3d"' in all_code
    assert 'HF_PACK_REVISION = "af028c61cde3f0aee6e52fc40593ac47b2a7aa1b"' in all_code
    assert "git clone" not in all_code
    assert "numkeep.py" in all_code
    assert "excluded_ipos.json" in all_code
