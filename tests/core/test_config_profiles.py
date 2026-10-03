"""Phase 2 profiles, upload limits and the env-key list (B0.3, B-ADR-16)."""

from __future__ import annotations

from pathlib import Path

import pytest

from finsight.core.config import ENV_KEYS, REQUIRED_ENV, load_settings, missing_env

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("FINSIGHT_PROFILE", "UPLOADS_ENABLED", "FINSIGHT_DB__URL", "DEMO_MODE"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.parametrize("profile", ["dev_light", "full", "deploy_cpu"])
def test_every_profile_loads(profile: str) -> None:
    s = load_settings(profile)
    assert s.profile == profile
    assert s.uploads.max_mb == 50
    assert s.simplify.auto_top_n == 15


def test_google_cloud_profiles_are_gone() -> None:
    for profile in ("cloud", "cloud_gpu"):
        with pytest.raises(ValueError, match="Unknown profile"):
            load_settings(profile)


def test_laptop_profiles_stay_local() -> None:
    s = load_settings("dev_light")
    assert (s.storage.backend, s.db.backend, s.auth.mode) == ("local", "sqlite", "off")


@pytest.mark.parametrize(
    ("value", "enabled"), [("false", False), ("0", False), ("off", False), ("true", True)]
)
def test_uploads_kill_switch(monkeypatch: pytest.MonkeyPatch, value: str, enabled: bool) -> None:
    monkeypatch.setenv("UPLOADS_ENABLED", value)
    assert load_settings("full").uploads.enabled is enabled


def test_db_url_comes_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSIGHT_DB__URL", "postgresql://example")
    assert load_settings("full").db.url == "postgresql://example"


def test_env_example_lists_exactly_the_env_keys() -> None:
    names = {
        line.split("=", 1)[0].strip()
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert names == set(ENV_KEYS)


def test_required_env_is_a_subset_of_env_keys() -> None:
    for names in REQUIRED_ENV.values():
        assert set(names) <= set(ENV_KEYS)


def test_local_profiles_need_no_env() -> None:
    assert missing_env("dev_light", {}) == []
    assert missing_env("full", {}) == []
