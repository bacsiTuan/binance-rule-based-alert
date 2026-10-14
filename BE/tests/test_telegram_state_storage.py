import asyncio
import json

import fakeredis.aioredis
import pytest
from redis.exceptions import ConnectionError, WatchError

from app.errors import CacheError
from app.models import RuleCreate
from app.rules import RuleStorage
from app.telegram_state import META_KEY, TelegramStateStore


@pytest.mark.parametrize("values,expected", [
    ([68, 70, 75, 69, 71], 2), ([75, 75, 80], 1),
])
async def test_persisted_condition(values, expected):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    rules = RuleStorage(redis)
    rule = await rules.create_rule(RuleCreate(
        symbol="BTCUSDT", timeframe="1h", indicator={"type": "rsi", "length": 14},
        operator="gte", target=70,
    ))
    store = TelegramStateStore(redis, "binance:spot:test")
    await store.bootstrap([rule])
    meta = json.loads(await redis.hget(META_KEY, str(rule.id)))
    boundary = meta["activated_at_ms"] + 1000
    events = []
    for value in values:
        result = await store.observe(rule, boundary, boundary - 3600000, str(value), "70")
        if result:
            events.append(result)
        assert await store.observe(rule, boundary, boundary - 3600000, str(value), "70") is None
        store = TelegramStateStore(redis, "binance:spot:test")
        await store.bootstrap([rule])
        boundary += 3600000
    assert len(events) == expected
    assert await redis.ttl(store.key) == -1
    await redis.aclose()


@pytest.mark.parametrize("conflicts", [1, 3])
async def test_cas_retry_bound(telegram_harness, monkeypatch, conflicts):
    h = telegram_harness
    rule = await h.create()
    await h.watcher.store.bootstrap([rule])
    h.clock.advance(65)
    boundary = int(h.clock.now.timestamp() * 1000) - 5000
    pipeline_type = type(h.redis.pipeline())
    execute = pipeline_type.execute
    count = 0

    async def conflict(pipe, *args, **kwargs):
        nonlocal count
        count += 1
        if count <= conflicts:
            raise WatchError("mock concurrent mutation")
        return await execute(pipe, *args, **kwargs)

    monkeypatch.setattr(pipeline_type, "execute", conflict)
    result = await h.watcher.store.observe(rule, boundary, boundary - 3600000, "75", "70")
    assert count == min(conflicts + 1, 3)
    assert bool(result) == (conflicts < 3)
    if conflicts == 3:
        state = json.loads(await h.redis.hget(h.watcher.store.key, str(rule.id)))
        assert state["condition"] == "unknown"


async def test_concurrent_observation_reserves_once(telegram_harness):
    h = telegram_harness
    rule = await h.create()
    await h.watcher.store.bootstrap([rule])
    h.clock.advance(65)
    boundary = int(h.clock.now.timestamp() * 1000) - 5000
    results = await asyncio.gather(*(
        h.watcher.store.observe(rule, boundary, boundary - 3600000, "75", "70")
        for _ in range(6)
    ))
    assert sum(result is not None for result in results) == 1


async def test_redis_failure_cannot_reserve(telegram_harness, monkeypatch):
    h = telegram_harness
    rule = await h.create()
    await h.watcher.store.bootstrap([rule])
    h.clock.advance(65)
    boundary = int(h.clock.now.timestamp() * 1000) - 5000

    async def broken(*args, **kwargs):
        raise ConnectionError("mock redis failure")

    monkeypatch.setattr(type(h.redis.pipeline()), "execute", broken)
    with pytest.raises(CacheError):
        await h.watcher.store.observe(rule, boundary, boundary - 3600000, "75", "70")
    h.sender.send_message.assert_not_awaited()


async def test_finalize_exhausted_cas_reports_failure(telegram_harness, monkeypatch):
    h = telegram_harness
    rule = await h.create()
    await h.watcher.store.bootstrap([rule])
    h.clock.advance(65)
    boundary = int(h.clock.now.timestamp() * 1000) - 5000
    generation, event = await h.watcher.store.observe(
        rule, boundary, boundary - 3600000, "75", "70",
    )

    async def conflict(*args, **kwargs):
        raise WatchError("mock conflict")

    monkeypatch.setattr(type(h.redis.pipeline()), "execute", conflict)
    with pytest.raises(CacheError):
        await h.watcher.store.finalize(rule.id, generation, event.event_id,
                                       "accepted", message_id=1)
