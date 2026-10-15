"""Opt-in manual Telegram actions with shared rate limits and durable request IDs."""

import json
import logging
from datetime import UTC, datetime
from secrets import compare_digest

from redis.exceptions import RedisError

from app.assistant_models import ChatRequest
from app.errors import CacheError
from app.service.telegram_format import market_message


class TelegramTest:
    def __init__(self, settings, assistant, sender, redis):
        self.settings = settings
        self.assistant = assistant
        self.sender = sender
        self.redis = redis

    @property
    def delivery_enabled(self):
        return bool(self.settings.telegram_test_enabled and self.settings.telegram_test_key
                    and self.sender)

    @property
    def available(self):
        return self.delivery_enabled and self.assistant.available

    def authorized(self, key):
        expected = self.settings.telegram_test_key
        return bool(expected and compare_digest(
            (key or "").encode(), expected.get_secret_value().encode()))

    async def _reserve(self, key, scope):
        # Redis survives reloads/restarts. A pending delivery is never automatically retried.
        pending = {"status": "pending", "scope": scope}
        try:
            reserved = await self.redis.set(key, json.dumps(pending), nx=True, ex=86400)
            if not reserved:
                existing = json.loads(await self.redis.get(key) or "{}")
                if existing.get("scope") != scope:
                    return {"status": "conflict"}
                return {**{k: v for k, v in existing.items() if k != "scope"}, "replayed": True}
            if not await self.redis.set("telegram:manual-test:cooldown", "1", nx=True, ex=60):
                await self.redis.set(key, json.dumps({**pending, "status": "rate_limited"}), ex=86400)
                return {"status": "rate_limited"}
        except RedisError as exc:
            raise CacheError("Manual test storage is unavailable") from exc
        return None

    async def trigger_rules(self, body, watcher):
        key = f"telegram:manual-rules:{body.request_id}"
        scope = ["all_rules"]
        previous = await self._reserve(key, scope)
        if previous:
            return previous
        # If interrupted after partial delivery, the pending reservation prevents a replay.
        stats = await watcher.trigger_all()
        result = {"status": "complete", "stats": stats}
        await self._finish(key, scope, result)
        return {**result, "replayed": False}

    async def send(self, body):
        key = f"telegram:manual-test:{body.request_id}"
        scope = [body.symbol, body.interval, body.language]
        previous = await self._reserve(key, scope)
        if previous:
            return previous

        try:
            result = await self.assistant.chat(ChatRequest(
                symbol=body.symbol, interval=body.interval, language=body.language,
                message=("Prepare a market outlook for the selected pair using closed-candle indicators in at most "
                         "130 words: observation, conditional scenarios/confirmation, and risk. "
                         "This is a market analysis request, not a triggered trading rule. "
                         "Do not invent a rule trigger, "
                         "and do not repeat timestamps: the message header provides the times."),
            ))
        except Exception:
            await self._finish(key, scope, "generation_failed")
            raise

        context = {**result["context"], "symbol": body.symbol, "interval": body.interval}
        text, bold = market_message(context, result["answer"], language=body.language,
                                    zone=self.settings.telegram_timezone, sent_at=datetime.now(UTC))
        try:
            delivery = await self.sender.send_message(text, bold_chars=bold)
            status = delivery.status
        except Exception:  # noqa: BLE001 - any post-send failure leaves delivery uncertain
            # The server may have accepted the message before a connection/process error.
            logging.getLogger(__name__).warning("telegram_manual_test_unknown")
            status = "unknown"
        await self._finish(key, scope, status)
        return {"status": status, "replayed": False}

    async def _finish(self, key, scope, status):
        try:
            result = status if isinstance(status, dict) else {"status": status}
            await self.redis.set(key, json.dumps({"scope": scope, **result}), ex=86400)
        except RedisError as exc:
            # Reservation remains pending; a lost acknowledgment must not cause a resend.
            raise CacheError("Manual test outcome could not be saved; check Telegram") from exc
