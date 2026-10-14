import httpx
import pytest

from app.config import Settings
from app.service.telegram_client import TelegramClient


@pytest.mark.parametrize("status,payload,expected,delay", [
    (200, {"ok": True, "result": {"message_id": 1}}, "accepted", 0),
    (200, {"ok": True, "result": {"message_id": True}}, "unknown", 0),
    (200, {"ok": True, "result": {"message_id": -1}}, "unknown", 0),
    (200, {"ok": False}, "failed", 0),
    (400, {"ok": False, "description": "secret"}, "failed", 0),
    (500, {"ok": False}, "unknown", 0),
    (302, {"ok": False}, "unknown", 0),
    (429, {"ok": False, "parameters": {"retry_after": 7}}, "failed", 7),
    (429, {"parameters": {"retry_after": True}}, "failed", 0),
    (429, {"parameters": {"retry_after": 10 ** 400}}, "failed", 0),
    (200, [], "unknown", 0),
    (200, {"ok": True, "result": None}, "unknown", 0),
])
async def test_response_contract(status, payload, expected, delay):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.extensions["timeout"]["read"] == 3
        return httpx.Response(status, json=payload, headers={"Location": "https://invalid.test"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await TelegramClient(Settings(
            _env_file=None, telegram_bot_token="fake", telegram_chat_id="1",
            telegram_timeout_seconds=3,
        ), http).send_message("text")
    assert (result.status, result.retry_after) == (expected, delay)
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["json", "timeout", "connect"])
async def test_unconfirmed_errors_once(failure):
    calls = []
    def handler(request):
        calls.append(request)
        if failure == "json":
            return httpx.Response(200, text="not json")
        error = httpx.ReadTimeout if failure == "timeout" else httpx.ConnectError
        raise error("fake secret URL", request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await TelegramClient(Settings(
            _env_file=None, telegram_bot_token="fake", telegram_chat_id="1",
        ), http).send_message("text")
    assert result.status == "unknown"
    assert len(calls) == 1
