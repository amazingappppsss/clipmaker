"""Import a video from a link (YouTube for now) — interface + yt-dlp implementation.

Only `https` links to allow-listed hosts are accepted, so the importer can never be pointed at
internal addresses. Users must confirm they own the video or have permission (checked by the
service layer). The feature has a kill switch: `ENABLE_URL_IMPORT=false`.

YouTube sometimes blocks downloads from data-centre IPs ("confirm you're not a bot"). That is
reported as `source_blocked` with a clear message suggesting a file upload — never a fake success.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

YOUTUBE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
)
#: Twitch VODs and clips. Where stream clippers actually work — a gaming clipper has a Twitch
#: link, not a YouTube one, and refusing it made the whole audience unreachable.
TWITCH_HOSTS = frozenset({"twitch.tv", "www.twitch.tv", "m.twitch.tv", "clips.twitch.tv"})
ALLOWED_HOSTS = YOUTUBE_HOSTS | TWITCH_HOSTS


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
        UrlImportError("unsupported_url"): anything that is not an https YouTube or Twitch link.
    """
    candidate = url.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS:
        raise UrlImportError(
            "unsupported_url", "Paste a YouTube or Twitch link (a video, a VOD or a clip)."
        )
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise UrlImportError("unsupported_url", "That link format isn't supported.")
    return candidate


def is_twitch(url: str) -> bool:
    """Whether this link is Twitch (pure). Apify's actor is YouTube-only, so it is skipped."""
    return (urlparse(url).hostname or "").lower() in TWITCH_HOSTS


class UrlImporter(Protocol):
    """Looks up and downloads remote videos."""

    def inspect(self, url: str) -> RemoteVideo:
        """Fetch title/duration without downloading."""
        ...

    def download(self, url: str, dest_dir: Path, heartbeat: Callable[[], None]) -> Path:
        """Download the video (with audio) as an MP4 into `dest_dir` and return its path."""
        ...

    def handles(self, url: str) -> bool:
        """Whether this importer can fetch this link at all."""
        ...

    @property
    def cheap_inspect(self) -> bool:
        """Whether `inspect` is cheap enough to run inside an API request."""
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

    def handles(self, url: str) -> bool:
        """Every allow-listed host: yt-dlp speaks YouTube and Twitch alike."""
        return True

    @property
    def cheap_inspect(self) -> bool:
        """Reading a page of metadata takes a second or two and costs nothing."""
        return True

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


# --- Apify (managed downloader with its own unblocked infrastructure) -----------------------
_QUALITY_SUFFIX = re.compile(r"\s*\((?:\d{3,4}p|audio)[^)]*\)\s*\.\w+$", re.IGNORECASE)
_DOWNLOAD_CHUNK = 1024 * 1024


class ApifyImporter:
    """UrlImporter that asks an Apify actor to fetch the video, then streams its short-lived link.

    Default actor: `coder2077~youtube-video-downloader` (input `{"urls": [...], "format": "1080p"}`,
    output items with `ok`, `duration`, `filename`, `download_url`, `error`). The download link is
    valid for ~5 minutes and a few opens, so `download` streams it to disk immediately.
    """

    def __init__(
        self,
        token: str,
        actor: str,
        video_format: str = "1080p",
        base_url: str = "https://api.apify.com",
        client: Any = None,
        run_timeout_seconds: int = 240,
        download_client: Any = None,
        inspect_timeout_seconds: int = 30,
    ) -> None:
        import httpx

        self._actor = actor
        self._format = video_format
        self._run_timeout = run_timeout_seconds
        self._inspect_timeout = min(inspect_timeout_seconds, run_timeout_seconds)
        self._client = client or httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(run_timeout_seconds + 30, connect=15.0),
            follow_redirects=True,
        )
        # Separate client WITHOUT the Apify token: the file link is on a third-party host.
        self._download_client = download_client or httpx.Client(
            timeout=httpx.Timeout(600.0, connect=15.0), follow_redirects=True
        )

    def _run(self, url: str, timeout: int | None = None) -> dict[str, Any]:
        import httpx

        budget = timeout or self._run_timeout
        try:
            response = self._client.post(
                f"/v2/acts/{self._actor}/run-sync-get-dataset-items",
                params={"timeout": budget},
                json={"urls": [url], "format": self._format},
                timeout=budget + 30,
            )
        except httpx.HTTPError as exc:
            raise UrlImportError(
                "source_network", "Couldn't reach the download service.", retryable=True
            ) from exc
        if response.status_code in (401, 403):
            raise UrlImportError("importer_unavailable", "Download service key is invalid.")
        if response.status_code == 402:
            raise UrlImportError("importer_unavailable", "Download service has no credit left.")
        if response.status_code >= 400:
            raise UrlImportError(
                "source_network",
                f"Download service error {response.status_code}.",
                retryable=response.status_code >= 500 or response.status_code == 408,
            )
        items = response.json()
        item = items[0] if isinstance(items, list) and items else None
        if not isinstance(item, dict):
            raise UrlImportError(
                "source_failed", "The download service returned no result.", retryable=True
            )
        if not item.get("ok"):
            raise _classify(str(item.get("error") or "unknown error"))
        if not item.get("download_url"):
            raise UrlImportError(
                "source_failed", "The download service returned no file.", retryable=True
            )
        return item

    def inspect(self, url: str) -> RemoteVideo:
        # Short budget: this runs inside an API request, with somebody watching a spinner.
        # The actor's run *is* the download preparation, so a long video can take minutes.
        item = self._run(url, timeout=self._inspect_timeout)
        filename = str(item.get("filename") or "YouTube video")
        title = _QUALITY_SUFFIX.sub("", filename).strip() or "YouTube video"
        return RemoteVideo(
            url=str(item.get("url") or url),
            title=title[:200],
            duration_seconds=float(item.get("duration") or 0.0),
            thumbnail_url=(item.get("thumbnails") or {}).get("max"),
            is_live=False,
        )

    def handles(self, url: str) -> bool:
        """YouTube only. The configured actor downloads YouTube videos; given a Twitch VOD it
        burns a run and a few minutes before failing, so it is skipped rather than tried."""
        return not is_twitch(url)

    @property
    def cheap_inspect(self) -> bool:
        """No: the actor fetches the whole video to answer, which costs a run and minutes."""
        return False

    def download(self, url: str, dest_dir: Path, heartbeat: Callable[[], None]) -> Path:
        import httpx

        item = self._run(url)  # fresh link: they expire after ~5 minutes
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "source.mp4"
        last_beat = 0
        try:
            with self._download_client.stream("GET", str(item["download_url"])) as r:
                if r.status_code >= 400:
                    raise UrlImportError(
                        "source_failed", f"Download link failed ({r.status_code}).", retryable=True
                    )
                with path.open("wb") as fh:
                    for chunk in r.iter_bytes(_DOWNLOAD_CHUNK):
                        fh.write(chunk)
                        last_beat += len(chunk)
                        if last_beat >= 64 * _DOWNLOAD_CHUNK:
                            heartbeat()
                            last_beat = 0
        except httpx.HTTPError as exc:
            raise UrlImportError(
                "source_network", "The download was interrupted.", retryable=True
            ) from exc
        if path.stat().st_size == 0:
            raise UrlImportError(
                "source_failed", "The download produced an empty file.", retryable=True
            )
        return path


# --- provider chain ---------------------------------------------------------------------------
# Errors about the *video itself* — another provider cannot fix these, so the chain stops.
_FINAL_CODES = frozenset(
    {"source_private", "source_restricted", "source_unavailable", "unsupported_url"}
)


class FallbackImporter:
    """Tries importers in order; moves on when one is blocked or broken.

    Downloading and looking up are ordered differently on purpose. For a *download* the
    managed service goes first: YouTube blocks data-centre IPs, so yt-dlp alone fails on a
    server. For a *lookup* it goes last, because the managed actor answers by fetching the
    whole video — minutes of waiting and a paid run, inside the API request that somebody is
    watching a spinner through, before the download then pays for it a second time.
    """

    def __init__(self, importers: list[UrlImporter]) -> None:
        if not importers:
            raise ValueError("FallbackImporter needs at least one importer")
        self._importers = importers

    def handles(self, url: str) -> bool:
        return any(i.handles(url) for i in self._importers)

    @property
    def cheap_inspect(self) -> bool:
        return any(i.cheap_inspect for i in self._importers)

    def _order(self, for_inspect: bool) -> list[UrlImporter]:
        if not for_inspect:
            return self._importers
        return [i for i in self._importers if i.cheap_inspect] + [
            i for i in self._importers if not i.cheap_inspect
        ]

    def _attempt(
        self, url: str, call: Callable[[UrlImporter], Any], *, for_inspect: bool = False
    ) -> Any:
        last: UrlImportError | None = None
        for importer in self._order(for_inspect):
            if not importer.handles(url):
                continue
            try:
                return call(importer)
            except UrlImportError as exc:
                if exc.code in _FINAL_CODES:
                    raise
                last = exc
        if last is None:
            # Every provider sat this one out: the link is allowed but nothing configured can
            # fetch it. Say so, rather than reporting a download failure that never happened.
            raise UrlImportError(
                "unsupported_url", "We can't import that link yet. Upload the file instead."
            )
        raise last

    def inspect(self, url: str) -> RemoteVideo:
        result: RemoteVideo = self._attempt(url, lambda i: i.inspect(url), for_inspect=True)
        return result

    def download(self, url: str, dest_dir: Path, heartbeat: Callable[[], None]) -> Path:
        result: Path = self._attempt(url, lambda i: i.download(url, dest_dir, heartbeat))
        return result


def build_url_importer(settings: Any) -> UrlImporter:
    """Importer chain from settings: URL_IMPORT_PROVIDERS="apify,ytdlp" (order matters).
    Apify is skipped when no APIFY_TOKEN is configured."""
    chain: list[UrlImporter] = []
    for name in [p.strip() for p in str(settings.url_import_providers).split(",") if p.strip()]:
        if name == "apify":
            token = settings.apify_token.get_secret_value() if settings.apify_token else ""
            if token:
                chain.append(
                    ApifyImporter(
                        token,
                        settings.apify_youtube_actor,
                        f"{settings.url_import_max_height}p",
                        inspect_timeout_seconds=settings.url_import_timeout_seconds,
                    )
                )
        elif name == "ytdlp":
            chain.append(
                YtDlpImporter(settings.url_import_max_height, settings.url_import_timeout_seconds)
            )
    # yt-dlp is the only provider that handles Twitch, so a chain without it would refuse
    # every VOD. Always keep it as the last resort.
    if not any(isinstance(i, YtDlpImporter) for i in chain):
        chain.append(
            YtDlpImporter(settings.url_import_max_height, settings.url_import_timeout_seconds)
        )
    return chain[0] if len(chain) == 1 else FallbackImporter(chain)
