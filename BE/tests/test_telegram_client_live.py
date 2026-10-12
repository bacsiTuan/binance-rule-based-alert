"""Sends a real Telegram message. Skipped unless the credentials are set in .env."""

import httpx
import pytest

from app.config import Settings
from app.errors import TelegramError
from app.service.telegram_client import TelegramClient

settings = Settings()

pytestmark = pytest.mark.skipif(
    not (settings.telegram_bot_token and settings.telegram_chat_id),
    reason="TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not set in .env",
)


async def test_send_real_message():
    async with httpx.AsyncClient(timeout=10) as http:
        await TelegramClient(settings, http).send_message("Tập hài lòng với những thứ mình đang có. Học từ bỏ những thứ trời không cho")


async def test_wrong_chat_id_is_rejected():
    bad = settings.model_copy(update={"telegram_chat_id": "0"})
    async with httpx.AsyncClient(timeout=10) as http:
        with pytest.raises(TelegramError, match="Telegram HTTP 400"):
            await TelegramClient(bad, http).send_message("should not be delivered")
