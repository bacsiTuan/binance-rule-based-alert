import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import fakeredis.aioredis
import httpx
import pytest
from redis.exceptions import ConnectionError

from app.assistant_models import ConfirmedTelegramRequest, TelegramTestRequest
from app.config import Settings
from app.errors import CacheError, OpenAIClientError
from app.main import create_app
from app.service.telegram_client import DeliveryResult
from app.service.telegram_test import TelegramTest

TEST_KEY = "manual-test-key-for-mock-only"


@pytest.fixture
async def manual():
    settings = Settings(_env_file=None, telegram_enabled=False, telegram_test_enabled=True,
                        telegram_test_key=TEST_KEY)
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    assistant = SimpleNamespace(available=True, chat=AsyncMock(return_value={
        "answer": "Conditional AI analysis", "context": {"market": "spot",
        "last_close_at": "2026-10-15T00:59:59+00:00", "source": "binance", "stale": False}}))
    sender = SimpleNamespace(send_message=AsyncMock(return_value=DeliveryResult("accepted", 123)))
    service = TelegramTest(settings, assistant, sender, redis)
    app = create_app(settings)
    app.state.assistant = assistant
    app.state.telegram_test = service
    yield SimpleNamespace(settings=settings, redis=redis, assistant=assistant, sender=sender,
                          service=service, app=app)
    await redis.aclose()


def body(**changes):
    return TelegramTestRequest(request_id=uuid4(), confirmed=True, **changes)


async def test_disabled_or_wrong_key_never_calls_ai_or_telegram(manual):
    h = manual
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app), base_url="http://test") as api:
        payload = body().model_dump(mode="json")
        for key in (None, "wrong-key"):
            headers = {"X-Telegram-Test-Key": key} if key else {}
            assert (await api.post("/ai/telegram-test", json=payload, headers=headers)).status_code == 403
        h.settings.telegram_test_enabled = False
        assert (await api.post("/ai/telegram-test", json=payload,
                              headers={"X-Telegram-Test-Key": TEST_KEY})).status_code == 404
        assert "/ai/telegram-test" not in h.app.openapi()["paths"]
    h.assistant.chat.assert_not_awaited()
    h.sender.send_message.assert_not_awaited()
    assert not await h.redis.keys("telegram:manual-test:*")


@pytest.mark.parametrize("status", ["accepted", "failed", "unknown"])
async def test_manual_analysis_labeled_and_deduplicated_across_service_restarts(manual, status):
    h = manual
    h.sender.send_message.return_value = DeliveryResult(status)
    request = body(symbol="ethusdt", interval="1h", language="vi")
    result = await h.service.send(request)
    assert result == {"status": status, "replayed": False}
    restarted = TelegramTest(h.settings, h.assistant, h.sender, h.redis)
    assert await restarted.send(request) == {"status": status, "replayed": True}
    h.sender.send_message.assert_awaited_once()
    text = h.sender.send_message.call_args.args[0]
    assert "Market outlook" in text and "TEST" not in text and "MANUAL" not in text
    assert "ETHUSDT · Market outlook" in text and "Conditional AI analysis" in text
    assert "Close: 15/10/2026 07:59:59" in text
    assert "Timezone: UTC+07:00" in text
    assert "Nhận định thị trường" not in text
    assert h.sender.send_message.call_args.kwargs["bold_chars"] == len(text.splitlines()[0])
    assert TEST_KEY not in text and len(text) <= 4096
    chat_request = h.assistant.chat.call_args.args[0]
    assert chat_request.language == "en" and chat_request.symbol == "ETHUSDT"
    assert "not a triggered trading rule" in chat_request.message
    assert not h.settings.telegram_enabled  # works without enabling the scheduler


async def test_concurrent_duplicate_and_cooldown_do_not_double_send(manual):
    h = manual
    entered, release = asyncio.Event(), asyncio.Event()
    original = h.assistant.chat.return_value

    async def generate(request):
        entered.set()
        await release.wait()
        return original

    h.assistant.chat.side_effect = generate
    request = body()
    first = asyncio.create_task(h.service.send(request))
    await asyncio.wait_for(entered.wait(), 1)
    assert (await h.service.send(request))["status"] == "pending"
    assert (await h.service.send(body()))["status"] == "rate_limited"
    release.set()
    assert (await first)["status"] == "accepted"
    h.sender.send_message.assert_awaited_once()
    changed = request.model_copy(update={"symbol": "ETHUSDT"})
    assert (await h.service.send(changed))["status"] == "conflict"


async def test_ai_failure_and_redis_failure_prevent_sending(manual):
    h = manual
    request = body()
    h.assistant.chat.side_effect = OpenAIClientError("private provider details")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app), base_url="http://test") as api:
        response = await api.post("/ai/telegram-test", json=request.model_dump(mode="json"),
                                  headers={"X-Telegram-Test-Key": TEST_KEY})
        assert response.status_code == 502 and response.json()["detail"] == "ai_failed"
        assert "private provider details" not in response.text
    assert (await h.service.send(request))["status"] == "generation_failed"
    h.sender.send_message.assert_not_awaited()
    h.service.redis = SimpleNamespace(set=AsyncMock(side_effect=ConnectionError("secret")))
    with pytest.raises(CacheError):
        await h.service.send(body())
    h.sender.send_message.assert_not_awaited()


async def test_lost_delivery_acknowledgment_is_unknown_and_not_retried(manual):
    h = manual
    h.sender.send_message.side_effect = RuntimeError("secret")
    request = body()
    assert (await h.service.send(request))["status"] == "unknown"
    assert (await h.service.send(request))["status"] == "unknown"
    h.sender.send_message.assert_awaited_once()


@pytest.mark.parametrize("change", [{"confirmed": False}, {"confirmed": None}, {"confirmed": 1},
    {"request_id": "bad"}, {"symbol": "BTC/USDT"}, {"interval": "1m"}, {"chat_id": "attacker"}])
async def test_invalid_unconfirmed_or_destination_override_is_rejected(manual, change):
    h = manual
    payload = {**body().model_dump(mode="json"), **change}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app), base_url="http://test") as api:
        assert (await api.post("/ai/telegram-test", json=payload,
                              headers={"X-Telegram-Test-Key": TEST_KEY})).status_code == 422
    h.sender.send_message.assert_not_awaited()


def test_test_key_requires_explicit_nontrivial_configuration():
    assert Settings(_env_file=None, telegram_test_key="").telegram_test_key is None
    assert not Settings(_env_file=None).telegram_test_enabled
    with pytest.raises(ValueError):
        Settings(_env_file=None, telegram_test_key="short")


async def test_cooldown_releases_and_status_never_exposes_secrets(manual):
    h = manual
    await h.service.send(body())
    assert 0 < await h.redis.ttl("telegram:manual-test:cooldown") <= 60
    await h.redis.delete("telegram:manual-test:cooldown")  # simulate the cooldown expiring
    assert (await h.service.send(body()))["status"] == "accepted"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app), base_url="http://test") as api:
        response = await api.get("/ai/status")
        assert response.json()["telegram_test_available"] is True
        assert TEST_KEY not in response.text
        h.assistant.available = False
        assert not (await api.get("/ai/status")).json()["telegram_test_available"]


async def test_rule_trigger_requires_auth_confirmation_and_enabled_watcher(manual):
    h = manual
    watcher = SimpleNamespace(trigger_all=AsyncMock(return_value={"accepted": 2}))
    h.app.state.telegram_watcher = watcher
    request = {"request_id": str(uuid4()), "confirmed": True}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app), base_url="http://test") as api:
        assert (await api.post("/telegram/trigger", json=request)).status_code == 403
        headers = {"X-Telegram-Test-Key": TEST_KEY}
        assert (await api.post("/telegram/trigger", json={**request, "confirmed": False}, headers=headers)).status_code == 422
        h.app.state.telegram_watcher = None
        assert (await api.post("/telegram/trigger", json=request, headers=headers)).status_code == 503
        watcher.trigger_all.assert_not_awaited()
        h.app.state.telegram_watcher = watcher
        response = await api.post("/telegram/trigger", json=request, headers=headers)
        assert response.json() == {"status": "complete", "stats": {"accepted": 2}, "replayed": False}
        repeated = await api.post("/telegram/trigger", json=request, headers=headers)
        assert repeated.json()["replayed"] is True
        watcher.trigger_all.assert_awaited_once()
        limited = await api.post("/telegram/trigger", json={**request, "request_id": str(uuid4())}, headers=headers)
        assert limited.status_code == 429


async def test_partially_interrupted_batch_remains_pending_and_cannot_resend(manual):
    h = manual
    watcher = SimpleNamespace(trigger_all=AsyncMock(side_effect=CacheError("partial delivery")))
    request = ConfirmedTelegramRequest(request_id=uuid4(), confirmed=True)
    with pytest.raises(CacheError):
        await h.service.trigger_rules(request, watcher)
    assert (await h.service.trigger_rules(request, watcher))["status"] == "pending"
    watcher.trigger_all.assert_awaited_once()


async def test_manual_ai_and_rule_trigger_share_cooldown(manual):
    h = manual
    await h.service.send(body())
    watcher = SimpleNamespace(trigger_all=AsyncMock())
    request = ConfirmedTelegramRequest(request_id=uuid4(), confirmed=True)
    assert (await h.service.trigger_rules(request, watcher))["status"] == "rate_limited"
    watcher.trigger_all.assert_not_awaited()
