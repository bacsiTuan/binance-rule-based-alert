import logging

import httpx

from app.config import Settings
from app.service.telegram_client import TelegramClient


async def test_low_level_logs_and_exception_do_not_leak(caplog):
    token, chat = "sentinel-secret-123", "sentinel-chat-456"
    caplog.set_level(logging.DEBUG)
    def handler(request):
        try:
            raise ValueError(f"request token={token}, chat={chat}")
        except ValueError:
            logging.getLogger("httpcore.http11").exception("receive_response_headers.failed")
        logging.getLogger("httpx").debug("payload %s", {"description": token, "chat_id": chat})
        raise httpx.ReadTimeout(f"private {token}", request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = TelegramClient(Settings(
            _env_file=None, telegram_bot_token=token, telegram_chat_id=chat,
        ), http)
        result = await client.send_message("hello")
    assert result.status == "unknown"
    assert token not in caplog.text
    assert chat not in caplog.text
    assert token not in repr(result)
    logging.getLogger("httpx").info("Binance request completed")
    assert "Binance request completed" in caplog.text
