"""core/config.py — production safety rules and hosting-platform compatibility."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from clipmaker.core.config import Settings

PROD_OK = {
    "app_env": "production",
    "enable_dev_auth": False,
    "supabase_url": "https://abc.supabase.co",
    "storage_backend": "local",
    "allow_single_node_storage": True,
    "storage_signing_key": "a-strong-random-signing-key-value",
}


@pytest.mark.parametrize(
    "url",
    [
        "postgres://u:p@h:5432/db",
        "postgresql://u:p@h:5432/db",
        "postgresql+psycopg://u:p@h:5432/db",
    ],
)
def test_platform_database_urls_are_normalised(url: str) -> None:
    assert Settings(database_url=url).database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_valid_single_node_production_config() -> None:
    Settings(**PROD_OK)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"enable_dev_auth": True}, "ENABLE_DEV_AUTH"),
        ({"allow_single_node_storage": False}, "ALLOW_SINGLE_NODE_STORAGE"),
        ({"storage_signing_key": "dev-only-signing-key-change-me"}, "STORAGE_SIGNING_KEY"),
        ({"supabase_url": None}, "SUPABASE"),
    ],
)
def test_unsafe_production_config_refused(override: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(**{**PROD_OK, "supabase_jwt_secret": None, **override})


def test_cors_origins_tolerate_spaces_and_trailing_slash() -> None:
    settings = Settings(cors_origins=" https://a.app/ , https://b.app")
    # Our own frontends are appended (see OUR_FRONTEND_ORIGINS); what matters here is that the
    # configured ones are parsed, trimmed and come first.
    assert settings.cors_origin_list[:2] == ["https://a.app", "https://b.app"]


def test_api_keys_accept_variant_names_and_strip_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
    monkeypatch.setenv("ASSEMBLY_AI_API_KEY", '  "abc123"\n')
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    s = Settings()
    assert s.assemblyai_api_key is not None
    assert s.assemblyai_api_key.get_secret_value() == "abc123"
    assert s.anthropic_api_key is None


def test_files_go_to_the_platform_volume(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    monkeypatch.delenv("LOCAL_STORAGE_DIR", raising=False)
    monkeypatch.delenv("WORK_DIR", raising=False)
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (s.local_storage_dir, s.work_dir) == ("/data/storage", "/data/work")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", "/elsewhere")
    assert Settings(_env_file=None).local_storage_dir == "/elsewhere"  # type: ignore[call-arg]


def test_our_own_frontends_are_always_allowed_origins() -> None:
    """A stale CORS_ORIGINS on the host must not be able to take the live site's forms down."""
    from clipmaker.core.config import OUR_FRONTEND_ORIGINS, Settings

    stale = Settings(cors_origins="https://an-old-domain.example")
    for origin in OUR_FRONTEND_ORIGINS:
        assert origin in stale.cors_origin_list
    assert "https://an-old-domain.example" in stale.cors_origin_list

    # No duplicates when the host already lists one of ours.
    overlap = Settings(cors_origins="https://clip2easy.vercel.app")
    assert overlap.cors_origin_list.count("https://clip2easy.vercel.app") == 1
