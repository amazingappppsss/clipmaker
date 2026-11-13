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


class SourceVideoOut(ApiModel):
    """Public view of the uploaded source video."""

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
    """A generated clip (populated from Milestone 2 onwards)."""

    id: uuid.UUID
    rank: int
    status: ClipStatus
    title: str | None
    hook: str | None
    alt_titles: list[str]
    social_caption: str | None
    hashtags: list[str]
    duration_seconds: float | None


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
    price_inr: int
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


class DevTokenRequest(BaseModel):
    """POST /dev/token body (development only)."""

    email: Annotated[str, StringConstraints(min_length=3, max_length=320)]


class DevTokenOut(BaseModel):
    """A locally minted access token (development only)."""

    access_token: str
    user_id: uuid.UUID
