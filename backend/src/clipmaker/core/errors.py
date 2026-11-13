"""Typed application errors.

Services raise these; the API layer converts them to JSON responses with a stable `code`
that the frontend can branch on. Internal details never leak to clients.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected, user-facing errors."""

    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    """Resource does not exist — or belongs to another user (never reveal which)."""

    status_code = 404
    code = "not_found"


class AuthError(AppError):
    """Missing or invalid credentials."""

    status_code = 401
    code = "unauthorized"


class ConflictError(AppError):
    """Request conflicts with the current state of the resource."""

    status_code = 409
    code = "conflict"


class ValidationFailedError(AppError):
    """Input passed schema validation but failed a business rule."""

    status_code = 422
    code = "validation_failed"


class RateLimitedError(AppError):
    """Too many requests."""

    status_code = 429
    code = "rate_limited"


class InsufficientCreditsError(AppError):
    """The user does not have enough credits for this operation."""

    status_code = 402
    code = "insufficient_credits"
