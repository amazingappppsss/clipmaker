"""Fixed-window rate limiter backed by Redis.

Fails *open* when Redis is unreachable (logged as a warning): an outage of the limiter must
not take the whole API down. Abuse protection at the edge (Cloudflare) is the second layer.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Protocol

import redis

from clipmaker.core.config import get_settings

logger = logging.getLogger(__name__)


class Counter(Protocol):
    """Minimal counter store (Redis in production, an in-memory fake in tests)."""

    def incr_window(self, key: str, window_seconds: int) -> int:
        """Increment `key` and return its value within the current window."""
        ...


class RedisCounter:
    """Counter implemented with INCR + EXPIRE in one pipeline."""

    def __init__(self, url: str) -> None:
        self._client = redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)

    def incr_window(self, key: str, window_seconds: int) -> int:
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = pipe.execute()
        return int(count)


@lru_cache(maxsize=1)
def get_counter() -> Counter:
    """Process-wide counter."""
    return RedisCounter(get_settings().redis_url)


def is_allowed(counter: Counter, subject: str, limit: int, window_seconds: int = 60) -> bool:
    """True if `subject` is under `limit` requests in the current window."""
    window = int(time.time()) // window_seconds
    try:
        return counter.incr_window(f"rl:{subject}:{window}", window_seconds) <= limit
    except redis.RedisError:
        logger.warning("rate_limiter_unavailable", extra={"subject": subject})
        return True
