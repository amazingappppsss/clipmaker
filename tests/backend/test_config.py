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
