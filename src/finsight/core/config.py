"""Profile-based settings (02_ARCHITECTURE.md section 8).

``configs/config.yaml`` holds shared ``paths`` and one block per profile
(``dev_light`` default, ``full``, ``deploy_cpu``). Environment variables win over
the YAML: ``FINSIGHT_PROFILE`` picks the profile, ``FINSIGHT_LLM__MODEL=...`` overrides
a nested value, ``DEMO_MODE=1`` turns demo mode on. Code reads paths from here and
uses ``pathlib`` only.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

DEFAULT_PROFILE = "dev_light"


class Paths(BaseModel):
    data_dir: Path = Path("data")
    processed_dir: Path = Path("data/processed")
    models_dir: Path = Path("models")
    eval_dir: Path = Path("eval_results")

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def samples_dir(self) -> Path:
        return self.data_dir / "samples"

    @property
    def gold_dir(self) -> Path:
        return self.data_dir / "gold"


class LLMConfig(BaseModel):
    backend: str = "ollama"
    model: str = "qwen3.5:0.8b"
    num_ctx: int = 2048
    # ADR-032: thinking mode is always off for the small models; config cannot enable it.
    think: Literal[False] = False


class RetrieveConfig(BaseModel):
    dense: bool = False
    rerank: bool = False
    rerank_top_n: int = 20
    final_top_k: int = 5
    # Abstain below this top score, per retrieval method (the score scales differ). Tuned on the
    # 50 dev questions only (ADR-049); a method without an entry never abstains on score.
    abstain_thresholds: dict[str, float] = Field(default_factory=dict)


class VoiceConfig(BaseModel):
    asr: str = "off"
    idle_unload_s: int = 120


class VerifyConfig(BaseModel):
    nli: bool = False


class GuardConfig(BaseModel):
    # keyword = rules (ADR-046); muril = fine-tuned classifier (P5.4). Privacy is always rules.
    backend: Literal["keyword", "muril"] = "keyword"
    threshold: float = 0.5  # probability of "advice" at or above which the classifier blocks


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FINSIGHT_", env_nested_delimiter="__", extra="ignore"
    )

    profile: str = DEFAULT_PROFILE
    root: Path = Path(".")
    paths: Paths = Field(default_factory=Paths)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    retrieve: RetrieveConfig = Field(default_factory=RetrieveConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
    guard: GuardConfig = Field(default_factory=GuardConfig)
    demo_mode: bool = Field(default=False, validation_alias=AliasChoices("DEMO_MODE", "demo_mode"))

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Earlier sources win: environment beats the YAML values passed as init kwargs.
        return (env_settings, dotenv_settings, init_settings)


def project_root() -> Path:
    """Repo root: ``FINSIGHT_ROOT`` if set, else the checkout this file lives in, else cwd."""
    env = os.environ.get("FINSIGHT_ROOT")
    if env:
        return Path(env).resolve()
    checkout = Path(__file__).resolve().parents[3]
    if (checkout / "configs" / "config.yaml").exists():
        return checkout
    return Path.cwd().resolve()


def load_settings(profile: str | None = None, config_path: Path | None = None) -> Settings:
    """Load ``config.yaml`` and build the settings for one profile (env overrides apply)."""
    root = project_root()
    path = config_path or Path(
        os.environ.get("FINSIGHT_CONFIG") or root / "configs" / "config.yaml"
    )
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    chosen = profile or os.environ.get("FINSIGHT_PROFILE") or DEFAULT_PROFILE
    profiles: dict[str, Any] = raw.get("profiles", {})
    if chosen not in profiles:
        raise ValueError(f"Unknown profile {chosen!r}. Available: {sorted(profiles)}")

    paths = {key: str((root / value).resolve()) for key, value in raw.get("paths", {}).items()}
    settings = Settings(root=root, paths=paths, **profiles[chosen])
    settings.profile = chosen  # the argument wins over FINSIGHT_PROFILE picked up from the env
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reset_settings() -> None:
    """Drop the cached settings (tests, or after changing env vars)."""
    get_settings.cache_clear()
