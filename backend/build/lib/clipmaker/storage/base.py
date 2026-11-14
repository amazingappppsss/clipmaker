"""Object-storage interface.

The rest of the application only depends on this Protocol, so the backend (local disk,
Cloudflare R2, AWS S3, ...) can be swapped through configuration alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SignedUpload:
    """Everything a browser needs to PUT a file directly to storage."""

    url: str
    method: str
    headers: dict[str, str]
    expires_in: int


@dataclass(frozen=True, slots=True)
class ObjectInfo:
    """Metadata of a stored object."""

    key: str
    size_bytes: int
    content_type: str | None


class ObjectStorage(Protocol):
    """Operations every storage backend must support."""

    def presign_upload(self, key: str, content_type: str, size_bytes: int) -> SignedUpload:
        """Return a short-lived URL the client can PUT exactly this object to."""
        ...

    def presign_download(self, key: str, filename: str | None = None) -> str:
        """Return a short-lived GET URL. `filename` sets Content-Disposition: attachment."""
        ...

    def head(self, key: str) -> ObjectInfo | None:
        """Metadata for `key`, or None if it does not exist."""
        ...

    def upload_file(self, local_path: Path, key: str, content_type: str) -> ObjectInfo:
        """Upload a local file (used by workers for generated assets)."""
        ...

    def download_file(self, key: str, local_path: Path) -> None:
        """Download `key` to a local path (used by workers)."""
        ...

    def delete_prefix(self, prefix: str) -> int:
        """Delete every object under `prefix`; returns the number deleted."""
        ...

    def media_source(self, key: str) -> str:
        """A path or URL that FFmpeg/FFprobe can read the object from without a full download."""
        ...


def project_prefix(user_id: str, project_id: str) -> str:
    """All objects of a project live under one prefix so deletion is complete and cheap."""
    return f"users/{user_id}/projects/{project_id}/"
