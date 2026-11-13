"""core/security.py — token verification edge cases."""

from __future__ import annotations

import time
import uuid

import jwt
import pytest

from clipmaker.core.config import get_settings
from clipmaker.core.errors import AuthError
from clipmaker.core.security import mint_dev_token, verify_access_token

SECRET = "test-secret-that-is-long-enough-for-hs256"


def _token(**overrides: object) -> str:
    now = int(time.time())
    payload = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "exp": now + 60,
        "iat": now,
        **overrides,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def test_valid_token_round_trip() -> None:
    uid = uuid.uuid4()
    user = verify_access_token(mint_dev_token(uid, "a@b.co", get_settings()), get_settings())
    assert user.id == uid and user.email == "a@b.co"


def test_expired_token_rejected() -> None:
    with pytest.raises(AuthError) as err:
        verify_access_token(_token(exp=int(time.time()) - 10), get_settings())
    assert err.value.code == "token_expired"


def test_wrong_audience_rejected() -> None:
    with pytest.raises(AuthError):
        verify_access_token(_token(aud="anon"), get_settings())


def test_wrong_secret_rejected() -> None:
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60},
        "x" * 40,
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        verify_access_token(forged, get_settings())


def test_alg_none_rejected() -> None:
    unsigned = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60},
        None,
        algorithm="none",
    )
    with pytest.raises(AuthError):
        verify_access_token(unsigned, get_settings())


def test_non_uuid_subject_rejected() -> None:
    with pytest.raises(AuthError):
        verify_access_token(_token(sub="not-a-uuid"), get_settings())


def test_malformed_token_rejected() -> None:
    with pytest.raises(AuthError):
        verify_access_token("abc.def", get_settings())


def test_asymmetric_token_without_supabase_url_explains_misconfiguration() -> None:
    import base64
    import json

    def b64(data: dict[str, str]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    header_only = f"{b64({'alg': 'ES256', 'typ': 'JWT'})}.{b64({'sub': 'x'})}.c2ln"
    with pytest.raises(AuthError, match="SUPABASE_URL"):
        verify_access_token(header_only, get_settings())
