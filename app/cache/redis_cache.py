import json
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.errors import CacheError

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def ping(self) -> None:
        try:
            await self.redis.ping()
        except RedisError as exc:
            raise CacheError(
                "Redis is unavailable; start it with docker compose up -d redis"
            ) from exc

    async def get(self, key: str) -> dict | None:
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise TypeError("Invalid cache object")
            return value
        except RedisError as exc:
            raise CacheError("Cannot read Redis cache") from exc
        except (ValueError, TypeError):
            logger.warning("Ignoring corrupt cache entry: %s", key)
            return None

    async def set(self, key: str, value: dict, ttl: int, stale_ttl: int) -> None:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(key, raw, ex=ttl)
                pipe.set(f"{key}:stale", raw, ex=stale_ttl)
                await pipe.execute()
        except RedisError as exc:
            raise CacheError("Cannot store Binance data in Redis") from exc
