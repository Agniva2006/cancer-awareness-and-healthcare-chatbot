"""Rate limiting with a Redis backend and in-memory fallback.

Phase 5 upgrade of the Phase-2 in-memory limiter: counters live in Redis so
they survive restarts and are shared across workers/instances. When Redis is
unreachable (local dev without the container, transient outage), we degrade
gracefully to the original per-process limiter — the API never hard-fails
because of the limiter's storage backend.
"""

import logging
import os
import time
from typing import Protocol

logger = logging.getLogger(__name__)

# Read env directly — this module is imported by app.core.config, so importing
# settings here would create a circular import.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_URL = os.getenv("REDIS_URL", "")


class LimiterBackend(Protocol):
    def check(self, key: str, max_attempts: int, window_minutes: int) -> bool: ...


class RedisBackend:
    """Fixed-window counter in Redis: INCR + EXPIRE (atomic enough per key)."""

    def __init__(self) -> None:
        import redis  # imported lazily; optional dependency path

        self._client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )

    def check(self, key: str, max_attempts: int, window_minutes: int) -> bool:
        window_seconds = window_minutes * 60
        now = int(time.time())
        bucket_key = f"rl:{key}:{now // window_seconds}"
        count = self._client.incr(bucket_key)
        if count == 1:
            self._client.expire(bucket_key, window_seconds + 1)
        return count <= max_attempts


class InMemoryBackend:
    """Per-process fixed-window limiter (original Phase-2 behavior)."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str, max_attempts: int, window_minutes: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_minutes * 60
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) >= max_attempts:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def reset(self) -> None:
        self._hits.clear()


class ResilientRateLimiter:
    """Tries Redis, falls back to in-memory, self-heals when Redis returns."""

    def __init__(self) -> None:
        self._redis: LimiterBackend | None = None
        self._memory = InMemoryBackend()
        self._redis_down_since: float | None = None
        if REDIS_URL or REDIS_HOST:
            try:
                self._redis = RedisBackend()
                self._redis._client.ping()
                logger.info("Rate limiting backend: redis (%s)", REDIS_HOST)
            except Exception as exc:
                logger.warning("Redis unavailable for rate limiting (%s); in-memory", exc)
                self._redis = None
        else:
            logger.info("Rate limiting backend: in-memory (no REDIS_HOST set)")

    def check(self, key: str, max_attempts: int, window_minutes: int) -> bool:
        if self._redis is not None:
            try:
                return self._redis.check(key, max_attempts, window_minutes)
            except Exception as exc:
                logger.warning("Redis limiter failed (%s); using in-memory", exc)
                self._memory.reset()
                self._redis = None
                self._redis_down_since = time.monotonic()
        return self._memory.check(key, max_attempts, window_minutes)

    def reset(self) -> None:
        """Clear in-memory state AND Redis rate-limit keys (used by tests)."""
        self._memory.reset()
        if self._redis is not None:
            try:
                self._redis._client.flushdb()
            except Exception:
                pass


_limiter_singleton: ResilientRateLimiter | None = None


def get_rate_limiter() -> ResilientRateLimiter:
    global _limiter_singleton
    if _limiter_singleton is None:
        _limiter_singleton = ResilientRateLimiter()
    return _limiter_singleton
