"""Typed application configuration.

All configuration comes from environment variables (or a local `.env` file in development).
Secrets are never hardcoded; see `.env.example` at the repository root for every key.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    """Deployment environment. Development-only features are refused outside `development`."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class StorageBackend(StrEnum):
    """Which object-storage implementation to use."""

    LOCAL = "local"  # filesystem + HMAC-signed URLs served by the API (dev/test only)
    S3 = "s3"  # any S3-compatible service; Cloudflare R2 in production


class Settings(BaseSettings):
    """Every runtime setting, validated at startup."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: AppEnv = AppEnv.DEVELOPMENT
    log_level: str = "INFO"
    # Public base URL of this API, used to build local-storage signed URLs.
    api_public_url: str = "http://localhost:8000"
    # Comma-separated list of browser origins allowed to call the API.
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://clipmaker:clipmaker@localhost:5432/clipmaker"
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth (Supabase) ---------------------------------------------------------------
    # Supabase project URL. When set, tokens are verified against its JWKS (ES256/RS256).
    supabase_url: str | None = None
    # Legacy/shared HS256 secret. Used for HS256 tokens (Supabase legacy keys, or local dev).
    supabase_jwt_secret: SecretStr | None = None
    jwt_audience: str = "authenticated"
    # Enables POST /dev/token which mints local HS256 tokens. Refused outside development.
    enable_dev_auth: bool = False

    # --- Storage ------------------------------------------------------------------------
    storage_backend: StorageBackend = StorageBackend.LOCAL
    local_storage_dir: str = "./.data/storage"
    # HMAC key for local signed URLs. Must be set explicitly outside dev/test.
    storage_signing_key: SecretStr = SecretStr("dev-only-signing-key-change-me")
    s3_endpoint_url: str | None = None  # e.g. https://<account>.r2.cloudflarestorage.com
    s3_bucket: str | None = None
    s3_region: str = "auto"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    signed_url_ttl_seconds: int = Field(default=3600, ge=60, le=7 * 24 * 3600)

    # --- Upload limits ------------------------------------------------------------------
    max_upload_bytes: int = 5 * 1024**3  # 5 GiB: the S3 single-PUT ceiling
    max_video_duration_seconds: int = 4 * 3600
    min_video_duration_seconds: int = 30

    # --- Rate limiting -------------------------------------------------------------------
    rate_limit_per_minute: int = 120

    # --- AI providers (PRD §7: swappable through configuration) --------------------------
    llm_provider: str = "anthropic"
    anthropic_api_key: SecretStr | None = None
    # "smart" = full-video understanding + clip selection (the quality-critical step).
    llm_smart_model: str = "claude-opus-5-5"
    llm_smart_effort: str = "high"
    # "fast" = titles, hooks, captions, hashtags (cheap, high-volume).
    llm_fast_model: str = "claude-haiku-5-5"
    llm_fast_effort: str = "low"
    # Server-side refusal fallback for the smart model (on by default; set false to disable).
    llm_refusal_fallback: bool = True

    transcription_provider: str = "assemblyai"
    assemblyai_api_key: SecretStr | None = None
    assemblyai_base_url: str = "https://api.assemblyai.com"
    # Estimated list price used for cost tracking; verify against the provider's pricing page.
    assemblyai_usd_per_hour: float = 0.15
    transcription_timeout_seconds: int = 3600

    # --- Pipeline -------------------------------------------------------------------------
    stage_max_attempts: int = Field(default=3, ge=1, le=10)
    job_lease_seconds: int = Field(default=900, ge=60)
    min_clip_seconds: float = 20.0
    max_clip_seconds: float = 90.0
    # Minimum weighted score (0-100) a candidate needs to become a clip. Fewer, better clips
    # beat padding the result with weak ones.
    min_clip_score: float = 55.0
    # Editorial scoring weights (PRD §5.4) — initial heuristics, kept configurable. JSON object.
    score_weights_json: str = (
        '{"standalone_context": 0.25, "strong_opening": 0.20, "story_payoff": 0.20,'
        ' "emotional_engagement": 0.15, "information_value": 0.10, "natural_ending": 0.10}'
    )
    work_dir: str = "./.data/work"

    @model_validator(mode="after")
    def _check_production_safety(self) -> Settings:
        """Fail fast on insecure configuration instead of discovering it in production."""
        if self.app_env == AppEnv.PRODUCTION:
            if self.enable_dev_auth:
                raise ValueError("ENABLE_DEV_AUTH must be false in production")
            if self.storage_backend == StorageBackend.LOCAL:
                raise ValueError("STORAGE_BACKEND=local is not allowed in production")
            if not self.supabase_url and not self.supabase_jwt_secret:
                raise ValueError("Set SUPABASE_URL or SUPABASE_JWT_SECRET in production")
        if self.storage_backend == StorageBackend.S3 and not self.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings (cached). Tests clear the cache to override."""
    return Settings()
