import httpx

from app.config import Settings
from app.errors import TelegramError


class TelegramClient:
    """Sends messages through the Telegram Bot API."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            raise TelegramError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        self.http = http
        self.chat_id = settings.telegram_chat_id
        # The token is part of the URL, so never include the URL in error messages.
        self._url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

    async def send_message(self, text: str) -> None:
        try:
            response = await self.http.post(self._url, json={"chat_id": self.chat_id, "text": text})
        except httpx.TransportError as exc:
            raise TelegramError("Cannot reach Telegram (network error or timeout)") from exc

        if response.is_error:
            try:
                description = response.json().get("description", "Request rejected")
            except (ValueError, AttributeError):
                description = "Request rejected"
            raise TelegramError(f"Telegram HTTP {response.status_code}: {description}")
