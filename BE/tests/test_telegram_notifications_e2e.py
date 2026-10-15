import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import fakeredis.aioredis
import httpx
import pytest

from app.config import Settings
from app.models import Candle, KlinesResult, RuleCreate, RuleUpdate
from app.rules import RuleStorage
from app.service.telegram_client import DeliveryResult, TelegramClient
from app.service.telegram_scheduler import TelegramScheduler, boundary_ms, eligible
from app.telegram_state import META_KEY


@pytest.mark.parametrize("status,payload,expected", [
    (200, {"ok": True, "result": {"message_id": 7}}, "accepted"),
    (200, {"ok": False}, "failed"),
    (500, {"ok": False}, "unknown"),
    (200, {}, "unknown"),
    (429, {"ok": False, "parameters": {"retry_after": 12}}, "failed"),
])
async def test_ack(status, payload, expected, caplog):
    token = "sentinel-token"
    settings = Settings(_env_file=None, telegram_bot_token=token, telegram_chat_id="123")
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json=payload)
    caplog.set_level("DEBUG")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await TelegramClient(settings, http).send_message("hello")
    assert result.status == expected
    assert len(calls) == 1
    assert token not in caplog.text


async def test_timeout_is_unknown():
    def fail(request):
        raise httpx.ReadTimeout("secret URL must not escape", request=request)
    settings = Settings(_env_file=None, telegram_bot_token="fake", telegram_chat_id="123")
    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as http:
        result = await TelegramClient(settings, http).send_message("hello")
    assert result.status == "unknown"


@pytest.mark.parametrize("frame,expected", [
    ("1h", "2026-10-14T12:00:00+00:00"),
    ("1d", "2026-10-14T00:00:00+00:00"),
    ("1w", "2026-10-12T00:00:00+00:00"),
])
def test_boundaries(frame, expected):
    now = datetime(2026, 10, 14, 12, 25, tzinfo=UTC)
    assert boundary_ms(now, frame) == int(datetime.fromisoformat(expected).timestamp() * 1000)


async def test_end_to_end_without_refresh():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    rules = RuleStorage(redis)
    rule = await rules.create_rule(RuleCreate(
        symbol="BTCUSDT", timeframe="1h", indicator={"type": "sma", "length": 1},
        operator="gte", target=70,
    ))
    now = datetime.now(UTC).replace(minute=0, second=5, microsecond=0) + timedelta(hours=1)
    calls = []

    async def no_sleep(delay):
        pass

    class Market:
        prefix = "binance:spot:test"
        settings = Settings(_env_file=None)
        value = 68
        async def closed_klines(self, symbol, timeframe, boundary):
            return KlinesResult(
                market="spot", symbol=symbol, interval=timeframe, source="binance",
                fetched_at=now, cache_key="test",
                candles=[Candle(open_time=boundary - 3600000, close_time=boundary - 1,
                                close=str(self.value))],
            )

    class Sender:
        async def send_message(self, text, bold_chars=0):
            calls.append(text)
            return DeliveryResult("accepted", message_id=len(calls))

    market = Market()
    for value in (68, 70, 75, 69, 71):
        market.value = value
        watcher = TelegramScheduler(market, rules, Sender(), clock=lambda now=now: now, sleep=no_sleep)
        await watcher.scan("1h")
        await watcher.scan("1h")
        now += timedelta(hours=1)
    assert len(calls) == 2
    assert "Nến: Đã đóng" in calls[0]
    assert ">= 70" in calls[0]
    assert "Threshold:" not in calls[0]
    await rules.update_rule(rule.id, RuleUpdate(enabled=False))
    await watcher.scan("1h")
    assert len(calls) == 2
    await redis.aclose()


async def test_generation_mutations():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    rules = RuleStorage(redis)
    rule = await rules.create_rule(RuleCreate(
        symbol="BTCUSDT", indicator={"type": "rsi", "length": 14}, operator="gte", target=70,
    ))
    async def generation():
        return json.loads(await redis.hget(META_KEY, str(rule.id)))["generation"]
    before = await generation()
    await rules.update_rule(rule.id, RuleUpdate(message="new"))
    assert await generation() == before
    await rules.update_rule(rule.id, RuleUpdate(enabled=False))
    await rules.update_rule(rule.id, RuleUpdate(enabled=True))
    assert await generation() != before
    await redis.aclose()


@pytest.mark.parametrize("overrides", [
    {"enabled": False}, {"operator": "cross_above"}, {"candle_mode": "include_current"},
    {"target": float("inf")}, {"expiration": "invalid"},
])
def test_legacy_rules_skipped(overrides):
    rule = SimpleNamespace(
        enabled=True, operator="gte", candle_mode="closed",
        indicator=SimpleNamespace(type="rsi", length=14), target=70, expiration=None,
    )
    for key, value in overrides.items():
        setattr(rule, key, value)
    assert not eligible(rule, datetime.now(UTC))

@pytest.mark.parametrize("market", ["spot", "futures"])
async def test_http_crud_lifespan_and_restart_with_mock_upstreams(
    monkeypatch, fake_clock, scheduler_clock, market,
):
    from apscheduler.events import EVENT_JOB_EXECUTED

    from app import main, telegram_state
    from app.service import market_data
    from app.service.telegram_scheduler import DURATIONS, TelegramScheduler

    clock = fake_clock
    monkeypatch.setattr(telegram_state, "now_ms", lambda: int(clock.now.timestamp() * 1000))
    monkeypatch.setattr(market_data, "datetime", SimpleNamespace(now=lambda tz: clock.now))
    server = fakeredis.FakeServer()
    resources = []
    def redis_factory(*args, **kwargs):
        redis = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
        resources.append(redis)
        return redis
    monkeypatch.setattr(main, "Redis", SimpleNamespace(from_url=redis_factory))
    original_http = httpx.AsyncClient
    clients, telegram_calls, market_calls = [], [], []
    current_value = "75"
    fail_send = False
    def upstream(request):
        if request.url.host == "api.telegram.org":
            telegram_calls.append(json.loads(request.content))
            if fail_send:
                raise httpx.ReadTimeout("mock timeout", request=request)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": len(telegram_calls)}})
        market_calls.append(request)
        expected = "/api/v3/klines" if market == "spot" else "/fapi/v1/klines"
        assert request.url.path == expected
        frame = request.url.params["interval"]
        end = int(request.url.params["endTime"])
        duration = DURATIONS[frame]
        return httpx.Response(200, json=[
            [end + 1 - (20 - i) * duration, "", "", "", current_value, "",
             end - (19 - i) * duration] for i in range(20)
        ])
    def client_factory(**kwargs):
        http = original_http(transport=httpx.MockTransport(upstream), **kwargs)
        clients.append(http)
        return http
    monkeypatch.setattr(main, "httpx", SimpleNamespace(AsyncClient=client_factory))
    executions = []
    def watcher_factory(service, rules, sender):
        watcher = TelegramScheduler(service, rules, sender, clock=lambda: clock.now,
                                    sleep=clock.sleep, monotonic=lambda: clock.elapsed)
        scheduler_clock.attach(watcher)
        watcher.scheduler.add_listener(executions.append, EVENT_JOB_EXECUTED)
        return watcher
    monkeypatch.setattr(main, "TelegramScheduler", watcher_factory)
    settings = Settings(
        _env_file=None, telegram_enabled=True, telegram_bot_token="fake-test-token",
        telegram_chat_id="fake-test-chat", binance_market=market,
    )
    ids = {}
    app = main.create_app(settings)
    async with app.router.lifespan_context(app):
        watcher = app.state.telegram_watcher
        assert len(watcher.scheduler.get_jobs()) == 3
        async with original_http(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
            for frame in DURATIONS:
                response = await api.post("/rules", json={
                    "symbol": "BTCUSDT", "timeframe": frame, "indicator": {"type": "sma", "length": 1},
                    "operator": "gte", "target": 70,
                })
                assert response.status_code == 201
                ids[frame] = response.json()["id"]
            assert not telegram_calls and not market_calls
            clock.advance(65)
            await scheduler_clock.tick(watcher)
            stats = [event.retval for event in executions]
            assert len(stats) == 3
            assert sum(s["triggered"] for s in stats) == 3
            assert sum(s["attempted"] for s in stats) == 3
            assert sum(s["accepted"] for s in stats) == 3
            assert len(telegram_calls) == 3
            assert all(f"· {market.upper()} ·" in call["text"] for call in telegram_calls)
            await scheduler_clock.tick(watcher)
            assert len(telegram_calls) == 3
            assert (await api.patch(f"/rules/{ids['1h']}", json={"enabled": False})).status_code == 200
            clock.advance(3600)
            await scheduler_clock.tick(watcher)
            assert len(telegram_calls) == 3
            assert (await api.patch(f"/rules/{ids['1h']}", json={"enabled": True})).status_code == 200
    assert not watcher.tasks
    assert all(client.is_closed for client in clients)
    app = main.create_app(settings)
    async with app.router.lifespan_context(app):
        watcher = app.state.telegram_watcher
        clock.advance(3600)
        fail_send = True
        await scheduler_clock.tick(watcher)
        stats = executions[-1].retval
        assert stats["triggered"] == 1 and stats["attempted"] == 1 and stats["unknown"] == 1
        assert stats["accepted"] == 0 and len(telegram_calls) == 4
    app = main.create_app(settings)
    async with app.router.lifespan_context(app):
        watcher = app.state.telegram_watcher
        clock.advance(3600)
        fail_send = False
        await scheduler_clock.tick(watcher)
        assert len(telegram_calls) == 4
        current_value = "69"
        clock.advance(3600)
        await scheduler_clock.tick(watcher)
        current_value = "71"
        clock.advance(3600)
        await scheduler_clock.tick(watcher)
        stats = executions[-1].retval
        assert stats["accepted"] == 1 and len(telegram_calls) == 5
    assert all(client.is_closed for client in clients)
