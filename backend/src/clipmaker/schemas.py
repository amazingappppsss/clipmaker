"""Pydantic API contract.

This module is the single source of truth for shapes shared with the frontend:
`scripts/gen-types.sh` exports the OpenAPI schema and generates `common/types/api.ts`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from clipmaker.core.enums import (
    ClipStatus,
    ContentCategory,
    Plan,
    ProjectState,
    UploadStatus,
    UsageKind,
    VideoStyle,
)

ClipCount = Literal["auto", 3, 5, 10]
LanguageCode = Annotated[str, StringConstraints(pattern=r"^(auto|[a-z]{2}(-[A-Z]{2})?)$")]

ALLOWED_VIDEO_TYPES: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
}


class ApiModel(BaseModel):
    """Base for response models built from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


# --- Projects ----------------------------------------------------------------------------
class ProjectSettings(BaseModel):
    """User choices for a project (PRD §4 step 2). Every field has a sensible default."""

    model_config = ConfigDict(extra="forbid")

    category: ContentCategory = ContentCategory.AUTO
    language: LanguageCode = "auto"
    clip_count: ClipCount = "auto"
    style: VideoStyle = VideoStyle.AUTO


class ProjectCreate(BaseModel):
    """POST /projects body."""

    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class ImportRequest(BaseModel):
    """POST /projects/import body: create a project from a video link."""

    model_config = ConfigDict(extra="forbid")

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=2048)]
    rights_confirmed: bool
    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class SourceVideoOut(ApiModel):
    """Public view of the source video (uploaded or imported from a link)."""

    source_kind: str
    source_url: str | None
    original_filename: str
    size_bytes: int
    upload_status: UploadStatus
    duration_seconds: float | None
    width: int | None
    height: int | None
    has_audio: bool | None
    error_message: str | None


class ProjectOut(ApiModel):
    """A project as returned by the API."""

    id: uuid.UUID
    title: str
    state: ProjectState
    settings: ProjectSettings
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    source_video: SourceVideoOut | None
    thumbnail_url: str | None = None
    # Short-lived signed URL for in-browser preview of picked moments (inline playback).
    source_video_url: str | None = None
    clip_count: int = 0


class ProjectList(BaseModel):
    """Paginated project list."""

    items: list[ProjectOut]
    next_cursor: str | None


# --- Uploads -----------------------------------------------------------------------------
class UploadRequest(BaseModel):
    """POST /projects/{id}/upload body: what the client intends to upload."""

    model_config = ConfigDict(extra="forbid")

    filename: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    content_type: str
    size_bytes: int = Field(gt=0)


class UploadTicket(BaseModel):
    """Signed instructions for uploading the file directly to storage."""

    upload_url: str
    method: str
    headers: dict[str, str]
    expires_in: int


# --- Clips -------------------------------------------------------------------------------
class ClipOut(ApiModel):
    """A selected clip: its moment in the source video plus publishing metadata."""

    id: uuid.UUID
    rank: int
    status: ClipStatus
    title: str | None
    hook: str | None
    alt_titles: list[str]
    social_caption: str | None
    hashtags: list[str]
    duration_seconds: float | None
    start_seconds: float | None = None
    end_seconds: float | None = None
    transcript: str | None = None
    score: float | None = None


StageRunStatus = Literal["pending", "running", "done", "failed"]


class StageStatusOut(BaseModel):
    """One pipeline stage as recorded by the runner."""

    stage: ProjectState
    status: StageRunStatus
    attempts: int


class JobStatusOut(BaseModel):
    """GET /projects/{id}/status — real progress, never simulated."""

    project_state: ProjectState
    progress: float
    stages: list[StageStatusOut]
    message: str | None
    started_at: datetime | None
    completed_at: datetime | None


# --- Account -----------------------------------------------------------------------------
class UsageRecordOut(ApiModel):
    """One ledger entry."""

    id: uuid.UUID
    kind: UsageKind
    credits: int
    description: str
    project_id: uuid.UUID | None
    created_at: datetime


class PlanOut(BaseModel):
    """Plan catalog entry."""

    plan: Plan
    name: str
    monthly_credits: int
    price_usd_cents: int
    watermark: bool


class AccountUsage(BaseModel):
    """GET /account/usage response."""

    email: str | None
    plan: Plan
    credits_balance: int
    history: list[UsageRecordOut]
    plans: list[PlanOut]


# --- Misc --------------------------------------------------------------------------------
class ErrorOut(BaseModel):
    """Every error response has this shape."""

    code: str
    message: str


class HealthOut(BaseModel):
    """GET /health response."""

    status: Literal["ok", "degraded"]
    database: bool
    redis: bool
    version: str
    # Which deploy is running, and whether processing has what it needs (never key values).
    commit: str | None = None
    transcription_ready: bool = False
    llm_ready: bool = False
    link_import_ready: bool = False
    # Base address used in upload/download links for this request (diagnostics).
    storage_base_url: str | None = None
    # True when stored videos live on a persistent volume (survive redeploys).
    storage_persistent: bool | None = None


class DevTokenRequest(BaseModel):
    """POST /dev/token body (development only)."""

    email: Annotated[str, StringConstraints(min_length=3, max_length=320)]


class DevTokenOut(BaseModel):
    """A locally minted access token (development only)."""

    access_token: str
    user_id: uuid.UUID
