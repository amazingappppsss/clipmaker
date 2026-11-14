"""storage/local.py — signing, expiry and path-traversal protection."""

from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from clipmaker.storage.local import InvalidSignatureError, LocalStorage


@pytest.fixture
def store(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "root", b"k" * 32, "http://api.test", ttl=60)


def _params(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_signed_upload_verifies(store: LocalStorage) -> None:
    p = _params(store.presign_upload("a/b.mp4", "video/mp4", 10).url)
    store.verify("PUT", "a/b.mp4", int(p["expires"]), p["sig"], 10)


def test_signature_bound_to_size_method_and_key(store: LocalStorage) -> None:
    p = _params(store.presign_upload("a/b.mp4", "video/mp4", 10).url)
    for method, key, size in [("PUT", "a/b.mp4", 11), ("GET", "a/b.mp4", 10), ("PUT", "a/c", 10)]:
        with pytest.raises(InvalidSignatureError):
            store.verify(method, key, int(p["expires"]), p["sig"], size)


def test_expired_signature_rejected(store: LocalStorage) -> None:
    p = _params(store.presign_download("a/b.mp4"))
    with pytest.raises(InvalidSignatureError, match="expired"):
        store.verify("GET", "a/b.mp4", int(time.time()) - 1, p["sig"], None)


@pytest.mark.parametrize("key", ["../escape", "a/../../escape", "/etc/passwd", ""])
def test_path_traversal_refused(store: LocalStorage, key: str) -> None:
    with pytest.raises(ValueError):
        store.path_for(key)


def test_upload_download_delete_prefix(store: LocalStorage, tmp_path: Path) -> None:
    src = tmp_path / "f.bin"
    src.write_bytes(b"x" * 5)
    store.upload_file(src, "users/u/projects/p/a.bin", "application/octet-stream")
    info = store.head("users/u/projects/p/a.bin")
    assert info is not None and info.size_bytes == 5
    store.download_file("users/u/projects/p/a.bin", tmp_path / "out.bin")
    assert (tmp_path / "out.bin").read_bytes() == b"x" * 5
    assert store.delete_prefix("users/u/projects/p/") == 1
    assert store.head("users/u/projects/p/a.bin") is None


def test_request_address_beats_absolute_setting(tmp_path: Path) -> None:
    """A stale/placeholder API_PUBLIC_URL must not break uploads made through the API."""
    from clipmaker.storage.local import request_base_url

    store = LocalStorage(tmp_path / "r", b"k" * 32, "https://placeholder-xxxx.example", ttl=60)
    assert store.base_url() == "https://placeholder-xxxx.example"  # worker: no request
    token = request_base_url.set("https://real.example")
    try:
        assert store.presign_upload("a.mp4", "video/mp4", 1).url.startswith("https://real.example/")
        relative = LocalStorage(tmp_path / "r2", b"k" * 32, "/api", ttl=60)
        assert relative.base_url() == "/api"
    finally:
        request_base_url.reset(token)


def test_delete_prefix_removes_a_single_file(store: LocalStorage, tmp_path: Path) -> None:
    src = tmp_path / "f.bin"
    src.write_bytes(b"x")
    store.upload_file(src, "u/p/source/original.mp4", "video/mp4")
    assert store.delete_prefix("u/p/source/original.mp4") == 1
    assert store.head("u/p/source/original.mp4") is None
    assert store.delete_prefix("u/p/source/original.mp4") == 0
