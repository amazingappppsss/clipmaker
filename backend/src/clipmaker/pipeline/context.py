"""What a stage receives: ids, settings, storage, a scratch dir, providers and a heartbeat.

Providers are built lazily so that a missing API key only fails the stage that needs it,
with a clear, permanent error — never a crash at worker start-up.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from clipmaker.core.config import Settings
from clipmaker.pipeline.errors import PermanentStageError
from clipmaker.providers.llm.base import LLMError, LLMProvider
from clipmaker.providers.transcription.base import TranscriptionError, TranscriptionProvider
from clipmaker.storage.base import ObjectStorage, project_prefix


@dataclass(slots=True)
class StageOutput:
    """What a stage reports back to the runner."""

    outputs: dict[str, Any] = field(default_factory=dict)
    cost_usd: Decimal = Decimal(0)
    skipped: bool = False  # output already existed (idempotent re-run)


@dataclass(slots=True)
class StageContext:
    """Everything a stage needs. Stages open their own short DB sessions via `sessions`."""

    job_id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    settings: Settings
    storage: ObjectStorage
    sessions: sessionmaker[Session]
    work_dir: Path
    heartbeat: Callable[[], None]
    llm_factory: Callable[[Settings], LLMProvider]
    transcriber_factory: Callable[[Settings], TranscriptionProvider]
    _llm: LLMProvider | None = None
    _transcriber: TranscriptionProvider | None = None

    @property
    def prefix(self) -> str:
        """Storage prefix for this project's files."""
        return project_prefix(str(self.user_id), str(self.project_id))

    def llm(self) -> LLMProvider:
        if self._llm is None:
            try:
                self._llm = self.llm_factory(self.settings)
            except LLMError as exc:
                raise PermanentStageError("llm_unavailable", str(exc)) from exc
        return self._llm

    def transcriber(self) -> TranscriptionProvider:
        if self._transcriber is None:
            try:
                self._transcriber = self.transcriber_factory(self.settings)
            except TranscriptionError as exc:
                raise PermanentStageError("transcription_unavailable", str(exc)) from exc
        return self._transcriber
