import uuid
from datetime import timedelta
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

import redis.asyncio as redis  # type: ignore[import-untyped]
from sqlmodel import SQLModel

from core.config import get_settings


config = get_settings()
T = TypeVar("T", bound=SQLModel)


class RedisKeys(str, Enum):
    """Redis Keys Identifiers."""

    blacklist = "blacklist"
    predefined_category = "predefined_category"
    stock_price = "stock_price"


class RedisClient:
    """Redis Client class."""

    def __init__(self, host: str = "localhost", port: int = 6379):
        """Initialize Redis connection."""
        self._redis = redis.Redis(host=host, port=port, decode_responses=True)

    async def add_token_to_blacklist(self, jwt_id: uuid.UUID, ttl: timedelta) -> None:
        """Add token to blacklist."""
        await self.add_row_to_cache(RedisKeys.blacklist.value, str(jwt_id), "blacklisted", ttl)

    async def is_token_blacklisted(self, jwt_id: uuid.UUID) -> bool:
        """Check if token is blacklisted."""
        return bool(await self._redis.exists(f"{RedisKeys.blacklist.value}:{jwt_id}") > 0)

    async def add_row_to_cache(self, redis_key: str, key: str, value: str, ttl: timedelta | None = None) -> None:
        """Add row to cache."""
        await self._redis.set(f"{redis_key}:{key}", value, ex=ttl)

    async def read_row_from_cache(self, redis_key: str, key: str) -> Any:
        """Read row from cache."""
        return await self._redis.get(f"{redis_key}:{key}")


redis_client = RedisClient(host=config.redis_host, port=config.redis_port)


def write_through_cache(redis_key: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Write SQL row to redis cache."""

    def inner(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> T:
            result = await func(*args, **kwargs)
            await redis_client.add_row_to_cache(redis_key, result.id, result.model_dump_json())
            return result

        return wrapper

    return inner
