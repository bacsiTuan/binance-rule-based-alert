import json

import pytest

from app.errors import BinanceError


@pytest.mark.parametrize("operator,values,counts,symbol", [
    ("gt", ["70", "71", "72", "70", "71"], [0, 1, 1, 1, 2], ">"),
    ("gte", ["69", "70", "71", "69", "70"], [0, 1, 1, 1, 2], ">="),
    ("lt", ["70", "69", "68", "70", "69"], [0, 1, 1, 1, 2], "<"),
    ("lte", ["71", "70", "69", "71", "70"], [0, 1, 1, 1, 2], "<="),
])
async def test_comparison_boundaries_and_rearm(telegram_harness, operator, values, counts, symbol):
    h = telegram_harness
    await h.create(operator=operator)
    h.clock.advance(65)
    for value, count in zip(values, counts, strict=True):
        h.market.value = value
        await h.watcher.scan("1h")
        await h.watcher.scan("1h")
        assert h.sender.send_message.await_count == count
        h.clock.advance(3600)
    assert f" {symbol} 70" in h.sender.send_message.await_args.args[0]


@pytest.mark.parametrize("operator,value", [
    ("gt", "71"), ("gte", "70"), ("lt", "69"), ("lte", "70"),
])
async def test_initial_true_comparison(telegram_harness, operator, value):
    h = telegram_harness
    await h.create(operator=operator)
    h.market.value = value
    h.clock.advance(65)
    await h.watcher.scan("1h")
    h.clock.advance(3600)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_awaited_once()


async def test_readable_message_format(telegram_harness):
    h = telegram_harness
    await h.create(target=40)
    h.market.value = "51.657346496072873893715394643415615554025685290631"
    h.clock.advance(65)
    await h.watcher.scan("1h")
    text = h.sender.send_message.await_args.args[0]
    assert "Value: 51.66 >= 40\n" in text
    assert "Threshold:" not in text
    assert "Open: 07/01/2030 06:00:00\n" in text
    assert "Close: 07/01/2030 06:59:59" in text
    assert "Timezone: UTC+07:00" in text


@pytest.mark.parametrize("values,expected", [
    (["68", "70", "75", "69", "71"], 2), (["75", "75", "80"], 1),
])
async def test_threshold_sequence(telegram_harness, values, expected):
    h = telegram_harness
    await h.create()
    h.clock.advance(65)
    for value in values:
        h.market.value = value
        await h.watcher.scan("1h")
        await h.watcher.scan("1h")
        h.clock.advance(3600)
    assert h.sender.send_message.await_count == expected


async def test_missing_data_and_network_failure_keep_latch(telegram_harness):
    h = telegram_harness
    rule = await h.create()
    h.clock.advance(65)
    await h.watcher.scan("1h")
    before = json.loads(await h.redis.hget(h.watcher.store.key, str(rule.id)))
    fetch = h.market.closed_klines.side_effect
    for failure in (None, BinanceError("mock failure")):
        h.clock.advance(3600)
        if failure is None:
            h.market.closed_klines.side_effect = None
            h.market.closed_klines.return_value = None
        else:
            h.market.closed_klines.side_effect = failure
        await h.watcher.scan("1h")
        state = json.loads(await h.redis.hget(h.watcher.store.key, str(rule.id)))
        assert state["condition"] == "latched"
        assert state["last_processed_close_ms"] == before["last_processed_close_ms"]
    h.market.closed_klines.side_effect = fetch
    h.clock.advance(3580)  # Last readiness pass ended at B+30, not B+5.
    await h.watcher.scan("1h")
    assert h.sender.send_message.await_count == 1


async def test_message_is_bold_title_after_rule_id(telegram_harness):
    h = telegram_harness
    rule = await h.create(target=40, message="Theo dõi chỉ báo ⚡")
    h.clock.advance(65)
    await h.watcher.scan("1h")
    call = h.sender.send_message.await_args
    title = f"Rule #{rule.id}: BTCUSDT · 1H · SMA(1) >= 40"
    assert call.args[0].startswith(title + "\nBTCUSDT · SPOT · 1H")
    assert "Theo dõi chỉ báo" not in call.args[0]
    assert call.kwargs["bold_chars"] == len(title)
