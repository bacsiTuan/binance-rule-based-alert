import asyncio
import os
import socket
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest

from app.config import Settings
from app.models import Candle, KlinesResult, RuleCreate
from app.rules import RuleStorage
from app.service.telegram_client import DeliveryResult
from app.service.telegram_scheduler import DURATIONS, TelegramScheduler


@pytest.fixture(autouse=True)
def prevent_network_in_mock_tests(monkeypatch, request):
    live_modules = {
        "test_telegram_client_live.py": "RUN_TELEGRAM_LIVE_TESTS",
        "test_open_ai_client.py": "RUN_OPENAI_LIVE_TESTS",
    }
    flag = live_modules.get(request.path.name)
    if flag and os.environ.get(flag) == "1":
        return

    def blocked(*args, **kwargs):
        raise AssertionError("Real network connections are forbidden in mock tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def fake_clock():
    class Clock:
        now = datetime(2030, 1, 6, 23, 59, tzinfo=UTC)
        elapsed = 0.0

        def advance(self, seconds):
            self.now += timedelta(seconds=seconds)
            self.elapsed += seconds

        async def sleep(self, seconds):
            self.advance(seconds)
            await asyncio.sleep(0)

    return Clock()


@pytest.fixture
def scheduler_clock(fake_clock, monkeypatch):
    from apscheduler.executors import base as executor_base
    from apscheduler.schedulers import base as scheduler_base

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_clock.now.astimezone(tz) if tz else fake_clock.now.replace(tzinfo=None)

    monkeypatch.setattr(scheduler_base, "datetime", FrozenDateTime)
    monkeypatch.setattr(executor_base, "datetime", FrozenDateTime)

    def attach(watcher):
        # Drive wakeups manually; keep the real cron, job store and async executor.
        monkeypatch.setattr(watcher.scheduler, "_start_timer", lambda seconds: None)

    async def tick(watcher, now=None, *, wait=True):
        if now is not None:
            fake_clock.now = now
        watcher.scheduler.wakeup()
        await asyncio.sleep(0)
        if wait:
            executor = watcher.scheduler._lookup_executor("default")
            pending = tuple(executor._pending_futures)
            if pending:
                await asyncio.wait_for(asyncio.gather(*pending), timeout=2)
            await asyncio.sleep(0)

    return SimpleNamespace(attach=attach, tick=tick)


@pytest.fixture
async def telegram_harness(fake_clock, monkeypatch):
    from app import telegram_state

    monkeypatch.setattr(telegram_state, "now_ms", lambda: int(fake_clock.now.timestamp() * 1000))
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    rules = RuleStorage(redis)
    calls = []
    market = SimpleNamespace(
        prefix="binance:spot:test", settings=Settings(_env_file=None), value="75", count=1000,
    )

    async def closed(symbol, timeframe, boundary):
        calls.append((symbol, timeframe, boundary, fake_clock.now))
        duration = DURATIONS[timeframe]
        return KlinesResult(
            market="spot", symbol=symbol, interval=timeframe, source="binance",
            cache_key="fake", fetched_at=fake_clock.now,
            candles=[Candle(open_time=boundary - (market.count - i) * duration,
                            close_time=boundary - (market.count - i - 1) * duration - 1,
                            close=market.value) for i in range(market.count)],
        )

    market.closed_klines = AsyncMock(side_effect=closed)
    sender = SimpleNamespace(send_message=AsyncMock(
        return_value=DeliveryResult("accepted", message_id=1),
    ))
    watcher = TelegramScheduler(market, rules, sender, clock=lambda: fake_clock.now,
                               sleep=fake_clock.sleep)

    async def create(**changes):
        data = {"symbol": "BTCUSDT", "timeframe": "1h", "indicator": {"type": "sma", "length": 1},
                    "operator": "gte", "target": 70}
        data.update(changes)
        return await rules.create_rule(RuleCreate(**data))

    yield SimpleNamespace(redis=redis, rules=rules, watcher=watcher, market=market,
                          sender=sender, clock=fake_clock, calls=calls, create=create)
    await watcher.stop()
    await redis.aclose()
