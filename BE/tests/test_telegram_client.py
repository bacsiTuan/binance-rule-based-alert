import json

import httpx
import pytest

from app.config import Settings
from app.errors import TelegramError
from app.service.telegram_client import TelegramClient

TOKEN = "123:secret-token"
CHAT_ID = "-1001"


@pytest.fixture
async def make_client():
    clients = []

    def make(handler, **overrides):
        settings = Settings(
            _env_file=None,
            **{"telegram_bot_token": TOKEN, "telegram_chat_id": CHAT_ID, **overrides},
        )
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        clients.append(http)
        return TelegramClient(settings, http)

    yield make
    for http in clients:
        await http.aclose()


async def test_send_message_posts_to_bot_api(make_client):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": {}})

    await make_client(handler).send_message("BTCUSDT RSI < 30")

    assert len(seen) == 1
    assert seen[0].method == "POST"
    assert str(seen[0].url) == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert json.loads(seen[0].content) == {"chat_id": CHAT_ID, "text": "BTCUSDT RSI < 30"}


async def test_api_error_raises_without_leaking_token(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "Bad Request: chat not found"})

    with pytest.raises(TelegramError) as exc_info:
        await make_client(handler).send_message("hi")

    assert "400" in str(exc_info.value)
    assert "chat not found" in str(exc_info.value)
    assert TOKEN not in str(exc_info.value)


async def test_non_json_error_body(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    with pytest.raises(TelegramError, match="Telegram HTTP 502: Request rejected"):
        await make_client(handler).send_message("hi")


async def test_network_error_raises_telegram_error(make_client):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(TelegramError, match="Cannot reach Telegram") as exc_info:
        await make_client(handler).send_message("hi")

    assert TOKEN not in str(exc_info.value)


@pytest.mark.parametrize("overrides", [{"telegram_bot_token": None}, {"telegram_chat_id": None}])
async def test_missing_credentials_rejected(make_client, overrides):
    with pytest.raises(TelegramError, match="must be set"):
        make_client(lambda request: httpx.Response(200), **overrides)
