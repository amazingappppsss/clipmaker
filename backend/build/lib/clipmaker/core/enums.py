"""Domain enumerations shared by DB models, API schemas and the pipeline.

String values are persisted in PostgreSQL and exposed to the frontend — treat them as a
public contract: add new values freely, but never rename or remove existing ones.
"""

from __future__ import annotations

from enum import StrEnum


class ProjectState(StrEnum):
    """Lifecycle of a project; mirrors the pipeline stages in PRD §8."""

    CREATED = "CREATED"  # project exists, waiting for an upload
    UPLOADED = "UPLOADED"  # source video verified, ready to process
    INGESTING = "INGESTING"
    TRANSCRIBING = "TRANSCRIBING"
    UNDERSTANDING = "UNDERSTANDING"
    SELECTING = "SELECTING"
    EDITING = "EDITING"
    RENDERING = "RENDERING"
    QUALITY_CHECK = "QUALITY_CHECK"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# The ordered processing stages a job walks through.
PIPELINE_STAGES: tuple[ProjectState, ...] = (
    ProjectState.INGESTING,
    ProjectState.TRANSCRIBING,
    ProjectState.UNDERSTANDING,
    ProjectState.SELECTING,
    ProjectState.EDITING,
    ProjectState.RENDERING,
    ProjectState.QUALITY_CHECK,
)

TERMINAL_STATES: frozenset[ProjectState] = frozenset(
    {
        ProjectState.COMPLETED,
        ProjectState.NEEDS_REVIEW,
        ProjectState.FAILED,
        ProjectState.CANCELLED,
    }
)


class UploadStatus(StrEnum):
    """State of the source-video upload."""

    PENDING = "pending"  # signed URL issued, bytes not yet confirmed
    VERIFIED = "verified"  # object exists, size matches, ffprobe accepted it
    FAILED = "failed"


class ContentCategory(StrEnum):
    """User-selected content category (PRD §4 step 2)."""

    AUTO = "auto"
    PODCAST = "podcast"
    INTERVIEW = "interview"
    EDUCATIONAL = "educational"
    BUSINESS = "business"
    GAMING = "gaming"


class VideoStyle(StrEnum):
    """Visual style for captions and titles."""

    AUTO = "auto"
    MODERN_CREATOR = "modern_creator"
    MINIMAL_PROFESSIONAL = "minimal_professional"


class ClipStatus(StrEnum):
    """Lifecycle of a single generated clip."""

    PLANNED = "planned"
    RENDERING = "rendering"
    QA = "qa"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class AssetKind(StrEnum):
    """Kinds of files tracked in `clip_assets`."""

    VIDEO = "video"
    THUMBNAIL = "thumbnail"
    SUBTITLES = "subtitles"
    EDIT_PLAN = "edit_plan"


class Plan(StrEnum):
    """Subscription plans. Prices live in services/billing (USD, international launch)."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"


class UsageKind(StrEnum):
    """Ledger entry types in `usage_records`."""

    GRANT = "grant"  # credits added (signup trial, plan renewal)
    DEBIT = "debit"  # credits consumed by processing
    REFUND = "refund"  # credits returned after a failed job


class SubscriptionStatus(StrEnum):
    """Status mirrored from the payment provider."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
