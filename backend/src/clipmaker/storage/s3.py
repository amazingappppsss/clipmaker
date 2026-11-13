"""S3-compatible storage (Cloudflare R2 in production) using presigned URLs.

Browsers upload and download directly to/from the bucket; the API never proxies video bytes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from clipmaker.storage.base import ObjectInfo, SignedUpload


class S3Storage:
    """ObjectStorage backed by a single S3-compatible bucket."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None,
        region: str,
        access_key_id: str | None,
        secret_access_key: str | None,
        ttl: int,
    ) -> None:
        self._bucket = bucket
        self._ttl = ttl
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(
                signature_version="s3v4", retries={"max_attempts": 5, "mode": "adaptive"}
            ),
        )

    def presign_upload(self, key: str, content_type: str, size_bytes: int) -> SignedUpload:
        # ContentLength is part of the signature, so the client cannot upload a different size.
        url: str = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": size_bytes,
            },
            ExpiresIn=self._ttl,
        )
        return SignedUpload(
            url=url, method="PUT", headers={"Content-Type": content_type}, expires_in=self._ttl
        )

    def presign_download(self, key: str, filename: str | None = None) -> str:
        params: dict[str, str] = {"Bucket": self._bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        url: str = self._client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=self._ttl
        )
        return url

    def head(self, key: str) -> ObjectInfo | None:
        try:
            res = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return ObjectInfo(
            key=key, size_bytes=int(res["ContentLength"]), content_type=res.get("ContentType")
        )

    def upload_file(self, local_path: Path, key: str, content_type: str) -> ObjectInfo:
        self._client.upload_file(
            str(local_path), self._bucket, key, ExtraArgs={"ContentType": content_type}
        )
        return ObjectInfo(key=key, size_bytes=local_path.stat().st_size, content_type=content_type)

    def download_file(self, key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(self._bucket, key, str(local_path))

    def delete_prefix(self, prefix: str) -> int:
        deleted = 0
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            objects = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objects:
                self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": objects})
                deleted += len(objects)
        return deleted

    def media_source(self, key: str) -> str:
        return self.presign_download(key)
