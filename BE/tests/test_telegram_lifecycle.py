import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import pytest

from app import main
from app.config import Settings
from app.errors import CacheError
from app.models import RuleUpdate
from app.service.telegram_client import DeliveryResult
from app.telegram_state import MonitorState


async def test_shutdown_cancels_inflight_without_second_send(telegram_harness, monkeypatch):
    from app.service import telegram_scheduler
    h = telegram_harness
    await h.create()
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    async def blocked(text):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    h.sender.send_message.side_effect = blocked
    h.clock.advance(65)
    task = asyncio.create_task(h.watcher.scan("1h"))
    await asyncio.wait_for(entered.wait(), 1)
    monkeypatch.setattr(telegram_scheduler, "SHUTDOWN_SECONDS", 0.01)
    await asyncio.wait_for(h.watcher.stop(), 1)
    assert task.cancelled()
    assert cancelled.is_set()
    assert not h.watcher.tasks
    h.sender.send_message.assert_awaited_once()
    rules = await h.rules.list_rules()
    await h.watcher.store.bootstrap(rules)
    state = MonitorState.model_validate_json(
        await h.redis.hget(h.watcher.store.key, str(rules[0].id)),
    )
    assert state.condition == "latched"
    assert state.last_event.delivery_status == "unknown"


async def test_shutdown_interrupts_cooldown_without_sending(telegram_harness):
    h = telegram_harness
    await h.create()
    entered = asyncio.Event()
    async def sleep(seconds):
        if seconds > 0:
            entered.set()
            await asyncio.Event().wait()
        await asyncio.sleep(0)
    h.watcher.sleep = sleep
    h.watcher.blocked_until = h.watcher.monotonic() + 3600
    h.clock.advance(65)
    task = asyncio.create_task(h.watcher.scan("1h"))
    await asyncio.wait_for(entered.wait(), 1)
    await asyncio.wait_for(h.watcher.stop(), 1)
    await task
    h.sender.send_message.assert_not_awaited()
    assert not h.watcher.tasks


@pytest.mark.parametrize("mutation", ["disable", "delete", "threshold", "expire"])
async def test_mutation_while_waiting_prevents_http(telegram_harness, mutation):
    h = telegram_harness
    rule = await h.create()
    waiting = asyncio.Event()
    release = asyncio.Event()
    async def sleep(seconds):
        if seconds > 0:
            waiting.set()
            await release.wait()
        await asyncio.sleep(0)
    h.watcher.sleep = sleep
    h.watcher.blocked_until = h.watcher.monotonic() + 100
    h.clock.advance(65)
    task = asyncio.create_task(h.watcher.scan("1h"))
    await asyncio.wait_for(waiting.wait(), 1)
    if mutation == "delete":
        await h.rules.delete_rule(rule.id)
    else:
        patch = {
            "disable": {"enabled": False}, "threshold": {"target": 71},
            "expire": {"expiration": "2020-01-01T00:00:00Z"},
        }[mutation]
        await h.rules.update_rule(rule.id, RuleUpdate(**patch))
    release.set()
    stats = await task
    assert stats["triggered"] == 1 and stats["attempted"] == 0
    h.sender.send_message.assert_not_awaited()


async def test_rate_limit_delays_new_event_not_retry(telegram_harness):
    h = telegram_harness
    await h.create()
    await h.create(symbol="ETHUSDT")
    h.watcher.monotonic = lambda: h.clock.elapsed
    h.sender.send_message.side_effect = [
        DeliveryResult("failed", error_code="rate_limited", retry_after=7),
        DeliveryResult("accepted", message_id=2),
    ]
    h.clock.advance(65)
    before = h.clock.elapsed
    stats = await h.watcher.scan("1h")
    assert h.clock.elapsed == before + 7
    assert (stats["triggered"], stats["attempted"], stats["accepted"], stats["failed"]) == (2, 2, 1, 1)
    assert h.sender.send_message.await_count == 2
    await h.watcher.scan("1h")
    assert h.sender.send_message.await_count == 2


async def test_bad_rule_state_does_not_stop_other_rule(telegram_harness):
    h = telegram_harness
    bad = await h.create()
    good = await h.create()
    await h.watcher.store.bootstrap(await h.rules.list_rules())
    await h.redis.hset(h.watcher.store.key, str(bad.id), "invalid")
    h.clock.advance(65)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_awaited_once()
    assert f"Rule #{good.id}" in h.sender.send_message.call_args.args[0]


async def test_start_with_redis_down_keeps_future_schedule(telegram_harness, monkeypatch):
    h = telegram_harness
    await h.create()
    original = h.rules.list_rules
    monkeypatch.setattr(h.rules, "list_rules", AsyncMock(side_effect=CacheError("mock outage")))
    await h.watcher.start()
    assert len(h.watcher.scheduler.get_jobs()) == 3
    monkeypatch.setattr(h.rules, "list_rules", original)
    h.clock.advance(65)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_awaited_once()


async def test_ack_then_state_write_failure_never_retries(telegram_harness, monkeypatch):
    h = telegram_harness
    rule = await h.create()
    original = h.watcher.store.finalize
    monkeypatch.setattr(h.watcher.store, "finalize", AsyncMock(side_effect=CacheError("mock write")))
    h.clock.advance(65)
    stats = await h.watcher.scan("1h")
    assert stats["accepted"] == stats["attempted"] == 1
    monkeypatch.setattr(h.watcher.store, "finalize", original)
    await h.watcher.store.bootstrap([rule])
    h.clock.advance(3600)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_awaited_once()


@pytest.mark.parametrize("enabled,token,chat", [(False, "fake", "1"), (True, None, "1"), (True, "fake", None)])
async def test_missing_config_keeps_api_working(monkeypatch, enabled, token, chat):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(main, "Redis", SimpleNamespace(from_url=lambda *a, **k: redis))
    original = httpx.AsyncClient
    clients = []
    def factory(**kwargs):
        client = original(transport=httpx.MockTransport(
            lambda request: pytest.fail("Disabled watcher must not call upstream")
        ), **kwargs)
        clients.append(client)
        return client
    monkeypatch.setattr(main, "httpx", SimpleNamespace(AsyncClient=factory))
    app = main.create_app(Settings(
        _env_file=None, telegram_enabled=enabled, telegram_bot_token=token, telegram_chat_id=chat,
    ))
    async with (
        app.router.lifespan_context(app),
        original(transport=httpx.ASGITransport(app=app), base_url="http://test") as api,
    ):
        assert (await api.get("/health")).status_code == 200
        response = await api.post("/rules", json={
            "symbol": "BTCUSDT", "indicator": {"type": "sma", "length": 1},
            "operator": "gte", "target": 70,
        })
        assert response.status_code == 201
        assert app.state.telegram_watcher is None
    assert all(client.is_closed for client in clients)


async def test_expired_invalid_legacy_rules_skip_with_reason(telegram_harness, caplog):
    h = telegram_harness
    caplog.set_level("INFO")
    await h.create(expiration="invalid")
    await h.create(expiration="2020-01-01T00:00:00Z")
    await h.create(operator="cross_above")
    await h.create(target={"type": "sma", "length": 2})
    off = await h.create()
    await h.rules.update_rule(off.id, RuleUpdate(enabled=False))
    raw = await h.redis.hgetall(h.rules.key)
    h.clock.advance(65)
    stats = await h.watcher.scan("1h")
    assert stats["skipped"] == 5 and stats["triggered"] == 0
    assert raw == await h.redis.hgetall(h.rules.key)
    for reason in ("invalid_expiration", "expired", "disabled", "unsupported_condition"):
        assert reason in caplog.text
    h.sender.send_message.assert_not_awaited()
