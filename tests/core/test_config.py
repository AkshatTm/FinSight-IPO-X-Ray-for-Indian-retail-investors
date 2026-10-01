from pathlib import Path

import pytest
from pydantic import ValidationError

from finsight.core import config
from finsight.core.config import Settings, load_settings

YAML = """
paths: {data_dir: data, processed_dir: data/processed, models_dir: models, eval_dir: eval_results}
profiles:
  dev_light:
    llm: {backend: ollama, model: tiny, num_ctx: 1024}
    retrieve: {dense: false, rerank: false}
    voice: {asr: "off"}
    verify: {nli: false}
    demo_mode: false
  full:
    llm: {backend: ollama, model: bigger, num_ctx: 2048}
    retrieve: {dense: true, rerank: true}
    voice: {asr: whisper}
    verify: {nli: false}
    demo_mode: false
"""


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(YAML, encoding="utf-8")
    for var in ("FINSIGHT_PROFILE", "DEMO_MODE", "FINSIGHT_LLM__MODEL", "FINSIGHT_ROOT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("FINSIGHT_ROOT", str(tmp_path))
    return path


def test_default_profile_is_dev_light(cfg: Path) -> None:
    s = load_settings(config_path=cfg)
    assert s.profile == "dev_light"
    assert s.llm.model == "tiny"
    assert s.retrieve.dense is False


def test_explicit_profile_argument(cfg: Path) -> None:
    s = load_settings("full", config_path=cfg)
    assert s.profile == "full"
    assert s.llm.model == "bigger"
    assert s.retrieve.rerank is True


def test_env_profile_selects_profile(cfg: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSIGHT_PROFILE", "full")
    assert load_settings(config_path=cfg).profile == "full"


def test_unknown_profile_lists_choices(cfg: Path) -> None:
    with pytest.raises(ValueError, match="dev_light"):
        load_settings("nope", config_path=cfg)


def test_env_overrides_yaml_including_nested(cfg: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSIGHT_LLM__MODEL", "from-env")
    s = load_settings(config_path=cfg)
    assert s.llm.model == "from-env"
    assert s.llm.backend == "ollama"  # untouched siblings survive the merge


def test_demo_mode_env_alias(cfg: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert load_settings(config_path=cfg).demo_mode is False
    monkeypatch.setenv("DEMO_MODE", "1")
    assert load_settings(config_path=cfg).demo_mode is True


def test_paths_resolve_under_root(cfg: Path, tmp_path: Path) -> None:
    s = load_settings(config_path=cfg)
    assert s.paths.data_dir == (tmp_path / "data").resolve()
    assert s.paths.processed_dir.is_absolute()
    assert s.paths.raw_dir == s.paths.data_dir / "raw"


def test_thinking_mode_cannot_be_enabled() -> None:
    # ADR-032: small models always run with thinking off.
    with pytest.raises(ValidationError):
        Settings.model_validate({"llm": {"think": True}})
    assert Settings().llm.think is False


def test_get_settings_is_cached(cfg: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSIGHT_CONFIG", str(cfg))
    config.reset_settings()
    assert config.get_settings() is config.get_settings()
    config.reset_settings()


@pytest.mark.parametrize("profile", ["dev_light", "full", "deploy_cpu"])
def test_repo_config_loads_every_profile(profile: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FINSIGHT_ROOT", raising=False)
    monkeypatch.delenv("FINSIGHT_LLM__MODEL", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    s = load_settings(profile)
    assert s.profile == profile
    assert s.llm.think is False


def test_full_profile_carries_the_dev_tuned_abstain_threshold() -> None:
    from finsight.core.config import load_settings

    thresholds = load_settings("full").retrieve.abstain_thresholds
    assert set(thresholds) == {"hybrid+rerank"}
    assert load_settings("dev_light").retrieve.abstain_thresholds == {}
