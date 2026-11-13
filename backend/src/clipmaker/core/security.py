"""Verification of Supabase Auth access tokens (JWT).

Supabase signs access tokens either with asymmetric "JWT signing keys" (ES256/RS256,
published at `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`) or, for legacy projects and local
development, with a shared HS256 secret. Both are supported; the algorithm is taken from our
own configuration, never trusted from the token header alone.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt

from clipmaker.core.config import Settings
from clipmaker.core.errors import AuthError

_ASYMMETRIC_ALGS = ["ES256", "RS256"]


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Identity extracted from a verified token."""

    id: uuid.UUID
    email: str | None


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    # Keys are cached in-process; PyJWKClient refetches when it sees an unknown `kid`.
    return jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


def verify_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Validate signature, expiry and audience; return the user identity.

    Raises:
        AuthError: for any invalid, expired or unverifiable token.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthError("Malformed token") from exc

    alg = header.get("alg")
    key: Any
    algorithms: list[str]
    if alg == "HS256":
        if settings.supabase_jwt_secret is None:
            raise AuthError("HS256 tokens are not accepted by this server")
        key = settings.supabase_jwt_secret.get_secret_value()
        algorithms = ["HS256"]
    elif alg in _ASYMMETRIC_ALGS and settings.supabase_url:
        jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        except jwt.PyJWTError as exc:
            raise AuthError("Unable to verify token signature") from exc
        algorithms = _ASYMMETRIC_ALGS
    else:
        raise AuthError("Unsupported token algorithm")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=settings.jwt_audience,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid token") from exc

    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except ValueError as exc:
        raise AuthError("Invalid subject claim") from exc
    email = claims.get("email")
    return AuthenticatedUser(id=user_id, email=email if isinstance(email, str) else None)


def mint_dev_token(user_id: uuid.UUID, email: str, settings: Settings, ttl: int = 86400) -> str:
    """Create an HS256 token shaped like a Supabase token. Development/tests only."""
    import time

    if settings.supabase_jwt_secret is None:
        raise RuntimeError("SUPABASE_JWT_SECRET must be set to mint dev tokens")
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "aud": settings.jwt_audience,
        "role": "authenticated",
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.supabase_jwt_secret.get_secret_value(), algorithm="HS256")
