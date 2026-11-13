"""Pipeline runner: walks a job through its stages reliably (PRD §8).

Guarantees:
* **Single runner per job** — a DB lease (`lease_owner`, `lease_expires_at`) is taken with an
  atomic UPDATE; a second worker gets `SKIPPED`. A crashed worker's lease expires and the job is
  picked up again (by Celery redelivery or the stale-job reaper).
* **No repeated work** — completed stages are recorded in `processing_jobs.stages` and skipped;
  stages are also idempotent on their own outputs.
* **Bounded retries** — a stage is attempted at most `stage_max_attempts` times, with
  exponential backoff between attempts. Never an infinite loop.
* **Honest terminal states** — COMPLETED only when every stage ran; on failure the project shows
  a readable reason and the user's credits are refunded.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import or_, update
from sqlalchemy.orm import Session, sessionmaker

from clipmaker.core.config import Settings
from clipmaker.core.enums import PIPELINE_STAGES, TERMINAL_STATES, ProjectState
from clipmaker.db.models import ProcessingJob, Project, User
from clipmaker.media.url_import import build_url_importer
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import JobCancelledError, StageError
from clipmaker.pipeline.stages import ingest, transcribe, understand
from clipmaker.pipeline.stages import select as select_stage
from clipmaker.providers.llm.factory import build_llm_provider
from clipmaker.providers.transcription.factory import build_transcription_provider
from clipmaker.services.billing import project_net_charge, refund_credits
from clipmaker.storage.base import ObjectStorage

logger = logging.getLogger(__name__)

StageFn = Callable[[StageContext], StageOutput]

# Stages implemented so far. Later milestones register EDITING, RENDERING and QUALITY_CHECK.
STAGE_HANDLERS: dict[ProjectState, StageFn] = {
    ProjectState.INGESTING: ingest.run,
    ProjectState.TRANSCRIBING: transcribe.run,
    ProjectState.UNDERSTANDING: understand.run,
    ProjectState.SELECTING: select_stage.run,
}

NOT_YET_AVAILABLE_MESSAGE = (
    "Your best moments are picked and ready below. Automatic editing into finished vertical "
    "videos is the next feature being built, so rendered clips aren't available yet."
)


class Outcome(StrEnum):
    """What the caller (Celery task) should do next."""

    COMPLETED = "completed"
    PAUSED = "paused"  # stopped at a stage that isn't implemented yet (NEEDS_REVIEW)
    RETRY = "retry"
    FAILED = "failed"
    SKIPPED = "skipped"  # another worker holds the lease, or the job is already finished
    CANCELLED = "cancelled"


def backoff_seconds(attempt: int) -> int:
    """30s, 2m, 8m, ... capped at 30 minutes."""
    return int(min(30 * 4 ** max(attempt - 1, 0), 1800))


def _now() -> datetime:
    return datetime.now(UTC)


class JobRunner:
    """Runs one job. Construct per run; `run()` returns an (Outcome, retry_delay_seconds)."""

    def __init__(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        settings: Settings,
        storage: ObjectStorage,
        sessions: sessionmaker[Session],
        handlers: dict[ProjectState, StageFn] | None = None,
        llm_factory: Callable[[Settings], Any] = build_llm_provider,
        transcriber_factory: Callable[[Settings], Any] = build_transcription_provider,
        importer_factory: Callable[[Settings], Any] | None = None,
    ) -> None:
        self.job_id = job_id
        self.worker_id = worker_id
        self.settings = settings
        self.storage = storage
        self.sessions = sessions
        self.handlers = STAGE_HANDLERS if handlers is None else handlers
        self.llm_factory = llm_factory
        self.transcriber_factory = transcriber_factory
        self.importer_factory = importer_factory or build_url_importer

    # --- lease ------------------------------------------------------------------------
    def _acquire_lease(self) -> bool:
        now = _now()
        with self.sessions() as db:
            result = db.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.id == self.job_id,
                    ProcessingJob.state.notin_(TERMINAL_STATES),
                    or_(
                        ProcessingJob.lease_owner.is_(None),
                        ProcessingJob.lease_owner == self.worker_id,
                        ProcessingJob.lease_expires_at < now,
                    ),
                )
                .values(
                    lease_owner=self.worker_id,
                    lease_expires_at=now + timedelta(seconds=self.settings.job_lease_seconds),
                )
                .returning(ProcessingJob.id)
            ).first()
            db.commit()
            return result is not None

    def heartbeat(self) -> None:
        """Extend the lease. Raises JobCancelledError if another worker took over."""
        with self.sessions() as db:
            row = db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.id == self.job_id, ProcessingJob.lease_owner == self.worker_id)
                .values(
                    lease_expires_at=_now() + timedelta(seconds=self.settings.job_lease_seconds)
                )
                .returning(ProcessingJob.id)
            ).first()
            db.commit()
        if row is None:
            raise JobCancelledError("lease lost")

    def _release_lease(self, db: Session, job: ProcessingJob) -> None:
        if job.lease_owner == self.worker_id:
            job.lease_owner = None
            job.lease_expires_at = None

    # --- main loop ----------------------------------------------------------------------
    def run(self) -> tuple[Outcome, int]:
        if not self._acquire_lease():
            logger.info("job_skipped_lease_held", extra={"job_id": str(self.job_id)})
            return Outcome.SKIPPED, 0
        work_dir = Path(self.settings.work_dir) / str(self.job_id)
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            return self._run_stages(work_dir)
        except JobCancelledError:
            logger.warning("job_cancelled_or_lease_lost", extra={"job_id": str(self.job_id)})
            return Outcome.CANCELLED, 0
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _load(self, db: Session) -> tuple[ProcessingJob, Project]:
        job = db.get(ProcessingJob, self.job_id, with_for_update=False)
        project = db.get(Project, job.project_id) if job else None
        if job is None or project is None or project.deleted_at is not None:
            raise JobCancelledError("project gone")
        if project.state == ProjectState.CANCELLED:
            raise JobCancelledError("project cancelled")
        return job, project

    def _run_stages(self, work_dir: Path) -> tuple[Outcome, int]:
        with self.sessions() as db:
            job, project = self._load(db)
            if job.started_at is None:
                job.started_at = _now()
            ctx = StageContext(
                job_id=job.id,
                project_id=project.id,
                user_id=project.user_id,
                settings=self.settings,
                storage=self.storage,
                sessions=self.sessions,
                work_dir=work_dir,
                heartbeat=self.heartbeat,
                llm_factory=self.llm_factory,
                transcriber_factory=self.transcriber_factory,
                importer_factory=self.importer_factory,
            )
            db.commit()

        total = len(PIPELINE_STAGES)
        for index, stage in enumerate(PIPELINE_STAGES):
            with self.sessions() as db:
                job, project = self._load(db)
                record: dict[str, Any] = dict(job.stages.get(stage.value, {}))
                if record.get("status") == "done":
                    continue
                handler = self.handlers.get(stage)
                if handler is None:
                    return self._pause(db, job, project, index / total)
                attempts = int(record.get("attempts", 0)) + 1
                record.update(
                    status="running", attempts=attempts, started_at=_now().isoformat(), error=None
                )
                job.stages = {**job.stages, stage.value: record}
                job.state = project.state = stage
                job.progress = index / total
                project.error_message = None
                db.commit()

            logger.info(
                "stage_started",
                extra={"job_id": str(self.job_id), "stage": stage.value, "attempt": attempts},
            )
            try:
                output = handler(ctx)
            except JobCancelledError:
                raise
            except Exception as exc:
                return self._stage_failed(stage, attempts, exc)

            with self.sessions() as db:
                job, project = self._load(db)
                record = dict(job.stages.get(stage.value, {}))
                record.update(
                    status="done",
                    finished_at=_now().isoformat(),
                    outputs=output.outputs,
                    skipped=output.skipped,
                    cost_usd=str(output.cost_usd),
                )
                job.stages = {**job.stages, stage.value: record}
                job.cost_usd = Decimal(job.cost_usd) + output.cost_usd
                job.progress = (index + 1) / total
                db.commit()
            self.heartbeat()
            logger.info(
                "stage_done",
                extra={
                    "job_id": str(self.job_id),
                    "stage": stage.value,
                    "skipped": output.skipped,
                    "cost_usd": str(output.cost_usd),
                },
            )

        with self.sessions() as db:
            job, project = self._load(db)
            job.state = project.state = ProjectState.COMPLETED
            job.progress = 1.0
            job.completed_at = _now()
            self._release_lease(db, job)
            db.commit()
        return Outcome.COMPLETED, 0

    def _pause(
        self, db: Session, job: ProcessingJob, project: Project, progress: float
    ) -> tuple[Outcome, int]:
        job.state = project.state = ProjectState.NEEDS_REVIEW
        job.progress = progress
        job.completed_at = _now()
        project.error_message = NOT_YET_AVAILABLE_MESSAGE
        self._release_lease(db, job)
        db.commit()
        return Outcome.PAUSED, 0

    def _stage_failed(
        self, stage: ProjectState, attempts: int, exc: Exception
    ) -> tuple[Outcome, int]:
        retryable = exc.retryable if isinstance(exc, StageError) else True
        code = exc.code if isinstance(exc, StageError) else "internal_error"
        # Unexpected errors name the exception so a user report is enough to diagnose them.
        user_message = (
            exc.message
            if isinstance(exc, StageError)
            else f"An unexpected error occurred ({type(exc).__name__}: {str(exc)[:200]})."
        )
        logger.warning(
            "stage_failed",
            exc_info=not isinstance(exc, StageError),
            extra={
                "job_id": str(self.job_id),
                "stage": stage.value,
                "code": code,
                "attempt": attempts,
                "retryable": retryable,
            },
        )
        will_retry = retryable and attempts < self.settings.stage_max_attempts
        with self.sessions() as db:
            job, project = self._load(db)
            record = dict(job.stages.get(stage.value, {}))
            record.update(
                status="failed", error=f"{code}: {exc}"[:1000], finished_at=_now().isoformat()
            )
            job.stages = {**job.stages, stage.value: record}
            job.error_code, job.error_detail = code, str(exc)[:4000]
            self._release_lease(db, job)
            if will_retry:
                job.retry_count += 1
                db.commit()
                return Outcome.RETRY, backoff_seconds(attempts)
            job.state = project.state = ProjectState.FAILED
            job.completed_at = _now()
            refunded = self._refund(db, project)
            suffix = " Your credits have been refunded." if refunded else ""
            project.error_message = f"{user_message}{suffix}"
            db.commit()
        return Outcome.FAILED, 0

    def _refund(self, db: Session, project: Project) -> bool:
        """Return the credits charged for this project's current run (once). True if refunded."""
        charged = project_net_charge(db, project.id)
        user = db.get(User, project.user_id)
        if charged > 0 and user is not None:
            refund_credits(db, user, charged, project.id, "Refund: processing failed")
            return True
        return False
