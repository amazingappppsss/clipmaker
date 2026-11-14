"""Select the configured transcription provider."""

from __future__ import annotations

from clipmaker.core.config import Settings
from clipmaker.providers.transcription.base import TranscriptionError, TranscriptionProvider


def build_transcription_provider(settings: Settings) -> TranscriptionProvider:
    """Return the provider named by `TRANSCRIPTION_PROVIDER`."""
    if settings.transcription_provider == "assemblyai":
        from clipmaker.providers.transcription.assemblyai import AssemblyAIProvider

        return AssemblyAIProvider(settings)
    raise TranscriptionError(
        f"Unknown transcription provider '{settings.transcription_provider}'", retryable=False
    )
