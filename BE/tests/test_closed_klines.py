from datetime import UTC, datetime

import fakeredis.aioredis
import httpx
import pytest

from app.cache.redis_cache import RedisCache
from app.config import Settings
from app.errors import BinanceError
from app.service.binance_client import BinanceClient
from app.service.market_data import MarketDataService


@pytest.mark.parametrize("market,path", [("spot", "/api/v3/klines"), ("futures", "/fapi/v1/klines")])
async def test_readiness_refetch_and_closed_history(market, path):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    settings = Settings(_env_file=None, binance_market=market)
    boundary = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) * 1000
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.path == path
        assert request.url.params["endTime"] == str(boundary - 1)
        assert request.url.params["limit"] == "1000"
        end = boundary - (3600000 if len(calls) == 1 else 0)
        rows = []
        for i in range(1000):
            opened = end - (1000 - i) * 3600000
            rows.append([opened, "", "", "", "70.000000001", "", opened + 3599999])
        return httpx.Response(200, json=rows)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        service = MarketDataService(settings, BinanceClient(settings, http), RedisCache(redis))
        assert await service.closed_klines("BTCUSDT", "1h", boundary) is None
        result = await service.closed_klines("BTCUSDT", "1h", boundary)
        assert len(result.candles) == 1000
        assert result.candles[-1].close_time == boundary - 1
        assert (await service.closed_klines("BTCUSDT", "1h", boundary)).source == "cache"
        assert len(calls) == 2
    await redis.aclose()


@pytest.mark.parametrize("corruption", ["stale", "source", "age", "symbol", "gap", "open"])
async def test_unusable_cached_target_refetches(corruption):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    settings = Settings(_env_file=None)
    boundary = 1767225600000
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[
            [boundary - 7200000, "", "", "", "70", "", boundary - 3600001],
            [boundary - 3600000, "", "", "", "71", "", boundary - 1],
        ])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        service = MarketDataService(settings, BinanceClient(settings, http), RedisCache(redis))
        first = await service.closed_klines("BTCUSDT", "1h", boundary)
        broken = first.model_dump(mode="json")
        if corruption == "stale":
            broken["stale"] = True
        elif corruption == "source":
            broken["source"] = "stale"
        elif corruption == "age":
            broken["fetched_at"] = "2020-01-01T00:00:00Z"
        elif corruption == "symbol":
            broken["symbol"] = "ETHUSDT"
        elif corruption == "gap":
            broken["candles"][0]["open_time"] -= 3600000
            broken["candles"][0]["close_time"] -= 3600000
        else:
            broken["candles"][-1]["close_time"] += 3600000
        await service.cache.set(first.cache_key, broken, 60, 3600)
        result = await service.closed_klines("BTCUSDT", "1h", boundary)
        assert result.source == "binance" and len(calls) == 2
    await redis.aclose()


@pytest.mark.parametrize("fault", ["duplicate", "reverse", "gap", "open", "missing"])
async def test_bad_upstream_never_becomes_processed_target(fault):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    settings = Settings(_env_file=None, binance_max_attempts=1)
    boundary = 1767225600000
    rows = [
        [boundary - 7200000, "", "", "", "70", "", boundary - 3600001],
        [boundary - 3600000, "", "", "", "71", "", boundary - 1],
    ]
    if fault == "duplicate":
        rows[0] = rows[1]
    elif fault == "reverse":
        rows.reverse()
    elif fault == "gap":
        rows[0][0] -= 3600000
        rows[0][6] -= 3600000
    elif fault == "open":
        rows[-1][6] += 3600000
    else:
        rows.pop()
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=rows)
    )) as http:
        service = MarketDataService(settings, BinanceClient(settings, http), RedisCache(redis))
        if fault in ("duplicate", "reverse"):
            with pytest.raises(BinanceError):
                await service.closed_klines("BTCUSDT", "1h", boundary)
        else:
            assert await service.closed_klines("BTCUSDT", "1h", boundary) is None
        assert not await redis.keys("*")
    await redis.aclose()


@pytest.mark.parametrize("failure", [429, 500, "timeout"])
async def test_closed_adapter_no_stale_fallback_and_cooldown(failure):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    settings = Settings(_env_file=None, binance_max_attempts=1)
    calls = []
    boundary = 1767225600000
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json=[
                [boundary - 3600000, "", "", "", "70", "", boundary - 1],
            ])
        if failure == "timeout":
            raise httpx.ReadTimeout("mock", request=request)
        return httpx.Response(failure, headers={"Retry-After": "60"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        service = MarketDataService(settings, BinanceClient(settings, http), RedisCache(redis))
        first = await service.closed_klines("BTCUSDT", "1h", boundary)
        await redis.delete(first.cache_key)
        assert await redis.exists(first.cache_key + ":stale")
        with pytest.raises(BinanceError):
            await service.closed_klines("BTCUSDT", "1h", boundary)
        if failure == 429:
            with pytest.raises(BinanceError):
                await service.closed_klines("BTCUSDT", "1h", boundary)
            assert len(calls) == 2
    await redis.aclose()
