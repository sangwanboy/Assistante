"""Redis client singleton for real-time state, pub/sub, and task queues."""

import logging
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client singleton. Falls back gracefully if Redis is unavailable."""

    _instance: "RedisClient | None" = None
    _available: bool = False

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    @classmethod
    async def get_instance(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = cls()
            try:
                cls._instance._redis = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
                await cls._instance._redis.ping()
                cls._available = True
                logger.info("Redis connected at %s", settings.redis_url)
            except Exception as exc:
                logger.warning("Redis unavailable (%s) — falling back to in-memory.", exc)
                cls._instance._redis = None
                cls._available = False
        return cls._instance

    @property
    def redis(self) -> aioredis.Redis | None:
        return self._redis

    @property
    def available(self) -> bool:
        return self._available and self._redis is not None

    async def close(self):
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None
            RedisClient._available = False

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
        cls._available = False
