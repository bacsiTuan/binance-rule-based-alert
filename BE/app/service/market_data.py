import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from itertools import pairwise

from pydantic import ValidationError

from app.cache.redis_cache import RedisCache
from app.config import Settings
from app.errors import BinanceError
from app.models import Interval, KlinesResult, SymbolsResult
from app.service.binance_client import BinanceClient

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, settings: Settings, client: BinanceClient, cache: RedisCache):
        self.settings = settings
        self.client = client
        self.cache = cache
        # Different hosts/test environments cannot share a cached candle series.
        origin = hashlib.sha256(settings.base_url.encode()).hexdigest()[:8]
        self.prefix = f"binance:{settings.binance_market}:{origin}"
        # One process: coalesce concurrent refreshes and serialize upstream requests.
        self.refresh_lock = asyncio.Lock()

    async def _cached(self, key, model):
        value = await self.cache.get(key)
        if value is not None:
            try:
                return model.model_validate(value)
            except ValidationError:
                logger.warning("Ignoring invalid cached data: %s", key)
        return None

    async def _load(self, key, model, ttl, fetch):
        cached = await self._cached(key, model)
        if cached is not None:
            return cached.model_copy(update={"source": "cache"})
        async with self.refresh_lock:
            cached = await self._cached(key, model)
            if cached is not None:
                return cached.model_copy(update={"source": "cache"})
            try:
                result = await fetch()
            except BinanceError as exc:
                if exc.retryable:
                    stale = await self._cached(f"{key}:stale", model)
                    if stale is not None:
                        logger.warning("Returning stale data for %s: %s", key, exc)
                        return stale.model_copy(
                            update={"source": "stale", "stale": True, "warning": str(exc)}
                        )
                raise
            await self.cache.set(
                key,
                result.model_dump(mode="json"),
                ttl,
                max(self.settings.stale_ttl_seconds, ttl + 1),
            )
            logger.info("Fetched and cached %s", key)
            return result

    async def klines(self, symbol: str, interval: Interval = "1h", limit: int = 300):
        symbol = symbol.strip().upper()
        if not symbol.isascii() or not symbol.isalnum() or not 2 <= len(symbol) <= 30:
            raise ValueError("Symbol must contain 2-30 ASCII letters/digits")
        if interval not in ("1h", "1d", "1w"):
            raise ValueError("Interval must be 1h, 1d or 1w")
        if not 1 <= limit <= 1000:
            raise ValueError("Limit must be between 1 and 1000")
        key = f"{self.prefix}:klines:{symbol}:{interval}:{limit}"

        async def fetch():
            candles = await self.client.klines(symbol, interval, limit)
            return KlinesResult(
                market=self.settings.binance_market,
                symbol=symbol,
                interval=interval,
                source="binance",
                cache_key=key,
                fetched_at=datetime.now(UTC),
                candles=candles,
            )

        return await self._load(key, KlinesResult, self.settings.cache_ttl_seconds, fetch)

    async def closed_klines(self, symbol: str, interval: Interval, boundary: int):
        duration = {"1h": 3600000, "1d": 86400000, "1w": 604800000}[interval]
        key = f"{self.prefix}:closed:{symbol}:{interval}:1000:{boundary - 1}"

        def ready(snapshot):
            candles = snapshot.candles
            return (
                snapshot.market == self.settings.binance_market
                and snapshot.symbol == symbol and snapshot.interval == interval
                and not snapshot.stale and snapshot.source != "stale"
                and snapshot.fetched_at.utcoffset() is not None
                and snapshot.fetched_at.timestamp() * 1000 >= boundary
                and bool(candles) and candles[-1].close_time == boundary - 1
                and all(c.close_time - c.open_time == duration - 1 for c in candles)
                and all(b.open_time == a.close_time + 1 for a, b in pairwise(candles))
            )

        async with self.refresh_lock:
            cached = await self._cached(key, KlinesResult)
            if cached is not None and ready(cached):
                return cached.model_copy(update={"source": "cache"})
            candles = await self.client.klines(symbol, interval, 1000, end_time=boundary - 1)
            snapshot = KlinesResult(
                market=self.settings.binance_market, symbol=symbol, interval=interval,
                source="binance", cache_key=key, fetched_at=datetime.now(UTC), candles=candles,
            )
            # Incomplete targets must not prevent the next upstream readiness attempt.
            if not ready(snapshot):
                return None
            ttl = self.settings.cache_ttl_seconds
            await self.cache.set(
                key, snapshot.model_dump(mode="json"), ttl,
                max(self.settings.stale_ttl_seconds, ttl + 1),
            )
            return snapshot

    async def symbols(self):
        async def fetch():
            symbols = await self.client.symbols()
            return SymbolsResult(
                market=self.settings.binance_market,
                source="binance",
                fetched_at=datetime.now(UTC),
                symbols=symbols,
            )

        return await self._load(
            f"{self.prefix}:symbols:USDT", SymbolsResult, self.settings.symbols_ttl_seconds, fetch
        )
