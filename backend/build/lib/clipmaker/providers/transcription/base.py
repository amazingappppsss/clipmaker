"""Transcription provider interface.

Providers return *word-level* timings; sentence segmentation is ours (pipeline/transcript.py) so
it behaves identically whichever provider produced the words. Speaker labels are optional.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Word:
    """One recognised word. Times are seconds from the start of the audio."""

    text: str
    start: float
    end: float
    confidence: float = 1.0
    speaker: str | None = None


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Provider-agnostic transcription output."""

    words: list[Word]
    language: str | None
    duration_seconds: float
    provider: str
    model: str
    cost_usd: Decimal
    has_speakers: bool
    raw: dict[str, Any] = field(default_factory=dict)


class TranscriptionError(Exception):
    """`retryable` tells the pipeline whether trying again can help."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


Heartbeat = Callable[[], None]


class TranscriptionProvider(Protocol):
    """Turns an audio file into timed words."""

    name: str

    def transcribe(
        self, audio: Path, language: str | None, heartbeat: Heartbeat
    ) -> TranscriptionResult:
        """Transcribe `audio`. `language` is an ISO code or None for auto-detect.
        `heartbeat` must be called at least every few minutes during long waits."""
        ...
