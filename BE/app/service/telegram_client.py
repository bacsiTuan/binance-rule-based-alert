import logging
import math
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal

import httpx

from app.config import Settings
from app.errors import TelegramError

_telegram_http_active = ContextVar("telegram_http_active", default=False)


@dataclass(frozen=True)
class DeliveryResult:
    status: Literal["accepted", "failed", "unknown"]
    message_id: int | None = None
    error_code: str | None = None
    retry_after: int = 0


class TelegramLogFilter(logging.Filter):
    def filter(self, record):
        # HTTP debug records can include both the URL and arbitrary response payloads.
        text = record.getMessage()
        if _telegram_http_active.get() or "api.telegram.org" in text or "/bot" in text:
            record.msg = "Telegram HTTP details suppressed"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
        return True


class TelegramClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            raise TelegramError("Telegram configuration is missing")
        self.http = http
        self.chat_id = settings.telegram_chat_id
        token = settings.telegram_bot_token.get_secret_value()
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        # Applies also to clients constructed directly outside FastAPI lifespan.
        for name in ("httpx", "httpcore.connection", "httpcore.http11",
                     "httpcore.http2", "httpcore.proxy"):
            logger = logging.getLogger(name)
            if not any(isinstance(f, TelegramLogFilter) for f in logger.filters):
                logger.addFilter(TelegramLogFilter())
        self.timeout = settings.telegram_timeout_seconds

    async def send_message(self, text: str, bold_chars: int = 0) -> DeliveryResult:
        payload = {"chat_id": self.chat_id, "text": text}
        if bold_chars > 0:
            # Entities avoid parse_mode escaping; Telegram measures them in UTF-16 units.
            length = len(text[:bold_chars].encode("utf-16-le")) // 2
            payload["entities"] = [{"type": "bold", "offset": 0, "length": length}]
        context_token = _telegram_http_active.set(True)
        try:
            response = await self.http.post(
                self._url, json=payload,
                timeout=self.timeout, follow_redirects=False,
            )
        except httpx.TransportError:
            return DeliveryResult("unknown", error_code="transport_error")
        finally:
            _telegram_http_active.reset(context_token)
        try:
            payload = response.json()
        except ValueError:
            return DeliveryResult("unknown", error_code="invalid_response")
        if not isinstance(payload, dict):
            return DeliveryResult("unknown", error_code="invalid_response")
        if response.is_redirect:
            return DeliveryResult("unknown", error_code="unexpected_redirect")
        if response.status_code >= 500:
            return DeliveryResult("unknown", error_code="service_error")
        if response.status_code == 429:
            delay = payload.get("parameters", {})
            delay = delay.get("retry_after", 0) if isinstance(delay, dict) else 0
            delay = delay if type(delay) is int and delay > 0 else 0
            try:
                if not math.isfinite(float(delay)):
                    delay = 0
            except OverflowError:
                delay = 0
            return DeliveryResult("failed", error_code="rate_limited", retry_after=delay)
        if payload.get("ok") is False:
            return DeliveryResult("failed", error_code="rejected")
        result = payload.get("result")
        message_id = result.get("message_id") if isinstance(result, dict) else None
        if (response.is_success and payload.get("ok") is True
                and type(message_id) is int and message_id >= 0):
            return DeliveryResult("accepted", message_id=message_id)
        return DeliveryResult("unknown", error_code="invalid_acknowledgment")
