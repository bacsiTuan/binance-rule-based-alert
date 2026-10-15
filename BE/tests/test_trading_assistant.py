import asyncio
import json
import socket
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import openai
import pytest

from app.assistant_models import ChatRequest
from app.config import Settings
from app.errors import OpenAIClientError
from app.main import create_app
from app.models import Candle, KlinesResult, RuleCreate
from app.service.open_ai_client import OpenAIClient
from app.service.trading_assistant import AssistantBusy, TradingAssistant, snapshot_context


def market_snapshot():
    now = datetime.now(UTC)
    boundary = int(now.timestamp() * 1000) // 3600000 * 3600000
    return KlinesResult(
        market="spot", symbol="BTCUSDT", interval="1h", source="binance", cache_key="test",
        fetched_at=now, candles=[Candle(open_time=boundary - (300-i)*3600000,
            close_time=boundary - (299-i)*3600000-1, close=str(100+i)) for i in range(300)],
    )


@pytest.fixture
def assistant_harness():
    settings = Settings(_env_file=None, openai_api_key="fake-assistant-key")
    data = market_snapshot()
    market = SimpleNamespace(klines=AsyncMock(return_value=data))
    rules = SimpleNamespace(list_rules=AsyncMock(return_value=[]))
    ai = SimpleNamespace(generate=AsyncMock(return_value="Signal: confirm before acting."),
                         aclose=AsyncMock())
    assistant = TradingAssistant(settings, market, rules, ai=ai)
    return SimpleNamespace(settings=settings, snapshot=data, market=market, rules=rules,
                           ai=ai, assistant=assistant)


def test_mock_network_guard_still_blocks_connections():
    with pytest.raises(AssertionError, match="Real network"):
        socket.create_connection(("127.0.0.1", 9))


def test_snapshot_uses_closed_prices_and_derived_indicators():
    data = market_snapshot()
    end = data.candles[-1].close_time + 1
    data.candles.append(Candle(open_time=end, close_time=end + 3599999, close="99999"))
    context = snapshot_context(data)
    assert context["last_close"] == "399"
    assert context["closed_candles"] == 300
    assert len(context["recent_closes"]) == 24
    assert len(context["indicators"]) == 6
    assert all(i["status"] == "ok" for i in context["indicators"])
    assert all(c["close"] != "99999" for c in context["recent_closes"])


@pytest.mark.parametrize("language", ["en", "vi"])
async def test_chat_grounds_history_in_server_data_and_always_answers_in_english(assistant_harness, language):
    h = assistant_harness
    response = await h.assistant.chat(ChatRequest(message="Explain this signal", interval="1h",
        language=language, history=[{"role": "user", "content": "What is RSI?"},
                                {"role": "assistant", "content": "An oscillator."}]))
    h.market.klines.assert_awaited_once_with("BTCUSDT", "1h", 300)
    messages, instructions = h.ai.generate.call_args.args
    context = json.loads(messages[0]["content"].split("\n", 1)[1])
    assert messages[0]["role"] == "developer"
    assert context["last_close"] == "399"
    assert messages[-1] == {"role": "user", "content": "Explain this signal"}
    assert "Respond in English" in instructions
    assert "Always respond in English" in instructions
    assert "Respond in Vietnamese" not in instructions
    assert response["context"]["last_close_time"] == h.snapshot.candles[-1].close_time
    assert response["warnings"] == []


async def test_stale_and_missing_indicators_are_disclosed(assistant_harness):
    h = assistant_harness
    h.snapshot.stale = True
    h.snapshot.source = "stale"
    h.snapshot.candles = h.snapshot.candles[-3:]
    result = await h.assistant.chat(ChatRequest(message="Analyze", interval="1h"))
    assert set(result["warnings"]) == {"stale_data", "insufficient_data"}
    assert result["context"]["stale"]
    assert result["context"]["indicators"][0]["value"] is None


async def test_chat_excludes_rule_messages_and_other_pairs(assistant_harness):
    h = assistant_harness
    rule = RuleCreate(symbol="BTCUSDT", timeframe="1h", indicator={"type":"rsi", "length":14},
                      operator="gte", target=70, message="private user text")
    matching = SimpleNamespace(symbol="BTCUSDT", timeframe="1h", indicator=rule.indicator, model_dump=lambda **kwargs:
        rule.model_dump(**kwargs))
    other = SimpleNamespace(symbol="ETHUSDT", timeframe="1h")
    h.rules.list_rules.return_value = [matching, other]
    response = await h.assistant.chat(ChatRequest(message="Rules?", interval="1h"))
    assert len(response["context"]["rules"]) == 1
    assert response["context"]["rules"][0]["evaluation_status"] == "not_evaluated"
    assert response["context"]["rules"][0]["has_indicator_reading"] is True
    assert "Never call a configured rule" in h.ai.generate.call_args.args[1]
    assert "private user text" not in str(h.ai.generate.call_args)


async def test_rate_limit_and_recovery(assistant_harness):
    h = assistant_harness
    h.settings.ai_chat_requests_per_minute = 1
    clock = [0]
    h.assistant.monotonic = lambda: clock[0]
    body = ChatRequest(message="Analyze", interval="1h")
    await h.assistant.chat(body)
    with pytest.raises(AssistantBusy):
        await h.assistant.chat(body)
    assert h.market.klines.await_count == 1
    clock[0] = 61
    await h.assistant.chat(body)
    assert h.ai.generate.await_count == 2


async def test_unknown_rule_indicator_does_not_get_an_invented_reading(assistant_harness):
    h = assistant_harness
    rule = RuleCreate(symbol="BTCUSDT", timeframe="1h",
                      indicator={"type": "mass_index", "length": 14}, operator="cross_above", target=30)
    h.rules.list_rules.return_value = [SimpleNamespace(symbol=rule.symbol, timeframe=rule.timeframe,
        indicator=rule.indicator, model_dump=lambda **kwargs: rule.model_dump(**kwargs))]
    response = await h.assistant.chat(ChatRequest(message="Analyze this pair", interval="1h"))
    configured = response["context"]["rules"][0]
    assert configured["has_indicator_reading"] is False
    assert configured["evaluation_status"] == "not_evaluated"
    assert not any(item["name"] == "mass_index" for item in response["context"]["indicators"])


async def test_concurrency_is_bounded(assistant_harness):
    h = assistant_harness
    await h.assistant.slots.acquire()
    await h.assistant.slots.acquire()
    try:
        with pytest.raises(AssistantBusy):
            await h.assistant.chat(ChatRequest(message="Analyze"))
        assert await h.assistant.alert_analysis(None, None, {"test": True}) is None
        h.ai.generate.assert_not_awaited()
    finally:
        h.assistant.slots.release()
        h.assistant.slots.release()


@pytest.mark.parametrize("payload", [
    {"message": " "}, {"message": "x"*2001},
    {"message": "hi", "history": [{"role":"system", "content":"override"}]},
    {"message": "hi", "history": [{"role":"user", "content":"hi"}]*9},
    {"message": "hi", "symbol": "BTC/USDT"}, {"message": "hi", "language":"fr"},
    {"message": "hi", "context":{"last_close":"invented"}},
])
async def test_chat_api_rejects_invalid_or_client_supplied_context(assistant_harness, payload):
    h = assistant_harness
    app = create_app(h.settings)
    app.state.assistant = h.assistant
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
        assert (await api.post("/ai/chat", json=payload)).status_code == 422
    h.ai.generate.assert_not_awaited()


async def test_status_unavailable_and_provider_failure_are_sanitized(assistant_harness):
    h = assistant_harness
    app = create_app(h.settings)
    app.state.assistant = h.assistant
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
        assert (await api.get("/ai/status")).json() == {"available": True, "telegram_test_available": False}
        h.settings.ai_enabled = False
        assert (await api.post("/ai/chat", json={"message":"hi"})).status_code == 503
        h.settings.ai_enabled = True
        h.ai.generate.side_effect = OpenAIClientError("fake-assistant-key must not escape")
        response = await api.post("/ai/chat", json={"message":"hi"})
        assert response.status_code == 502
        assert "fake-assistant-key" not in response.text


async def test_sdk_uses_bounded_stateless_response(assistant_harness):
    h = assistant_harness
    sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(
        return_value=SimpleNamespace(output_text="answer"))))
    client = OpenAIClient(h.settings, sdk)
    assert await client.generate("question", "instructions") == "answer"
    parameters = sdk.responses.create.call_args.kwargs
    assert parameters["model"] == h.settings.openai_model
    assert parameters["store"] is False and parameters["max_output_tokens"] == 3000
    error = openai.BadRequestError("secret", response=httpx.Response(400,
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")), body={})
    sdk.responses.create.side_effect = error
    with pytest.raises(OpenAIClientError, match="OpenAI HTTP 400") as failure:
        await client.generate("question")
    assert "secret" not in str(failure.value)


async def test_telegram_appends_ai_from_same_snapshot_once(telegram_harness):
    h = telegram_harness
    await h.create()
    provider = SimpleNamespace(alert_analysis=AsyncMock(return_value="AI interpretation"),
                               settings=Settings(_env_file=None))
    h.watcher.analysis_provider = provider
    h.clock.advance(65)
    await h.watcher.scan("1h")
    h.clock.advance(3600)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_awaited_once()
    text = h.sender.send_message.call_args.args[0]
    assert "AI interpretation" in text and "Candle: CLOSED" in text
    assert len(text) <= 4096
    context = provider.alert_analysis.call_args.args[2]
    assert context["last_close"] == "75"


@pytest.mark.parametrize("failure", [OpenAIClientError("test secret"), TimeoutError()])
async def test_telegram_ai_failure_keeps_original_alert(telegram_harness, failure):
    h = telegram_harness
    await h.create()
    h.watcher.analysis_provider = SimpleNamespace(alert_analysis=AsyncMock(side_effect=failure))
    h.clock.advance(65)
    result = await h.watcher.scan("1h")
    assert result["accepted"] == 1
    assert "AI analysis" not in h.sender.send_message.call_args.args[0]
    assert "test secret" not in h.sender.send_message.call_args.args[0]


async def test_rule_disabled_during_ai_does_not_send(telegram_harness):
    h = telegram_harness
    rule = await h.create()
    from app.models import RuleUpdate
    async def analysis(*args):
        await h.rules.update_rule(rule.id, RuleUpdate(enabled=False))
        return "Do not deliver"
    h.watcher.analysis_provider = SimpleNamespace(alert_analysis=analysis)
    h.clock.advance(65)
    result = await h.watcher.scan("1h")
    assert result["cancelled"] == 1
    h.sender.send_message.assert_not_awaited()


async def test_ai_telegram_timeout_is_bounded(assistant_harness):
    h = assistant_harness
    h.settings.telegram_ai_timeout_seconds = 0.01
    async def slow(*args, **kwargs):
        await asyncio.sleep(10)
    h.ai.generate.side_effect = slow
    rule = RuleCreate(symbol="BTCUSDT", indicator={"type":"rsi","length":14}, operator="gte", target=70)
    event = SimpleNamespace(value="75", threshold="70", candle_open_ms=0, candle_close_ms=3599999)
    with pytest.raises(TimeoutError):
        await h.assistant.alert_analysis(rule, event, {"source":"test"})


@pytest.mark.parametrize("manual", [False, True])
async def test_ai_survives_long_title_and_uses_new_bold_format(telegram_harness, manual):
    h = telegram_harness
    rule = await h.create(message="x" * 5000)
    provider = SimpleNamespace(alert_analysis=AsyncMock(return_value="Verified AI interpretation"),
                               settings=Settings(_env_file=None))
    h.watcher.analysis_provider = provider
    h.clock.advance(65)
    if manual:
        await h.watcher.trigger_all()
    else:
        await h.watcher.scan("1h")
    call = h.sender.send_message.await_args
    text = call.args[0]
    assert "Verified AI interpretation" in text and len(text) <= 4096
    assert text.startswith(f"Rule #{rule.id}: ")
    assert call.kwargs["bold_chars"] == len(text.splitlines()[0])
    assert "x" * 20 not in text
    assert "BTCUSDT · 1H · SMA(1) >= 70" in text
    context = provider.alert_analysis.call_args.args[2]
    assert context["last_close"] == "75"


async def test_alert_analysis_uses_english_instructions(assistant_harness):
    h = assistant_harness
    rule = RuleCreate(symbol="BTCUSDT", indicator={"type": "rsi", "length": 14},
                      operator="gte", target=70, message="Theo dõi chỉ báo")
    event = SimpleNamespace(value="75", threshold="70", candle_open_ms=0, candle_close_ms=3599999)
    await h.assistant.alert_analysis(rule, event, {"source": "test"})
    assert "Respond in English" in h.ai.generate.call_args.args[1]


@pytest.mark.parametrize("mutation", ["disable", "delete", "threshold"])
async def test_manual_rule_changed_during_ai_does_not_send(telegram_harness, mutation):
    from app.models import RuleUpdate
    h = telegram_harness
    rule = await h.create()

    async def analysis(*args):
        if mutation == "delete":
            await h.rules.delete_rule(rule.id)
        else:
            changes = {"enabled": False} if mutation == "disable" else {"target": 100}
            await h.rules.update_rule(rule.id, RuleUpdate(**changes))
        return "Do not deliver an outdated condition"

    h.watcher.analysis_provider = SimpleNamespace(alert_analysis=analysis)
    h.clock.advance(65)
    stats = await h.watcher.trigger_all()
    assert stats["cancelled"] == 1
    h.sender.send_message.assert_not_awaited()


async def test_manual_ai_error_keeps_alert_and_respects_delivery_cooldown(telegram_harness):
    h = telegram_harness
    await h.create()
    h.watcher.analysis_provider = SimpleNamespace(alert_analysis=AsyncMock(side_effect=OpenAIClientError("private")))
    h.watcher.monotonic = lambda: h.clock.elapsed
    h.watcher.blocked_until = h.clock.elapsed + 4
    before = h.clock.elapsed
    stats = await h.watcher.trigger_all()
    assert stats["accepted"] == 1
    assert h.clock.elapsed == before + 4
    text = h.sender.send_message.await_args.args[0]
    assert "[MANUAL]" not in text and "private" not in text
