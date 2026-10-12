import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import pytest

from app.cache.redis_cache import RedisCache
from app.config import Settings
from app.errors import BinanceError, CacheError
from app.main import create_app
from app.models import Candle, KlinesResult
from app.service import MarketDataService
from app.service.binance_client import BinanceClient


def make_snapshot(count=60, **updates):
    data = {
        "market": "spot",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "source": "cache",
        "fetched_at": datetime(2026, 10, 11, tzinfo=UTC),
        "cache_key": "fixture-key",
        "candles": [
            Candle(open_time=i * 1000, close=str(i + 1), close_time=i * 1000 + 999)
            for i in range(count)
        ],
    }
    data.update(updates)
    return KlinesResult(**data)


@pytest.mark.parametrize("market", ["spot", "futures"])
async def test_indicator_endpoint_reuses_service(market):
    app = create_app(Settings(_env_file=None, binance_market=market))
    data = make_snapshot(market=market)
    service = AsyncMock()
    service.klines.return_value = data
    app.state.service = service
    # ASGITransport intentionally does not run the real Redis/HTTP lifespan.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        choices = [
            {"name": "sma", "period": 20},
            {"name": "sma", "period": 50},
            {"name": "ema"},
            {"name": "rsi"},
        ]
        response = await http.post("/indicators", json={"symbol": "btcusdt", "indicators": choices})
        assert response.status_code == 200
        result = response.json()
        service.klines.assert_awaited_once_with("BTCUSDT", "1h", 300)
        assert [(x["name"], x["period"]) for x in result["results"]] == [
            ("sma", 20),
            ("sma", 50),
            ("ema", 14),
            ("rsi", 14),
        ]
        for key in (
            "market",
            "symbol",
            "interval",
            "source",
            "stale",
            "fetched_at",
            "cache_key",
            "warning",
        ):
            assert result[key] == data.model_dump(mode="json")[key]
        assert all(isinstance(x["latest"]["value"], str) for x in result["results"])
        old = await http.get("/klines")
        assert old.json() == data.model_dump(mode="json")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"indicators": []},
        {"indicators": [{"name": "SMA"}]},
        *[{"indicators": [{"name": "sma", "period": p}]} for p in (0, 1000, True, 14.0, "14")],
        *[{"indicators": [{"name": "sma"}], "limit": p} for p in (0, 1001, True, 14.0, "14")],
        {"indicators": [{"name": "sma"}, {"name": "sma", "period": 14}]},
        {"indicators": [{"name": "sma", "extra": 1}]},
        {"indicators": [{"name": "sma"}], "market": "futures"},
        {"indicators": [{"name": "sma"}], "include_open": "true"},
        {"indicators": [{"name": "sma"}], "symbol": " BTCUSDT"},
        {"indicators": [{"name": "sma"}], "interval": "1m"},
    ],
)
async def test_invalid_request_does_not_fetch(body):
    app = create_app(Settings(_env_file=None))
    service = AsyncMock()
    app.state.service = service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.post("/indicators", json=body)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    service.klines.assert_not_called()


@pytest.mark.parametrize("count", [0, 30])
async def test_partial_warmup_is_success(count):
    app = create_app(Settings(_env_file=None))
    app.state.service = AsyncMock()
    app.state.service.klines.return_value = make_snapshot(count)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.post(
            "/indicators",
            json={"indicators": [{"name": "sma", "period": 20}, {"name": "sma", "period": 50}]},
        )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["latest"]["status"] == ("ok" if count else "insufficient_data")
    assert results[1]["latest"]["value"] is None
    if not count:
        assert results[0]["points"] == []
        assert results[0]["latest"]["open_time"] is None


async def test_invalid_snapshot_is_502():
    app = create_app(Settings(_env_file=None))
    app.state.service = AsyncMock()
    app.state.service.klines.return_value = make_snapshot(symbol="ETHUSDT")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.post("/indicators", json={"indicators": [{"name": "sma"}]})
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "invalid_indicator_data"


@pytest.fixture
async def market_api():
    resources = []

    def make(handler, **overrides):
        settings = Settings(_env_file=None, binance_max_attempts=1, **overrides)
        upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        service = MarketDataService(settings, BinanceClient(settings, upstream), RedisCache(redis))
        app = create_app(settings)
        app.state.service = service
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        resources.extend([http, upstream, redis])
        return http, redis, service

    yield make
    for resource in resources:
        await resource.aclose()


def rows(count=5):
    return [[i * 1000, "0", "0", "0", str(i + 1), "0", i * 1000 + 999] for i in range(count)]


async def test_cache_hit_no_extra_keys_or_ttl_refresh(market_api):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=rows())

    http, redis, _ = market_api(handler)
    body = {"indicators": [{"name": "sma", "period": 3}, {"name": "sma", "period": 50}]}
    first = (await http.post("/indicators", json=body)).json()
    key = first["cache_key"]
    await redis.expire(key, 30)
    await redis.expire(key + ":stale", 300)
    second = (await http.post("/indicators", json=body)).json()
    assert (first["source"], second["source"]) == ("binance", "cache")
    assert second["fetched_at"] == first["fetched_at"]
    assert len(calls) == 1
    assert set(await redis.keys("*")) == {key, key + ":stale"}
    assert 0 < await redis.ttl(key) <= 30
    assert 0 < await redis.ttl(key + ":stale") <= 300
    old = (await http.get("/klines")).json()
    assert old["candles"] == make_snapshot(5).model_dump(mode="json")["candles"]
    assert "results" not in old
    assert second["results"][1]["latest"]["status"] == "insufficient_data"


@pytest.mark.parametrize("failure", [418, 429, 500, "timeout"])
async def test_stale_preserves_metadata_and_cooldown(market_api, failure):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json=rows())
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(failure, headers={"Retry-After": "120"})

    http, redis, _ = market_api(handler)
    body = {"indicators": [{"name": "sma", "period": 3}]}
    first = (await http.post("/indicators", json=body)).json()
    key = first["cache_key"]
    await redis.delete(key)
    await redis.expire(key + ":stale", 300)
    response = await http.post("/indicators", json=body)
    assert response.status_code == 200
    stale = response.json()
    assert stale["source"] == "stale" and stale["stale"] and stale["warning"]
    assert stale["fetched_at"] == first["fetched_at"]
    assert stale["results"][0]["latest"]["status"] == "ok"
    assert not stale["results"][0]["latest"]["provisional"]
    assert await redis.get(key) is None
    assert 0 < await redis.ttl(key + ":stale") <= 300
    if failure in (418, 429):
        await http.post("/indicators", json=body)
        assert len(calls) == 2
        error = await http.post("/indicators", json={**body, "symbol": "ETHUSDT"})
        assert error.status_code == failure and int(error.headers["Retry-After"]) > 0


async def test_concurrent_indicators_and_market_share_refresh(market_api):
    calls = []

    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json=rows())

    http, _, _ = market_api(handler)
    responses = await asyncio.gather(
        http.get("/klines"),
        *(http.post("/indicators", json={"indicators": [{"name": "sma"}]}) for _ in range(5)),
    )
    assert all(r.status_code == 200 for r in responses)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "error,status",
    [
        (BinanceError("invalid symbol", status_code=400), 400),
        (BinanceError("limited", status_code=418, retry_after=60), 418),
        (BinanceError("limited", status_code=429, retry_after=60), 429),
        (BinanceError("timeout"), 502),
        (CacheError("redis down"), 503),
    ],
)
async def test_upstream_errors_are_not_insufficient_data(error, status):
    app = create_app(Settings(_env_file=None))
    app.state.service = AsyncMock()
    app.state.service.klines.side_effect = error
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.post("/indicators", json={"indicators": [{"name": "sma"}]})
    assert response.status_code == status
    assert response.json()["detail"] == str(error)
    if status in (418, 429):
        assert response.headers["Retry-After"] == "60"


async def test_market_host_interval_limit_separation(market_api):
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, json=rows())

    spot, _, _ = market_api(handler)
    futures, _, _ = market_api(handler, binance_market="futures")
    host, _, _ = market_api(handler, binance_base_url="https://data-api.binance.vision")
    body = {"indicators": [{"name": "sma"}]}
    responses = [
        await http.post("/indicators", json={**body, **params})
        for http, params in [
            (spot, {}),
            (futures, {}),
            (host, {}),
            (spot, {"limit": 2}),
            (spot, {"interval": "1w"}),
        ]
    ]
    assert all(r.status_code == 200 for r in responses)
    assert len({r.json()["cache_key"] for r in responses}) == 5
    assert calls[1].path == "/fapi/v1/klines"
    assert responses[1].json()["market"] == "futures"


@pytest.mark.parametrize("include_open", [False, True])
async def test_clock_counters_provisional_and_latest_contract(monkeypatch, include_open):
    from app import main

    calls = []

    def now(tz):
        calls.append(tz)
        return datetime(1970, 1, 1, 0, 0, 10, tzinfo=UTC)

    monkeypatch.setattr(main, "datetime", SimpleNamespace(now=now))
    app = create_app(Settings(_env_file=None))
    app.state.service = AsyncMock()
    app.state.service.klines.return_value = make_snapshot(
        count=5,
        fetched_at=datetime(1970, 1, 1, 0, 0, 3, tzinfo=UTC),
        source="stale",
        stale=True,
        warning="upstream timeout",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.post(
            "/indicators",
            json={
                "include_open": include_open,
                "indicators": [{"name": "sma", "period": 3}, {"name": "rsi", "period": 3}],
            },
        )
    result = response.json()
    assert response.status_code == 200
    assert calls == [UTC]
    assert result["evaluated_at"] == 10000
    assert result["input_candles"] == 5
    assert result["eligible_candles"] == (5 if include_open else 3)
    assert result["excluded_candles"] == (0 if include_open else 2)
    assert result["series_start_time"] == 0
    for item in result["results"]:
        assert item["latest"] == item["points"][-1]
        assert item["available_candles"] == result["eligible_candles"]
        assert item["latest"]["provisional"] is include_open
        for point in item["points"]:
            assert type(point["open_time"]) is int and type(point["close_time"]) is int
            assert point["status"] in ("ok", "insufficient_data")
            assert (point["value"] is None) == (point["status"] == "insufficient_data")


async def test_bad_cached_order_only_changes_indicator_behavior(market_api):
    http, redis, _ = market_api(lambda request: httpx.Response(200, json=rows()))
    original = (await http.get("/klines")).json()
    original["candles"].reverse()
    await redis.set(original["cache_key"], json.dumps(original), ex=60)
    response = await http.post("/indicators", json={"indicators": [{"name": "sma"}]})
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "invalid_indicator_data"
    unchanged = await http.get("/klines")
    assert unchanged.status_code == 200
    assert unchanged.json()["candles"] == original["candles"]


def test_openapi_documents_separate_request_and_response():
    schema = create_app(Settings(_env_file=None)).openapi()
    route = schema["paths"]["/indicators"]["post"]
    assert route["requestBody"]["required"]
    assert route["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/IndicatorsResult"
    )
    assert "get" in schema["paths"]["/klines"]
