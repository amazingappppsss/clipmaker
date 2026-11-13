"""Shared FastAPI dependencies: authentication, rate limiting, storage, settings."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from clipmaker.core.config import Settings, get_settings
from clipmaker.core.errors import AuthError, RateLimitedError
from clipmaker.core.rate_limit import Counter, get_counter, is_allowed
from clipmaker.core.security import verify_access_token
from clipmaker.db.models import User
from clipmaker.db.session import get_db
from clipmaker.services.users import get_or_create_user
from clipmaker.storage.base import ObjectStorage
from clipmaker.storage.factory import get_storage

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
Storage = Annotated[ObjectStorage, Depends(get_storage)]


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Authorization header must be 'Bearer <token>'")
    return token


def get_current_user(
    db: DbSession,
    settings: AppSettings,
    counter: Annotated[Counter, Depends(get_counter)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Authenticate the request, enforce the per-user rate limit and load the local user."""
    identity = verify_access_token(_bearer_token(authorization), settings)
    if not is_allowed(counter, f"user:{identity.id}", settings.rate_limit_per_minute):
        raise RateLimitedError("Too many requests. Please slow down.")
    return get_or_create_user(db, identity)


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_job_queue() -> Callable[[uuid.UUID], None]:
    """How the API hands jobs to workers (Celery in production; overridden in tests)."""
    from clipmaker.workers.tasks import enqueue_job

    return enqueue_job


JobQueue = Annotated[Callable[[uuid.UUID], None], Depends(get_job_queue)]
