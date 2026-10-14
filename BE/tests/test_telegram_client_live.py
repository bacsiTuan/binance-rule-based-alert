"""Manual live test: explicit opt-in and credentials are both required."""
# pytest tests/test_telegram_client_live.py -v
import os

import httpx
import pytest

from app.config import Settings
from app.service.telegram_client import TelegramClient

if os.environ.get("RUN_TELEGRAM_LIVE_TESTS") != "1":
    pytest.skip("Telegram live tests require explicit opt-in", allow_module_level=True)

settings = Settings()

pytestmark = pytest.mark.skipif(
    not (settings.telegram_bot_token and settings.telegram_chat_id),
    reason="TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not set in .env",
)


async def test_send_real_message():
    async with httpx.AsyncClient(timeout=10) as http:
        result = await TelegramClient(settings, http).send_message(
            "[KIỂM THỬ] Kiểm tra kết nối Telegram; không phải cảnh báo từ rule."
        )
        assert result.status == "accepted", "Telegram did not acknowledge the test message"
        assert type(result.message_id) is int and result.message_id >= 0, "Invalid acknowledgment ID"


async def test_wrong_chat_id_is_rejected():
    bad = settings.model_copy(update={"telegram_chat_id": "0"})
    async with httpx.AsyncClient(timeout=10) as http:
        result = await TelegramClient(bad, http).send_message("should not be delivered")
        assert result.status == "failed"
