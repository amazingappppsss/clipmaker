"""Errors raised by pipeline stages.

Stages classify failures so the runner can decide what to do:
* `RetryableStageError`  — transient (network, rate limit, provider 5xx). Retried with backoff,
  up to `Settings.stage_max_attempts`.
* `PermanentStageError`  — will not succeed on retry (bad input, missing credentials,
  content the providers refuse). The job fails immediately and credits are refunded.
Any other exception is treated as retryable (unknown failures get the benefit of the doubt,
but are still bounded by the attempt limit — never an infinite loop).
"""

from __future__ import annotations


class StageError(Exception):
    """Base class. `code` is stable and shown to operators; `message` is user-readable."""

    retryable: bool = True

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class RetryableStageError(StageError):
    """Transient failure — try again later."""

    retryable = True


class PermanentStageError(StageError):
    """Failure that retrying cannot fix."""

    retryable = False


class JobCancelledError(Exception):
    """The project was deleted or cancelled while the job ran."""
