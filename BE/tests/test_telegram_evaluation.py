import pytest

from app.models import RuleUpdate
from app.service.telegram_client import DeliveryResult


@pytest.mark.parametrize("name,period,target,expected", [
    ("sma", 1, 75, 1), ("ema", 14, 75, 1), ("rsi", 999, 50, 1),
    ("sma", 999, 76, 0),
])
async def test_supported_indicators_closed_history(telegram_harness, name, period, target, expected):
    h = telegram_harness
    await h.create(indicator={"type": name, "length": period}, target=target)
    h.clock.advance(65)
    await h.watcher.scan("1h")
    assert h.sender.send_message.await_count == expected


async def test_duplicate_selection_and_message_limit(telegram_harness):
    h = telegram_harness
    await h.create(message="x" * 5000)
    await h.create(target=80)
    await h.create(symbol="ETHUSDT", indicator={"type": "ema", "length": 2})
    h.clock.advance(65)
    await h.watcher.scan("1h")
    assert len(h.calls) == 2
    assert h.sender.send_message.await_count == 2
    texts = [call.args[0] for call in h.sender.send_message.await_args_list]
    assert all(len(text) <= 4096 for text in texts)
    assert all("Candle: CLOSED" in text and "Timezone: UTC+07:00" in text for text in texts)


async def test_insufficient_history_no_event(telegram_harness):
    h = telegram_harness
    h.market.count = 1
    await h.create(indicator={"type": "rsi", "length": 14})
    h.clock.advance(65)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_not_awaited()


async def test_decimal_not_rounded_before_compare(telegram_harness):
    h = telegram_harness
    h.market.value = "69.9999999999999999999999999999"
    await h.create()
    h.clock.advance(65)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_not_awaited()
    h.market.value = "70.0000000000000000000000000001"
    h.clock.advance(3600)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_awaited_once()


@pytest.mark.parametrize("status", ["failed", "unknown"])
async def test_send_failure_no_retry_but_new_event_allowed(telegram_harness, status):
    h = telegram_harness
    await h.create()
    h.sender.send_message.return_value = DeliveryResult(status)
    h.clock.advance(65)
    for value in ("75", "75", "69", "71"):
        h.market.value = value
        await h.watcher.scan("1h")
        h.clock.advance(3600)
    assert h.sender.send_message.await_count == 2


async def test_manual_trigger_sends_matching_rules_without_touching_state(telegram_harness):
    h = telegram_harness
    await h.create()
    await h.create(target=80)
    off = await h.create()
    await h.rules.update_rule(off.id, RuleUpdate(enabled=False))
    h.clock.advance(65)
    stats = await h.watcher.trigger_all()
    assert (stats["scanned"], stats["triggered"], stats["accepted"], stats["skipped"]) == (2, 1, 1, 1)
    h.sender.send_message.assert_awaited_once()
    # The scheduled scan still delivers: manual runs share no dedup state.
    await h.watcher.scan("1h")
    assert h.sender.send_message.await_count == 2
