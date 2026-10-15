import json

import pytest

from app.models import RuleUpdate
from app.telegram_state import META_KEY


@pytest.mark.parametrize("changes", [
    {"target": 71}, {"timeframe": "1d"}, {"symbol": "ETHUSDT"},
    {"indicator": {"type": "ema", "length": 14}}, {"operator": "lt"},
    {"candle_mode": "include_current"}, {"enabled": False},
])
async def test_condition_changes_generation(telegram_harness, changes):
    h = telegram_harness
    rule = await h.create()
    before = json.loads(await h.redis.hget(META_KEY, str(rule.id)))["generation"]
    await h.rules.update_rule(rule.id, RuleUpdate(**changes))
    after = json.loads(await h.redis.hget(META_KEY, str(rule.id)))["generation"]
    assert after != before


@pytest.mark.parametrize("changes", [
    {"target": 70}, {"target": 70.0}, {"message": "new"}, {"notifications": []},
    {"trigger_type": "every_time"}, {"expiration": "2031-01-01T00:00:00Z"},
])
async def test_non_condition_change_preserves_generation(telegram_harness, changes):
    h = telegram_harness
    rule = await h.create()
    before = await h.redis.hget(META_KEY, str(rule.id))
    await h.rules.update_rule(rule.id, RuleUpdate(**changes))
    assert await h.redis.hget(META_KEY, str(rule.id)) == before


async def test_a_b_a_resets_and_legacy_bootstrap_preserves_rule(telegram_harness):
    h = telegram_harness
    rule = await h.create()
    before = await h.redis.hget(META_KEY, str(rule.id))
    await h.rules.update_rule(rule.id, RuleUpdate(target=71))
    await h.rules.update_rule(rule.id, RuleUpdate(target=70))
    assert await h.redis.hget(META_KEY, str(rule.id)) != before
    await h.redis.hdel(META_KEY, str(rule.id))
    raw = await h.redis.hget(h.rules.key, str(rule.id))
    await h.watcher.store.bootstrap([rule])
    assert await h.redis.hget(h.rules.key, str(rule.id)) == raw
    assert await h.redis.ttl(META_KEY) == -1


async def test_condition_change_regenerates_message_unless_patch_sets_one(telegram_harness):
    h = telegram_harness
    rule = await h.create(indicator={"type": "rsi", "length": 14}, operator="lt", target=30)
    assert rule.message == "Rsi(14) Less Than 30 on BTCUSDT"
    # The edit form resends the stored message alongside the new condition.
    updated = await h.rules.update_rule(rule.id, RuleUpdate(operator="gt", message=rule.message))
    assert updated.message == "Rsi(14) Greater Than 30 on BTCUSDT"
    assert (await h.rules.get_rule(rule.id)).message == updated.message
    updated = await h.rules.update_rule(rule.id, RuleUpdate(enabled=False))
    assert updated.message == "Rsi(14) Greater Than 30 on BTCUSDT"
    updated = await h.rules.update_rule(rule.id, RuleUpdate(target=40, message="custom"))
    assert updated.message == "custom"
