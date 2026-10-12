import argparse
import asyncio
import logging
import sys

import httpx
from redis.asyncio import Redis

from app.cache.redis_cache import RedisCache
from app.config import get_settings
from app.errors import BinanceError, CacheError
from app.service import MarketDataService
from app.service.binance_client import BinanceClient


async def fetch_once(args):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    redis = Redis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3
    )
    try:
        async with httpx.AsyncClient(timeout=settings.binance_timeout_seconds) as http:
            cache = RedisCache(redis)
            await cache.ping()
            service = MarketDataService(settings, BinanceClient(settings, http), cache)
            result = await service.klines(args.symbol, args.interval, args.limit)
            print(result.model_dump_json(indent=2))
    finally:
        await redis.aclose()


def main():
    parser = argparse.ArgumentParser(description="Fetch Binance candles and store them in Redis")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", choices=["1h", "1d", "1w"], default="1h")
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args()
    try:
        asyncio.run(fetch_once(args))
    except (BinanceError, CacheError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
