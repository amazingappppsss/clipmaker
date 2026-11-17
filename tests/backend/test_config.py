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


def test_api_docs_are_closed_unless_switched_on() -> None:
    """They were open to the internet because APP_ENV was not exactly "production"."""
    assert Settings().expose_api_docs is False
    assert Settings(expose_api_docs=True).expose_api_docs is True


def test_a_placeholder_api_url_loses_to_the_platforms_own_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This exact value shipped and sent the transcription provider to a 404."""
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "clipmaker-production-ee9196d1.up.railway.app")
    stale = Settings(api_public_url="https://clipmaker-production-xxxx.up.railway.app")
    assert stale.public_api_url == "https://clipmaker-production-ee9196d1.up.railway.app"

    # Unset is the normal case: ask the platform.
    unset = Settings(api_public_url=None)
    assert unset.public_api_url == "https://clipmaker-production-ee9196d1.up.railway.app"

    # A real custom domain is deliberate and is kept.
    real = Settings(api_public_url="https://api.clip2easy.com")
    assert real.public_api_url == "https://api.clip2easy.com"


def test_a_relative_api_url_is_deliberate_and_survives(monkeypatch: pytest.MonkeyPatch) -> None:
    """ "/api" behind the dev proxy is a choice, not an unfinished value."""
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "something.up.railway.app")
    assert Settings(api_public_url="/api").public_api_url == "/api"


def test_without_a_platform_domain_nothing_is_invented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)
    assert Settings(api_public_url=None).public_api_url is None
    # Even a placeholder is kept when there is nothing better; guessing would be worse.
    assert Settings(api_public_url="https://x-xxxx.app").public_api_url == "https://x-xxxx.app"
