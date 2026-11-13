"""Import a video from a link (YouTube for now) — interface + yt-dlp implementation.

Only `https` links to allow-listed hosts are accepted, so the importer can never be pointed at
internal addresses. Users must confirm they own the video or have permission (checked by the
service layer). The feature has a kill switch: `ENABLE_URL_IMPORT=false`.

YouTube sometimes blocks downloads from data-centre IPs ("confirm you're not a bot"). That is
reported as `source_blocked` with a clear message suggesting a file upload — never a fake success.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

ALLOWED_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
)


class UrlImportError(Exception):
    """`code` is stable for the API/UI; `retryable` guides the pipeline."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class RemoteVideo:
    """Metadata of a remote video, fetched without downloading it."""

    url: str
    title: str
    duration_seconds: float
    thumbnail_url: str | None
    is_live: bool


def validate_url(url: str) -> str:
    """Normalise and allow-list a link (pure; unit-tested).

    Raises:
        UrlImportError("unsupported_url"): anything that is not an https YouTube link.
    """
    candidate = url.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS:
        raise UrlImportError("unsupported_url", "Paste a YouTube link (youtube.com or youtu.be).")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise UrlImportError("unsupported_url", "That link format isn't supported.")
    return candidate


class UrlImporter(Protocol):
    """Looks up and downloads remote videos."""

    def inspect(self, url: str) -> RemoteVideo:
        """Fetch title/duration without downloading."""
        ...

    def download(self, url: str, dest_dir: Path, heartbeat: Callable[[], None]) -> Path:
        """Download the video (with audio) as an MP4 into `dest_dir` and return its path."""
        ...


def _classify(message: str) -> UrlImportError:
    """Map yt-dlp error text to a stable, user-readable error (pure; unit-tested)."""
    text = message.lower()
    if "sign in to confirm" in text or "not a bot" in text or "http error 429" in text:
        return UrlImportError(
            "source_blocked",
            "YouTube is blocking automatic downloads right now. Please download the video "
            "(YouTube Studio → Content → ⋮ → Download) and upload the file instead.",
            retryable=True,
        )
    if "private video" in text or "members-only" in text or "sign in to view" in text:
        return UrlImportError("source_private", "This video is private or members-only.")
    if "age" in text and "restrict" in text:
        return UrlImportError("source_restricted", "Age-restricted videos can't be imported.")
    if "unavailable" in text or "removed" in text or "does not exist" in text:
        return UrlImportError("source_unavailable", "This video is unavailable.")
    if "timed out" in text or "connection" in text or "temporary failure" in text:
        return UrlImportError(
            "source_network", "Couldn't reach YouTube. Try again shortly.", retryable=True
        )
    return UrlImportError(
        "source_failed", "We couldn't import this video. Try uploading the file instead."
    )


class YtDlpImporter:
    """UrlImporter backed by the yt-dlp library (imported lazily: heavy, optional at API import)."""

    def __init__(self, max_height: int = 1080, socket_timeout: int = 30) -> None:
        self._max_height = max_height
        self._socket_timeout = socket_timeout

    def _options(self, extra: dict[str, Any]) -> dict[str, Any]:
        return {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": self._socket_timeout,
            "retries": 3,
            **extra,
        }

    def inspect(self, url: str) -> RemoteVideo:
        import yt_dlp

        try:
            with yt_dlp.YoutubeDL(self._options({"skip_download": True})) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            raise _classify(str(exc)) from exc
        if not isinstance(info, dict):
            raise UrlImportError("source_failed", "We couldn't read this link.")
        return RemoteVideo(
            url=str(info.get("webpage_url") or url),
            title=str(info.get("title") or "YouTube video")[:200],
            duration_seconds=float(info.get("duration") or 0.0),
            thumbnail_url=info.get("thumbnail"),
            is_live=bool(info.get("is_live")),
        )

    def download(self, url: str, dest_dir: Path, heartbeat: Callable[[], None]) -> Path:
        import yt_dlp

        dest_dir.mkdir(parents=True, exist_ok=True)
        h = self._max_height

        def progress(_: dict[str, Any]) -> None:
            heartbeat()

        options = self._options(
            {
                # Best MP4-compatible streams up to max height, merged by FFmpeg into one MP4.
                "format": (
                    f"bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}][ext=mp4]"
                    f"/bv*[height<={h}]+ba/b"
                ),
                "merge_output_format": "mp4",
                "outtmpl": str(dest_dir / "source.%(ext)s"),
                "progress_hooks": [progress],
            }
        )
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as exc:
            raise _classify(str(exc)) from exc
        files = sorted(dest_dir.glob("source.*"), key=lambda p: p.stat().st_size, reverse=True)
        files = [f for f in files if f.suffix in (".mp4", ".mkv", ".webm", ".mov")]
        if not files:
            raise UrlImportError(
                "source_failed", "The download produced no video file.", retryable=True
            )
        return files[0]
