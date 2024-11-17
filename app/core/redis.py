import uuid
from datetime import timedelta
from enum import Enum

import redis.asyncio as redis  # type: ignore[import-untyped]

from core.config import get_settings


config = get_settings()


class RedisKeys(str, Enum):
    """Redis Keys Identifiers."""

    blacklist = "blacklist"


class RedisClient:
    """Redis Client class."""

    def __init__(self, host: str = "localhost", port: int = 6379):
        """Initialize Redis connection."""
        self._redis = redis.Redis(host=host, port=port)

    async def add_token_to_blacklist(self, jwt_id: uuid.UUID, ttl: timedelta) -> None:
        """Add token to blacklist."""
        await self._redis.setex(f"{RedisKeys.blacklist}:{jwt_id}", ttl, "blacklisted")

    async def is_token_blacklisted(self, jwt_id: uuid.UUID) -> bool:
        """Check if token is blacklisted."""
        return bool(await self._redis.exists(f"{RedisKeys.blacklist}:{jwt_id}") > 0)


redis_client = RedisClient(host=config.redis_host, port=config.redis_port)
