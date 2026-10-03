"""Phase 2 profiles, upload limits and the env-key list (B0.3, B-ADR-04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from finsight.core.config import ENV_KEYS, REQUIRED_ENV, load_settings, missing_env

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("FINSIGHT_PROFILE", "UPLOADS_ENABLED", "FINSIGHT_DB__URL", "DEMO_MODE"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.parametrize("profile", ["dev_light", "full", "deploy_cpu", "cloud", "cloud_gpu"])
def test_every_profile_loads(profile: str) -> None:
    s = load_settings(profile)
    assert s.profile == profile
    assert s.uploads.max_mb == 50
    assert s.simplify.auto_top_n == 15


def test_cloud_profile_uses_gcp_backends() -> None:
    s = load_settings("cloud")
    assert s.storage.backend == "gcs"
    assert s.db.backend == "postgres"
    assert s.auth.mode == "supabase"
    assert s.jobs.runner == "cloud_run"
    assert s.jobs.gpu_job is False
    assert s.simplify.backend == "llama-cpp"
    assert s.db.url is None  # secrets never come from the YAML


def test_cloud_gpu_profile_uses_the_gpu_job() -> None:
    s = load_settings("cloud_gpu")
    assert s.jobs.gpu_job is True
    assert s.simplify.backend == "vllm"


def test_laptop_profiles_stay_local() -> None:
    s = load_settings("dev_light")
    assert (s.storage.backend, s.db.backend, s.auth.mode, s.jobs.runner) == (
        "local",
        "sqlite",
        "off",
        "inline",
    )


@pytest.mark.parametrize(
    ("value", "enabled"), [("false", False), ("0", False), ("off", False), ("true", True)]
)
def test_uploads_kill_switch(monkeypatch: pytest.MonkeyPatch, value: str, enabled: bool) -> None:
    monkeypatch.setenv("UPLOADS_ENABLED", value)
    assert load_settings("cloud").uploads.enabled is enabled


def test_db_url_comes_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSIGHT_DB__URL", "postgresql://example")
    assert load_settings("cloud").db.url == "postgresql://example"


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


def test_missing_env_reports_names_only() -> None:
    env = {"FINSIGHT_DB__URL": "x", "GCP_PROJECT": "p"}
    missing = missing_env("cloud", env)
    assert "FINSIGHT_DB__URL" not in missing
    assert "FINSIGHT_STORAGE__BUCKET" in missing
    assert missing_env("dev_light", {}) == []
