"""B4.1 groundwork: the generated reference pages match their sources (docs as code, B09 §9)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("docs_gen", ROOT / "scripts" / "docs_gen.py")
assert SPEC is not None
assert SPEC.loader is not None
docs_gen = importlib.util.module_from_spec(SPEC)
sys.modules["docs_gen"] = docs_gen
SPEC.loader.exec_module(docs_gen)


def test_committed_pages_are_current() -> None:
    assert docs_gen.stale() == [], "run `uv run poe docs-gen` and commit the pages"


def test_config_page_lists_every_env_key_and_profile() -> None:
    page = docs_gen.config_page()
    from finsight.core.config import ENV_KEYS

    for key in ENV_KEYS:
        assert f"`{key}`" in page
    profiles = yaml.safe_load((ROOT / "configs" / "config.yaml").read_text(encoding="utf-8"))
    for name in profiles["profiles"]:
        assert f"### `{name}`" in page
    assert "| `llm.model` | str | `qwen3.5:0.8b` | `FINSIGHT_LLM__MODEL` |" in page
    assert "`DEMO_MODE`" in page


def test_provisional_configs_are_flagged_on_their_pages() -> None:
    for make, name in ((docs_gen.risklevel_page, "risklevel"), (docs_gen.compare_page, "compare")):
        cfg = yaml.safe_load((ROOT / "configs" / f"{name}.yaml").read_text(encoding="utf-8"))
        assert ('!!! warning "Provisional"' in make()) is bool(cfg["provisional"])


def test_adr_index_has_every_decision() -> None:
    headings = [
        line
        for rel in (
            "docs/09_DECISIONS.md",
            "docs/phase2/B08_DECISIONS.md",
            "docs/phase3/C_DECISIONS.md",
        )
        for line in (ROOT / rel).read_text(encoding="utf-8").splitlines()
        if docs_gen.ADR_HEADING.match(line)
    ]
    rows = [
        line
        for line in docs_gen.adr_page().splitlines()
        if line.startswith(("| ADR-", "| B-ADR-", "| C-ADR-"))
    ]
    assert len(headings) > 80
    assert "## Phase 3" in docs_gen.adr_page()
    assert len(rows) == len(headings)


def test_cli_page_lists_every_poe_task() -> None:
    import tomllib

    tasks = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["poe"][
        "tasks"
    ]
    page = docs_gen.cli_page()
    for name in tasks:
        assert f"| `{name}` |" in page


def test_mkdocs_nav_points_at_files_that_exist() -> None:
    class Loader(yaml.SafeLoader):
        pass

    Loader.add_multi_constructor("tag:yaml.org,2002:python/", lambda *_: None)
    cfg = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=Loader)

    def pages(node: object) -> list[str]:
        if isinstance(node, str):
            return [node]
        if isinstance(node, list):
            return [p for item in node for p in pages(item)]
        if isinstance(node, dict):
            return [p for value in node.values() for p in pages(value)]
        return []

    root_pages = {"changelog.md": "CHANGELOG.md", "contributing.md": "CONTRIBUTING.md"}
    root_pages |= {"security.md": "SECURITY.md", "privacy.md": "PRIVACY.md"}
    nav = pages(cfg["nav"])
    assert nav
    missing = [
        p
        for p in nav
        if not (ROOT / "docs" / p).exists() and not (ROOT / root_pages.get(p, "-")).exists()
    ]
    assert missing == []
    hooks = (ROOT / "scripts" / "mkdocs_hooks.py").read_text(encoding="utf-8")
    for page, source in root_pages.items():
        assert f'"{page}": "{source}"' in hooks


def test_glossary_has_every_term_with_its_hindi() -> None:
    page = docs_gen.glossary_page()
    finance = yaml.safe_load((ROOT / "configs" / "glossary.yaml").read_text(encoding="utf-8"))
    ml = yaml.safe_load((ROOT / "configs" / "glossary_ml.yaml").read_text(encoding="utf-8"))
    for term in finance["terms"]:
        assert f"| {term['title']['en']} |" in page
        assert term["title"]["hi"] in page
    for term in ml["terms"]:
        assert f"| {term['term']} |" in page


def test_data_formats_list_schema_fields_and_every_gold_file() -> None:
    from finsight.core.schemas import DocRecord, Risk

    page = docs_gen.data_formats_page()
    for model in (DocRecord, Risk):
        for name in model.model_fields:
            assert f"| `{name}` |" in page
    for path in (ROOT / "data" / "gold").glob("*.jsonl"):
        assert f"| `{path.name}` |" in page


def test_experiment_registry_covers_e1_to_e24_and_only_real_files() -> None:
    found = {e["id"]: e for e in docs_gen.experiments()}
    assert {f"E{i}" for i in range(1, 25)} <= set(found)
    assert found["E1"]["found"] == ["weaklabel_audit.json"]
    assert "e7.json" in found["E7"]["found"]
    for e in found.values():
        for name in e["found"]:
            assert (ROOT / "eval_results" / name).exists()


def test_fill_blocks_rewrites_only_between_markers() -> None:
    text = "intro\n<!-- generated:x start -->\nold\n<!-- generated:x end -->\nkept\n"
    out = docs_gen.fill_blocks(text, {"x": lambda: "new"})
    assert out == "intro\n<!-- generated:x start -->\n\nnew\n\n<!-- generated:x end -->\nkept\n"
    assert docs_gen.fill_blocks(out, {"x": lambda: "new"}) == out


def test_fill_blocks_refuses_a_page_without_markers() -> None:
    import pytest

    with pytest.raises(ValueError, match="generated:x"):
        docs_gen.fill_blocks("no markers", {"x": lambda: "new"})


def test_model_cards_quote_every_seed_from_the_result_files() -> None:
    import json

    card = (ROOT / "docs" / "model_cards" / "extractor_qa.md").read_text(encoding="utf-8")
    for path in (ROOT / "eval_results").glob("extractor_metrics-*.json"):
        run = json.loads(path.read_text(encoding="utf-8"))
        assert f"| {run['seed']} |" in card
        assert f"{run['EM']:.3f}" in card


def test_teacher_block_reads_the_quality_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(docs_gen, "ROOT", tmp_path)
    assert "No teacher run" in docs_gen._teacher_block()
    (tmp_path / "eval_results").mkdir()
    (tmp_path / "eval_results" / "teacher_quality.json").write_text(
        '{"model": "Qwen/Qwen3-14B-AWQ", "prompt_version": "teacher-v1", "n_rated": 100,'
        ' "faithful": {"yes": 90, "partly": 7, "no": 3}, "faithful_yes_share": 0.9,'
        ' "faithful_yes_ci95": [0.83, 0.94], "category_correct_share": 0.88, "gate": 0.85,'
        ' "go": true, "rated_by": "human:akshat (single annotator)",'
        ' "filter": {"kept": 11000, "total": 12000, "dropped": {"invalid_json": 5}}}',
        encoding="utf-8",
    )
    block = docs_gen._teacher_block()
    assert "90.0%" in block
    assert "**go**" in block
    assert "kept 11000" not in block  # formatted as "11000 kept of 12000"
    assert "11000 kept of 12000" in block


def test_classifier_block_reads_the_summary(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(docs_gen, "ROOT", tmp_path)
    assert "not been trained" in docs_gen._classifier_block()
    (tmp_path / "eval_results" / "b").mkdir(parents=True)
    (tmp_path / "eval_results" / "b" / "classifier_base.json").write_text(
        '{"model": "deberta", "n_train": 900, "n_dev": 100, "dev_macro_f1_by_seed": {"13": 0.7},'
        ' "dev_macro_f1_mean": 0.7, "dev_macro_f1_sd": null, "best_seed": 13,'
        ' "label_source": "teacher (AI labels)", "tfidf_dev_macro_f1": 0.6, "beats_tfidf": true}',
        encoding="utf-8",
    )
    block = docs_gen._classifier_block()
    assert "| 13 | 0.700 |" in block
    assert "n/a (one seed)" in block
    assert "beats the TF-IDF baseline (0.600)" in block
