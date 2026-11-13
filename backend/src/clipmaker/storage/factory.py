"""Build the configured ObjectStorage implementation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from clipmaker.core.config import StorageBackend, get_settings
from clipmaker.storage.base import ObjectStorage
from clipmaker.storage.local import LocalStorage
from clipmaker.storage.s3 import S3Storage


@lru_cache(maxsize=1)
def get_storage() -> ObjectStorage:
    """Process-wide storage instance selected by `STORAGE_BACKEND`."""
    s = get_settings()
    if s.storage_backend == StorageBackend.S3:
        assert s.s3_bucket is not None  # enforced by Settings validation
        return S3Storage(
            bucket=s.s3_bucket,
            endpoint_url=s.s3_endpoint_url,
            region=s.s3_region,
            access_key_id=s.s3_access_key_id.get_secret_value() if s.s3_access_key_id else None,
            secret_access_key=(
                s.s3_secret_access_key.get_secret_value() if s.s3_secret_access_key else None
            ),
            ttl=s.signed_url_ttl_seconds,
        )
    return LocalStorage(
        root=Path(s.local_storage_dir),
        signing_key=s.storage_signing_key.get_secret_value().encode(),
        public_base_url=s.api_public_url,
        ttl=s.signed_url_ttl_seconds,
    )
