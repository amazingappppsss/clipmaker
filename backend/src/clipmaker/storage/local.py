"""Filesystem storage with HMAC-signed URLs — for development and tests only.

Signed URLs point at `/storage/local/{key}` on this API (see api/local_storage.py), which
verifies the signature, expiry and declared size before reading or writing bytes. This mirrors
the presigned-URL flow of S3/R2 so the frontend code path is identical in every environment.
"""

from __future__ import annotations

import hashlib
import hmac
import shutil
import time
from contextvars import ContextVar
from pathlib import Path
from urllib.parse import quote, urlencode

from clipmaker.storage.base import ObjectInfo, SignedUpload

DEFAULT_BASE_URL = "http://localhost:8000"

# Set per request by the API (main.py) from the Host / X-Forwarded-* headers, so signed URLs
# point back at whatever public address the browser used when API_PUBLIC_URL is not configured.
request_base_url: ContextVar[str | None] = ContextVar("request_base_url", default=None)


class InvalidSignatureError(Exception):
    """Signature missing, wrong, or expired."""


class LocalStorage:
    """Stores objects under `root`; keys map to relative paths."""

    def __init__(
        self, root: Path, signing_key: bytes, public_base_url: str | None, ttl: int
    ) -> None:
        self._root = root.resolve()
        self._key = signing_key
        self._base = public_base_url.rstrip("/") if public_base_url else None
        self._ttl = ttl
        self._root.mkdir(parents=True, exist_ok=True)

    # --- path safety -------------------------------------------------------------------
    def path_for(self, key: str) -> Path:
        """Resolve a key to a path, refusing anything that escapes the storage root."""
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root) or path == self._root:
            raise ValueError("invalid storage key")
        return path

    # --- signing -----------------------------------------------------------------------
    def _signature(self, method: str, key: str, expires: int, size: int | None) -> str:
        message = f"{method}\n{key}\n{expires}\n{size if size is not None else ''}"
        return hmac.new(self._key, message.encode(), hashlib.sha256).hexdigest()

    def _signed_url(self, method: str, key: str, size: int | None, extra: dict[str, str]) -> str:
        expires = int(time.time()) + self._ttl
        params = {"expires": str(expires), "sig": self._signature(method, key, expires, size)}
        if size is not None:
            params["size"] = str(size)
        params.update(extra)
        return f"{self.base_url()}/storage/local/{quote(key)}?{urlencode(params)}"

    def base_url(self) -> str:
        """Where signed links point.

        During an API request the browser's own address is used: it is always reachable, while a
        hand-typed absolute API_PUBLIC_URL can be stale or a placeholder. A relative setting
        (e.g. "/api" behind the dev proxy) still wins, and outside requests (workers) the setting
        or localhost is used.
        """
        from_request = request_base_url.get()
        if self._base and (self._base.startswith("/") or not from_request):
            return self._base
        return from_request or self._base or DEFAULT_BASE_URL

    def verify(self, method: str, key: str, expires: int, sig: str, size: int | None) -> None:
        """Raise InvalidSignatureError unless the URL was signed by us and is still valid."""
        if expires < int(time.time()):
            raise InvalidSignatureError("signed URL expired")
        expected = self._signature(method, key, expires, size)
        if not hmac.compare_digest(expected, sig):
            raise InvalidSignatureError("bad signature")

    # --- ObjectStorage -----------------------------------------------------------------
    def presign_upload(self, key: str, content_type: str, size_bytes: int) -> SignedUpload:
        url = self._signed_url("PUT", key, size_bytes, {})
        return SignedUpload(
            url=url, method="PUT", headers={"Content-Type": content_type}, expires_in=self._ttl
        )

    def presign_download(self, key: str, filename: str | None = None) -> str:
        extra = {"filename": filename} if filename else {}
        return self._signed_url("GET", key, None, extra)

    def head(self, key: str) -> ObjectInfo | None:
        path = self.path_for(key)
        if not path.is_file():
            return None
        return ObjectInfo(key=key, size_bytes=path.stat().st_size, content_type=None)

    def upload_file(self, local_path: Path, key: str, content_type: str) -> ObjectInfo:
        dest = self.path_for(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        shutil.copyfile(local_path, tmp)
        tmp.replace(dest)  # atomic: readers never see a half-written object
        return ObjectInfo(key=key, size_bytes=dest.stat().st_size, content_type=content_type)

    def download_file(self, key: str, local_path: Path) -> None:
        src = self.path_for(key)
        if not src.is_file():
            raise FileNotFoundError(key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, local_path)

    def delete_prefix(self, prefix: str) -> int:
        target = self.path_for(prefix.rstrip("/"))
        if not target.exists():
            return 0
        if target.is_file():  # an exact key (S3 prefix semantics cover single objects too)
            target.unlink()
            return 1
        count = sum(1 for p in target.rglob("*") if p.is_file())
        shutil.rmtree(target)
        return count

    def media_source(self, key: str) -> str:
        return str(self.path_for(key))
