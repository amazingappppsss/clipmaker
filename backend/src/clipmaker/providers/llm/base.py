"""LLM provider interface.

The pipeline asks for *structured JSON* only: every call names a JSON schema and gets back a
parsed dict that matches it (providers must enforce the schema natively where they can).
`tier` picks the model: "smart" for the quality-critical reasoning, "fast" for cheap metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Protocol

Tier = Literal["smart", "fast"]


@dataclass(frozen=True, slots=True)
class LLMUsage:
    """Token accounting for one call (cache fields are 0 when unsupported)."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True, slots=True)
class LLMResult:
    """Parsed output plus what it cost."""

    data: dict[str, Any]
    model: str
    usage: LLMUsage
    cost_usd: Decimal
    request_id: str | None = None
    notes: list[str] = field(default_factory=list)  # e.g. "served by fallback model"


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """One structured-output request.

    `context` is large, stable input (e.g. the transcript) placed first and marked cacheable,
    so several calls about the same video pay for it only once.
    """

    tier: Tier
    system: str
    context: str
    instruction: str
    schema: dict[str, Any]
    max_tokens: int = 16000


class LLMError(Exception):
    """Base error. `retryable` tells the pipeline whether trying again can help."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMProvider(Protocol):
    """Anything that can answer an LLMRequest with schema-valid JSON."""

    name: str

    def complete_json(self, request: LLMRequest) -> LLMResult:
        """Run the request. Raises LLMError on failure."""
        ...
