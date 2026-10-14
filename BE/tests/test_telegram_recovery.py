import json
from datetime import UTC, datetime
from uuid import uuid4

import fakeredis.aioredis
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models import RuleCreate, RuleUpdate
from app.rules import RuleStorage
from app.service.telegram_scheduler import DURATIONS, TelegramScheduler, boundary_ms
from app.telegram_state import META_KEY, MonitorState, TelegramStateStore


@pytest.fixture
async def context():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    rules = RuleStorage(redis)
    rule = await rules.create_rule(RuleCreate(
        symbol="BTCUSDT", timeframe="1h", indicator={"type": "sma", "length": 1},
        operator="gte", target=70,
    ))
    store = TelegramStateStore(redis, "binance:spot:test")
    await store.bootstrap([rule])
    meta = json.loads(await redis.hget(META_KEY, str(rule.id)))
    boundary = meta["activated_at_ms"] + 3600000
    yield redis, rules, rule, store, boundary
    await redis.aclose()


async def test_failed_delivery_does_not_rearm(context):
    _redis, _rules, rule, store, boundary = context
    generation, event = await store.observe(rule, boundary, boundary - 3600000, "75", "70")
    await store.finalize(rule.id, generation, event.event_id, "unknown")
    assert await store.observe(rule, boundary + 3600000, boundary, "75", "70") is None
    assert await store.observe(rule, boundary + 7200000, boundary, "69", "70") is None
    assert await store.observe(rule, boundary + 10800000, boundary, "71", "70")


async def test_crash_reservation_unknown_no_replay(context):
    redis, _rules, rule, store, boundary = context
    await store.observe(rule, boundary, boundary - 3600000, "75", "70")
    restarted = TelegramStateStore(redis, "binance:spot:test")
    await restarted.bootstrap([rule])
    state = MonitorState.model_validate_json(await redis.hget(store.key, str(rule.id)))
    assert state.last_event.delivery_status == "unknown"
    assert await restarted.observe(rule, boundary + 3600000, boundary, "75", "70") is None


async def test_missing_state_fail_closed_and_toggle_recovers(context):
    redis, rules, rule, store, boundary = context
    await redis.hdel(store.key, str(rule.id))
    await store.bootstrap([rule])
    assert await store.observe(rule, boundary, boundary - 3600000, "75", "70") is None
    await rules.update_rule(rule.id, RuleUpdate(enabled=False))
    rule = await rules.update_rule(rule.id, RuleUpdate(enabled=True))
    await store.bootstrap([rule])
    assert await store.observe(rule, boundary, boundary - 3600000, "75", "70")


async def test_stale_generation_cannot_finalize_new_event(context):
    redis, rules, rule, store, boundary = context
    generation, event = await store.observe(rule, boundary, boundary - 3600000, "75", "70")
    rule = await rules.update_rule(rule.id, RuleUpdate(target=71))
    await store.bootstrap([rule])
    await store.finalize(rule.id, generation, event.event_id, "accepted", message_id=12)
    state = MonitorState.model_validate_json(await redis.hget(store.key, str(rule.id)))
    assert state.condition == "unknown"
    assert state.last_event is None


async def test_invalid_value_does_not_rearm(context):
    _redis, _rules, rule, store, boundary = context
    await store.observe(rule, boundary, boundary - 3600000, "75", "70")
    assert await store.observe(rule, boundary + 3600000, boundary, "NaN", "70") is None
    assert await store.observe(rule, boundary + 7200000, boundary, "75", "70") is None


async def test_delete_cleans_state(context):
    redis, rules, rule, store, _boundary = context
    assert await rules.delete_rule(rule.id)
    assert await redis.hget(store.key, str(rule.id)) is None
    assert await redis.hget(META_KEY, str(rule.id)) is None


@pytest.mark.parametrize("patch", [
    {"condition": "bad"}, {"schema_version": 2}, {"last_value": "NaN"},
    {"generation": "bad"}, {"updated_at_ms": 1.5},
])
def test_invalid_state_rejected(patch):
    fields = {"generation": str(uuid4()), "rule_id": 1, "updated_at_ms": 123}
    fields.update(patch)
    with pytest.raises(ValidationError):
        MonitorState(**fields)


async def test_schedule_starts_after_boundary_even_within_grace(context):
    _redis, rules, _rule, _store, _boundary = context
    now = datetime.now(UTC).replace(minute=0, second=2, microsecond=0)
    class Market:
        prefix = "binance:spot:test"
        settings = Settings(_env_file=None)
    watcher = TelegramScheduler(Market(), rules, None, clock=lambda: now)
    await watcher.start()
    for timeframe, duration in DURATIONS.items():
        job = watcher.scheduler.get_job(f"telegram-{timeframe}")
        expected = boundary_ms(now, timeframe) + duration + 5000
        assert int(job.next_run_time.timestamp() * 1000) == expected
    await watcher.stop()


async def test_disabled_before_send_cancels(context):
    _redis, rules, rule, store, boundary = context
    generation, event = await store.observe(rule, boundary, boundary - 3600000, "75", "70")
    class Market:
        prefix = "binance:spot:test"
        settings = Settings(_env_file=None)
    watcher = TelegramScheduler(Market(), rules, None)
    await rules.update_rule(rule.id, RuleUpdate(enabled=False))
    await watcher.deliver(rule, generation, event)
    assert not await store.current(rule.id, generation)


@pytest.mark.parametrize("frame,now,expected", [
    ("1w", datetime(2027, 1, 3, 23, 59, tzinfo=UTC), datetime(2026, 12, 28, tzinfo=UTC)),
    ("1w", datetime(2027, 1, 4, tzinfo=UTC), datetime(2027, 1, 4, tzinfo=UTC)),
    ("1d", datetime(2027, 1, 1, 23, 59, tzinfo=UTC), datetime(2027, 1, 1, tzinfo=UTC)),
])
def test_calendar_edges(frame, now, expected):
    assert boundary_ms(now, frame) == int(expected.timestamp() * 1000)
