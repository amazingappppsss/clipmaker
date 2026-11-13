"""Select the configured LLM provider (PRD §7: swappable without rewriting the app)."""

from __future__ import annotations

from clipmaker.core.config import Settings
from clipmaker.providers.llm.base import LLMError, LLMProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Return the provider named by `LLM_PROVIDER`."""
    if settings.llm_provider == "anthropic":
        from clipmaker.providers.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings)
    raise LLMError(f"Unknown LLM provider '{settings.llm_provider}'", retryable=False)
