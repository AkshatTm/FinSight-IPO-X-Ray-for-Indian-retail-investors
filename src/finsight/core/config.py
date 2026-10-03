"""Profile-based settings (02_ARCHITECTURE.md section 8).

``configs/config.yaml`` holds shared ``paths`` and one block per profile
(``dev_light`` default, ``full``, ``deploy_cpu``; Phase 2 adds ``cloud`` for Google Cloud Run
on CPU and ``cloud_gpu`` for the optional L4 GPU job, B-ADR-04). Environment variables win over
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
    """Where data, processed outputs, models and eval results live."""

    data_dir: Path = Path("data")
    processed_dir: Path = Path("data/processed")
    models_dir: Path = Path("models")
    eval_dir: Path = Path("eval_results")

    @property
    def raw_dir(self) -> Path:
        """Original PDFs (never read by sessions, never committed)."""
        return self.data_dir / "raw"

    @property
    def samples_dir(self) -> Path:
        """Short, truncated snippets that sessions may read."""
        return self.data_dir / "samples"

    @property
    def gold_dir(self) -> Path:
        """Hand-checked gold labels."""
        return self.data_dir / "gold"


class LLMConfig(BaseModel):
    """The chat model: backend, model name and context size (thinking always off)."""

    backend: str = "ollama"
    model: str = "qwen3.5:0.8b"
    num_ctx: int = 2048
    # ADR-032: thinking mode is always off for the small models; config cannot enable it.
    think: Literal[False] = False


class RetrieveConfig(BaseModel):
    """Retrieval switches: dense search, reranking, top-k and abstain thresholds."""

    dense: bool = False
    rerank: bool = False
    rerank_top_n: int = 20
    final_top_k: int = 5
    # Abstain below this top score, per retrieval method (the score scales differ). Tuned on the
    # 50 dev questions only (ADR-049); a method without an entry never abstains on score.
    abstain_thresholds: dict[str, float] = Field(default_factory=dict)


class VoiceConfig(BaseModel):
    """Speech recognition model (``off`` disables voice) and idle unload time."""

    asr: str = "off"
    idle_unload_s: int = 120


class VerifyConfig(BaseModel):
    """Verifier switches (the optional NLI check)."""

    nli: bool = False


class GuardConfig(BaseModel):
    """Advice guard backend (keyword rules or the fine-tuned classifier)."""

    # keyword = rules (ADR-046); muril = fine-tuned classifier (P5.4). Privacy is always rules.
    backend: Literal["keyword", "muril"] = "keyword"
    threshold: float = 0.5  # probability of "advice" at or above which the classifier blocks


class UploadsConfig(BaseModel):
    """Upload limits (B01 B-FR-01, B02 §11-12). ``UPLOADS_ENABLED=false`` is the kill switch."""

    enabled: bool = True
    max_mb: int = 50  # Akshat's limit (B01 B-FR-01); the UI copy reads this value
    max_pages: int = 1500
    # A PDF whose median page has fewer extractable characters than this is treated as a scan.
    scanned_min_median_chars: int = 100
    per_user_per_day: int = 3
    global_per_day: int = 10
    retention_days: int = 30


class StorageConfig(BaseModel):
    """Where document artefacts live: the local ``data/`` tree or a GCS bucket (B02 §9)."""

    backend: Literal["local", "gcs"] = "local"
    local_dir: Path = Path("data/store")  # keys are docs/<doc_id>/..., bank/...
    bucket: str | None = None  # env FINSIGHT_STORAGE__BUCKET in the cloud profiles
    signed_url_ttl_s: int = 900


class DbConfig(BaseModel):
    """SQLite locally, Supabase Postgres via the pooler in the cloud (B02 §9)."""

    backend: Literal["sqlite", "postgres"] = "sqlite"
    sqlite_path: Path = Path("data/finsight.db")
    url: str | None = None  # env FINSIGHT_DB__URL only; never in YAML or git


class AuthConfig(BaseModel):
    """``off`` = one local user (laptop); ``supabase`` = verify Supabase JWTs (B06 §1)."""

    mode: Literal["off", "supabase"] = "off"
    supabase_url: str | None = None  # env FINSIGHT_AUTH__SUPABASE_URL
    jwt_secret: str | None = None  # env FINSIGHT_AUTH__JWT_SECRET (HS256 fallback only)
    audience: str = "authenticated"
    admin_emails: list[str] = Field(default_factory=list)


class SimplifyConfig(BaseModel):
    """Plain-English rewrites (B02 §8): top N automatic, the rest on click."""

    backend: Literal["ollama", "llama-cpp", "vllm"] = "ollama"
    model: str = "qwen3.5:2b"
    # The base instruct model with the same prompt, used (and flagged) when the student is
    # unavailable; a GGUF file name for llama-cpp, a tag for Ollama.
    fallback_model: str | None = None
    auto_top_n: int = 15
    vllm_url: str | None = None  # optional GPU path only


class JobsConfig(BaseModel):
    """``inline`` = in-process worker (laptop, tests); ``cloud_run`` = Cloud Run Jobs (B02 §10)."""

    runner: Literal["inline", "cloud_run"] = "inline"
    gpu_job: bool = False  # cloud_gpu: simplify + index run in the L4 job
    cpu_job_name: str = "finsight-worker"  # Cloud Run Job names (deploy/gcp/*.yaml)
    gpu_job_name: str = "finsight-gpu-worker"
    poll_interval_s: float = 1.0


# Environment variables a deployment may need. Names only: values never live in the repo.
# ``.env.example`` must list exactly these (tests/core/test_config_profiles.py).
ENV_KEYS: tuple[str, ...] = (
    "FINSIGHT_PROFILE",
    "UPLOADS_ENABLED",
    "FINSIGHT_DB__URL",
    "FINSIGHT_STORAGE__BUCKET",
    "FINSIGHT_AUTH__SUPABASE_URL",
    "FINSIGHT_AUTH__JWT_SECRET",
    "FINSIGHT_AUTH__ADMIN_EMAILS",
    "FINSIGHT_SIMPLIFY__VLLM_URL",
    "GCP_PROJECT",
    "GCP_REGION",
    "FINSIGHT_API_ORIGIN",  # frontend build: where Next.js rewrites /api/* (next.config.ts)
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
)

# What each profile cannot run without (``scripts/check_env.py`` reports the missing names).
REQUIRED_ENV: dict[str, tuple[str, ...]] = {
    "cloud": (
        "FINSIGHT_DB__URL",
        "FINSIGHT_STORAGE__BUCKET",
        "FINSIGHT_AUTH__SUPABASE_URL",
        "GCP_PROJECT",
        "GCP_REGION",
    ),
    "cloud_gpu": (
        "FINSIGHT_DB__URL",
        "FINSIGHT_STORAGE__BUCKET",
        "FINSIGHT_AUTH__SUPABASE_URL",
        "GCP_PROJECT",
        "GCP_REGION",
    ),
}


def missing_env(profile: str, environ: dict[str, str] | None = None) -> list[str]:
    """Names of required environment variables that are unset or empty for ``profile``."""
    env = os.environ if environ is None else environ
    return [name for name in REQUIRED_ENV.get(profile, ()) if not env.get(name)]


class Settings(BaseSettings):
    """All settings for one profile; environment variables win over the YAML."""

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
    uploads: UploadsConfig = Field(default_factory=UploadsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    db: DbConfig = Field(default_factory=DbConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    simplify: SimplifyConfig = Field(default_factory=SimplifyConfig)
    jobs: JobsConfig = Field(default_factory=JobsConfig)
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
        """Make environment variables beat the YAML values."""
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


SHARED_BLOCKS = ("uploads",)


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
    chosen_values = dict(profiles[chosen])
    for key in SHARED_BLOCKS:  # top-level blocks apply to every profile; a profile may override
        if key in raw:
            chosen_values[key] = {**raw[key], **chosen_values.get(key, {})}
    settings = Settings(root=root, paths=paths, **chosen_values)
    settings.profile = chosen  # the argument wins over FINSIGHT_PROFILE picked up from the env
    kill = os.environ.get("UPLOADS_ENABLED")
    if kill is not None:  # the kill switch has a short name so it is easy to flip in a console
        settings.uploads.enabled = kill.strip().lower() not in {"0", "false", "no", "off"}
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The settings for ``FINSIGHT_PROFILE``, loaded once and cached."""
    return load_settings()


def reset_settings() -> None:
    """Drop the cached settings (tests, or after changing env vars)."""
    get_settings.cache_clear()
