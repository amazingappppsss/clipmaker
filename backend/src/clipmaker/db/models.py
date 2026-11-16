"""SQLAlchemy ORM models — the relational schema from PRD §9 (+ `video_analyses`).

Design rules:
* Source data, AI decisions, intermediate outputs and final assets live in separate tables,
  so the AI pipeline can be improved and re-run without rebuilding everything.
* Every user-owned row is reachable from `users.id`; services always filter by owner.
* Files are never stored in the DB — only object-storage keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from clipmaker.core.enums import (
    AssetKind,
    ClipStatus,
    Plan,
    ProjectState,
    SubscriptionStatus,
    UploadStatus,
    UsageKind,
)

JsonDict = dict[str, Any]


def _enum(cls: type, name: str) -> Enum:
    """Persist StrEnums by value (not member name) as native PostgreSQL enums."""
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class Base(DeclarativeBase):
    """Declarative base with JSONB mapping for dict columns."""

    type_annotation_map: ClassVar[dict[Any, Any]] = {
        JsonDict: JSONB,
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
    }


class TimestampMixin:
    """`created_at` / `updated_at` maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# --- 1. users ---------------------------------------------------------------------------
class User(TimestampMixin, Base):
    """Local mirror of a Supabase Auth user. `id` equals the Supabase `sub` claim."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(120))
    plan: Mapped[Plan] = mapped_column(_enum(Plan, "plan"), default=Plan.FREE, nullable=False)
    # Cached balance; the source of truth is the sum of `usage_records.credits`.
    credits_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    projects: Mapped[list[Project]] = relationship(back_populates="user")


# --- 2. projects ------------------------------------------------------------------------
class Project(TimestampMixin, Base):
    """One user request: a source video turned into a set of clips."""

    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[ProjectState] = mapped_column(
        _enum(ProjectState, "project_state"), default=ProjectState.CREATED, nullable=False
    )
    # ProjectSettings (category, language, clip_count, style) — validated by pydantic.
    settings: Mapped[JsonDict] = mapped_column(default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Unguessable token for a read-only results link (None = not shared). Revocable.
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True)

    user: Mapped[User] = relationship(back_populates="projects")
    source_video: Mapped[SourceVideo | None] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    jobs: Mapped[list[ProcessingJob]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProcessingJob.created_at"
    )
    clips: Mapped[list[Clip]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Clip.rank"
    )


# --- 3. source_videos -------------------------------------------------------------------
class SourceVideo(TimestampMixin, Base):
    """The original uploaded file and its probed metadata."""

    __tablename__ = "source_videos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    # "upload" (browser → storage) or "url" (imported by a worker from source_url).
    source_kind: Mapped[str] = mapped_column(
        String(20), default="upload", server_default="upload", nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    upload_status: Mapped[UploadStatus] = mapped_column(
        _enum(UploadStatus, "upload_status"), default=UploadStatus.PENDING, nullable=False
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Float)
    video_codec: Mapped[str | None] = mapped_column(String(50))
    has_audio: Mapped[bool | None] = mapped_column(Boolean)
    probe: Mapped[JsonDict] = mapped_column(default=dict, nullable=False)  # raw ffprobe output
    thumbnail_key: Mapped[str | None] = mapped_column(String(512))
    error_message: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="source_video")


# --- 4. processing_jobs -----------------------------------------------------------------
class ProcessingJob(TimestampMixin, Base):
    """One run of the pipeline for a project. Stages are idempotent and individually retried.

    `stages` holds per-stage bookkeeping:
        {"TRANSCRIBING": {"status": "done", "attempts": 1, "started_at": ..., "finished_at": ...,
                          "error": null, "outputs": {...}}}
    `lease_owner` / `lease_expires_at` implement a lease so that two workers never run the same
    job concurrently, and a crashed worker's job is picked up again once the lease expires.
    """

    __tablename__ = "processing_jobs"
    __table_args__ = (Index("ix_jobs_state_lease", "state", "lease_expires_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[ProjectState] = mapped_column(
        _enum(ProjectState, "project_state"), default=ProjectState.CREATED, nullable=False
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0..1
    stages: Mapped[JsonDict] = mapped_column(default=dict, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(200))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="jobs")


# --- 5./6. transcripts + transcript_segments --------------------------------------------
class Transcript(TimestampMixin, Base):
    """Speech-to-text output for a source video (provider-agnostic)."""

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str | None] = mapped_column(String(16))
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    has_word_timestamps: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_speakers: Mapped[bool] = mapped_column(Boolean, nullable=False)
    raw_key: Mapped[str | None] = mapped_column(String(512))  # raw provider response in storage

    segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan", order_by="TranscriptSegment.idx"
    )


class TranscriptSegment(Base):
    """A sentence-level segment. `words` = [{"w": str, "s": float, "e": float, "p": float}]."""

    __tablename__ = "transcript_segments"
    __table_args__ = (UniqueConstraint("transcript_id", "idx"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    words: Mapped[list[Any]] = mapped_column(default=list, nullable=False)

    transcript: Mapped[Transcript] = relationship(back_populates="segments")


# --- video_analyses (architecture addition) ---------------------------------------------
class VideoAnalysis(TimestampMixin, Base):
    """Structured full-video understanding (PRD §5.3): topics, sections, moments."""

    __tablename__ = "video_analyses"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)  # analysis prompt version
    analysis: Mapped[JsonDict] = mapped_column(nullable=False)


# --- 7. candidates ----------------------------------------------------------------------
class Candidate(TimestampMixin, Base):
    """A potential clip proposed by the clipping engine, with its editorial scores."""

    __tablename__ = "candidates"
    __table_args__ = (Index("ix_candidates_project_score", "project_id", "total_score"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    scores: Mapped[JsonDict] = mapped_column(nullable=False)  # per-signal 0..10
    total_score: Mapped[float] = mapped_column(Float, nullable=False)  # weighted 0..100
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejected_reason: Mapped[str | None] = mapped_column(String(200))


# --- 8. clips ---------------------------------------------------------------------------
class Clip(TimestampMixin, Base):
    """A finished (or in-progress) short-form video."""

    __tablename__ = "clips"
    __table_args__ = (UniqueConstraint("project_id", "rank"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="SET NULL")
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ClipStatus] = mapped_column(
        _enum(ClipStatus, "clip_status"), default=ClipStatus.PLANNED, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200))
    hook: Mapped[str | None] = mapped_column(String(300))
    alt_titles: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    social_caption: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    style: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    edit_plan: Mapped[JsonDict] = mapped_column(default=dict, nullable=False)
    # What the viewer changed by hand, kept apart from `edit_plan` so re-planning never
    # discards it: the AI's decision is regenerated, the human's correction survives.
    corrections: Mapped[JsonDict] = mapped_column(default=dict, nullable=False)
    qa_report: Mapped[JsonDict] = mapped_column(default=dict, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="clips")
    assets: Mapped[list[ClipAsset]] = relationship(
        back_populates="clip", cascade="all, delete-orphan"
    )


# --- 9. clip_assets ---------------------------------------------------------------------
class ClipAsset(Base):
    """A file produced for a clip. Only `is_final=True` assets that passed QA are served."""

    __tablename__ = "clip_assets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    clip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clips.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[AssetKind] = mapped_column(_enum(AssetKind, "asset_kind"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    clip: Mapped[Clip] = relationship(back_populates="assets")


# --- 10. brand_presets ------------------------------------------------------------------
class BrandPreset(TimestampMixin, Base):
    """User-defined caption/title look. Kept minimal for the MVP (PRD §13)."""

    __tablename__ = "brand_presets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    style: Mapped[str] = mapped_column(String(50), nullable=False)
    font_family: Mapped[str | None] = mapped_column(String(100))
    primary_color: Mapped[str | None] = mapped_column(String(9))
    accent_color: Mapped[str | None] = mapped_column(String(9))


# --- 11. usage_records ------------------------------------------------------------------
class UsageRecord(Base):
    """Append-only credit ledger, plus the real provider cost of each operation."""

    __tablename__ = "usage_records"
    __table_args__ = (Index("ix_usage_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL")
    )
    kind: Mapped[UsageKind] = mapped_column(_enum(UsageKind, "usage_kind"), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)  # signed: grants > 0
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# --- 12. subscriptions ------------------------------------------------------------------
class Subscription(TimestampMixin, Base):
    """Subscription mirrored from the payment provider (provider chosen in Milestone 5)."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[Plan] = mapped_column(_enum(Plan, "plan"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        _enum(SubscriptionStatus, "subscription_status"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- 13. waitlist_signups ---------------------------------------------------------------
class WaitlistSignup(Base):
    """A pre-launch signup.

    Deliberately not tied to `users`: nobody has an account yet. The only personal data
    stored is the email address itself — the signup's IP is kept as a keyed hash, which is
    enough to spot one machine spamming the form but cannot be turned back into an address.
    """

    __tablename__ = "waitlist_signups"
    __table_args__ = (Index("ix_waitlist_created", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)  # lowercased
    referral_code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    referred_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("waitlist_signups.id", ondelete="SET NULL")
    )
    source: Mapped[str | None] = mapped_column(String(60))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
