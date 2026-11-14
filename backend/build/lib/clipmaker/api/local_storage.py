"""Signed upload/download endpoints for LocalStorage (development and tests only).

Production uses S3/R2 presigned URLs and never reaches these routes; they are only mounted
when STORAGE_BACKEND=local (which Settings forbids in production).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse, Response

from clipmaker.core.errors import AppError, NotFoundError, ValidationFailedError
from clipmaker.storage.factory import get_storage
from clipmaker.storage.local import InvalidSignatureError, LocalStorage

router = APIRouter(prefix="/storage/local", tags=["local-storage"])

_CHUNK = 1024 * 1024


class ForbiddenError(AppError):
    """Bad or expired signature."""

    status_code = 403
    code = "forbidden"


def _local() -> LocalStorage:
    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise NotFoundError("Not found")
    return storage


LocalStore = Annotated[LocalStorage, Depends(_local)]


@router.put(
    "/{key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def put_object(
    key: str,
    request: Request,
    storage: LocalStore,
    expires: Annotated[int, Query()],
    sig: Annotated[str, Query()],
    size: Annotated[int, Query()],
) -> None:
    """Stream the request body to disk, refusing anything larger than the signed size."""
    try:
        storage.verify("PUT", key, expires, sig, size)
    except InvalidSignatureError as exc:
        raise ForbiddenError(str(exc)) from exc

    dest = storage.path_for(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(f"{dest}.part")
    written = 0
    try:
        with tmp.open("wb") as fh:
            async for chunk in request.stream():
                written += len(chunk)
                if written > size:
                    raise ValidationFailedError("Upload exceeds declared size", code="too_large")
                fh.write(chunk)
        if written != size:
            raise ValidationFailedError("Upload incomplete", code="upload_incomplete")
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


@router.get("/{key:path}")
def get_object(
    key: str,
    storage: LocalStore,
    expires: Annotated[int, Query()],
    sig: Annotated[str, Query()],
    filename: str | None = None,
) -> FileResponse:
    """Serve a stored file (supports HTTP Range for video seeking)."""
    try:
        storage.verify("GET", key, expires, sig, None)
    except InvalidSignatureError as exc:
        raise ForbiddenError(str(exc)) from exc
    path = storage.path_for(key)
    if not path.is_file():
        raise NotFoundError("Not found")
    return FileResponse(
        path, filename=filename, content_disposition_type="attachment" if filename else "inline"
    )
