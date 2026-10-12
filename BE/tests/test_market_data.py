import asyncio
import json

import fakeredis.aioredis
import httpx
import pytest
from fastapi.testclient import TestClient

from app.cache.redis_cache import RedisCache
from app.config import Settings
from app.errors import BinanceError, CacheError
from app.main import create_app
from app.service import MarketDataService
from app.service.binance_client import BinanceClient

ROWS = [
    [1000, "1", "3", "1", "2.123456789012345678", "10", 1999],
    [2000, "2", "4", "2", "3", "20", 2999],
]


@pytest.fixture
async def make_service():
    resources = []

    def make(handler, **overrides):
        settings = Settings(_env_file=None, binance_max_attempts=1, **overrides)
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        service = MarketDataService(settings, BinanceClient(settings, http), RedisCache(redis))
        resources.append((http, redis))
        return service, redis

    yield make
    for http, redis in resources:
        await http.aclose()
        await redis.aclose()


async def test_miss_hit_json_and_ttls(make_service):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=ROWS)

    service, redis = make_service(handler)
    first = await service.klines("btcusdt")
    second = await service.klines("BTCUSDT")
    assert first.source == "binance" and second.source == "cache"
    assert len(calls) == 1
    assert calls[0].url.path == "/api/v3/klines"
    assert dict(calls[0].url.params) == {"symbol": "BTCUSDT", "interval": "1h", "limit": "300"}
    assert first.candles[0].close == "2.123456789012345678"
    stored = json.loads(await redis.get(first.cache_key))
    assert stored["candles"][0] == {
        "open_time": 1000,
        "close": "2.123456789012345678",
        "close_time": 1999,
    }
    assert 0 < await redis.ttl(first.cache_key) <= 60
    assert 60 < await redis.ttl(first.cache_key + ":stale") <= 3600


async def test_keys_separate_limits_intervals_markets_and_origins(make_service):
    handler = lambda request: httpx.Response(200, json=ROWS)
    spot, _ = make_service(handler)
    futures, _ = make_service(handler, binance_market="futures")
    other_host, _ = make_service(handler, binance_base_url="https://data-api.binance.vision")
    results = [
        await spot.klines("BTCUSDT", "1h", 2),
        await spot.klines("BTCUSDT", "1h", 300),
        await spot.klines("BTCUSDT", "1d", 2),
        await futures.klines("BTCUSDT", "1h", 2),
        await other_host.klines("BTCUSDT", "1h", 2),
    ]
    assert len({r.cache_key for r in results}) == 5


@pytest.mark.parametrize("status", [418, 429, 500])
async def test_stale_on_upstream_failure_and_cooldown(make_service, status):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json=ROWS)
        return httpx.Response(status, headers={"Retry-After": "120"}, json={"msg": "error"})

    service, redis = make_service(handler)
    first = await service.klines("BTCUSDT")
    await redis.delete(first.cache_key)  # Simulate fresh TTL expiry, retaining the fallback.
    stale = await service.klines("BTCUSDT")
    assert stale.stale and stale.source == "stale" and stale.warning
    assert stale.fetched_at == first.fetched_at
    assert await redis.get(first.cache_key) is None  # Never refresh the age of stale data.
    if status in (418, 429):
        await service.klines("BTCUSDT")
        assert len(calls) == 2  # Cooldown prevents another Binance request.
        with pytest.raises(BinanceError) as error:
            await service.klines("ETHUSDT")
        assert error.value.retry_after > 0


async def test_invalid_symbol_never_uses_stale(make_service):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return (
            httpx.Response(200, json=ROWS)
            if calls == 1
            else httpx.Response(400, json={"code": -1121, "msg": "Invalid symbol."})
        )

    service, redis = make_service(handler)
    first = await service.klines("BTCUSDT")
    await redis.delete(first.cache_key)
    with pytest.raises(BinanceError, match="Invalid symbol") as error:
        await service.klines("BTCUSDT")
    assert error.value.status_code == 400


async def test_timeout_without_stale(make_service):
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    service, _ = make_service(handler)
    with pytest.raises(BinanceError, match="timeout"):
        await service.klines("BTCUSDT")


async def test_timeout_with_stale(make_service):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, json=ROWS)
        raise httpx.ReadTimeout("timeout", request=request)

    service, redis = make_service(handler)
    first = await service.klines("BTCUSDT")
    await redis.delete(first.cache_key)
    assert (await service.klines("BTCUSDT")).stale
    await redis.delete(first.cache_key + ":stale")
    with pytest.raises(BinanceError):
        await service.klines("BTCUSDT")


async def test_concurrent_refreshes_fetch_once(make_service):
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return httpx.Response(200, json=ROWS)

    service, _ = make_service(handler)
    results = await asyncio.gather(*(service.klines("BTCUSDT") for _ in range(10)))
    assert calls == 1
    assert sum(r.source == "binance" for r in results) == 1


async def test_futures_route_and_symbols_filter(make_service):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("klines"):
            return httpx.Response(200, json=ROWS)
        return httpx.Response(
            200,
            json={
                "symbols": [
                    {"symbol": "BTCUSDT", "quoteAsset": "USDT", "status": "TRADING"},
                    {"symbol": "ETHUSDT", "quoteAsset": "USDT", "status": "BREAK"},
                    {"symbol": "ETHBTC", "quoteAsset": "BTC", "status": "TRADING"},
                ]
            },
        )

    service, _ = make_service(handler, binance_market="futures")
    await service.klines("BTCUSDT", "1w")
    assert (await service.symbols()).symbols == ["BTCUSDT"]
    assert (await service.symbols()).source == "cache"
    assert calls == ["/fapi/v1/klines", "/fapi/v1/exchangeInfo"]


@pytest.mark.parametrize(
    "payload", [{"error": True}, [[0]], [[1, 0, 0, 0, "NaN", 0, 2]], list(reversed(ROWS))]
)
async def test_malformed_candles_are_clear_errors(make_service, payload):
    service, _ = make_service(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(BinanceError, match="malformed"):
        await service.klines("BTCUSDT")


async def test_corrupt_cache_is_refetched(make_service):
    service, redis = make_service(lambda request: httpx.Response(200, json=ROWS))
    first = await service.klines("BTCUSDT")
    await redis.set(first.cache_key, "{broken")
    assert (await service.klines("BTCUSDT")).source == "binance"
    await redis.set(first.cache_key, '{"candles": []}')
    assert (await service.klines("BTCUSDT")).source == "binance"
    invalid = first.model_dump(mode="json")
    invalid["candles"][0]["close"] = "invalid-price"
    await redis.set(first.cache_key, json.dumps(invalid))
    assert (await service.klines("BTCUSDT")).source == "binance"


def test_http_validation_health_and_errors():
    app = create_app(Settings(_env_file=None))

    class FakeService:
        cache = None

        async def klines(self, *args):
            raise BinanceError("Rate limited", status_code=429, retry_after=120)

        async def ping(self):
            raise CacheError("Redis unavailable")

    fake = FakeService()
    fake.cache = fake
    with TestClient(app) as http:
        app.state.service = fake
        for params in [{"limit": 0}, {"limit": 1001}, {"interval": "1m"}, {"symbol": "bad:key"}]:
            assert http.get("/klines", params=params).status_code == 422
        response = http.get("/klines")
        assert response.status_code == 429 and response.headers["Retry-After"] == "120"
        assert http.get("/health").status_code == 503


async def test_retries_transient_failure():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503) if calls == 1 else httpx.Response(200, json=ROWS)

    settings = Settings(_env_file=None, binance_max_attempts=2)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        candles = await BinanceClient(settings, http).klines("BTCUSDT", "1h", 300)
    assert len(candles) == 2 and calls == 2
