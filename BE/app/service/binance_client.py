import asyncio
import math
import time
from decimal import InvalidOperation
from itertools import pairwise

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.errors import BinanceError
from app.models import Candle, Interval


class BinanceClient:
    """Public REST only. Never submits trades or requires credentials."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self.settings = settings
        self.http = http
        self.prefix = "/api/v3" if settings.binance_market == "spot" else "/fapi/v1"
        self.blocked_until = 0.0
        self.blocked_status = 429

    async def _get(self, endpoint: str, params: dict | None = None):
        remaining = self.blocked_until - time.monotonic()
        if remaining > 0:
            raise BinanceError(
                "Binance rate-limit cooldown is active",
                status_code=self.blocked_status,
                retryable=True,
                retry_after=math.ceil(remaining),
            )
        for attempt in range(self.settings.binance_max_attempts):
            try:
                response = await self.http.get(
                    f"{self.settings.base_url}{self.prefix}/{endpoint}", params=params
                )
            except httpx.TransportError as exc:
                if attempt + 1 < self.settings.binance_max_attempts:
                    await asyncio.sleep(0.5 * 2**attempt)
                    continue
                raise BinanceError(
                    "Cannot reach Binance (network error or timeout)", retryable=True
                ) from exc

            if response.status_code in (418, 429):
                try:
                    retry_after = max(
                        1, math.ceil(float(response.headers.get("Retry-After", "60")))
                    )
                except (ValueError, OverflowError):
                    retry_after = 60
                self.blocked_status = response.status_code
                self.blocked_until = time.monotonic() + retry_after
                raise BinanceError(
                    f"Binance returned HTTP {response.status_code}; retry later",
                    status_code=response.status_code,
                    retryable=True,
                    retry_after=retry_after,
                )
            if response.status_code >= 500:
                if attempt + 1 < self.settings.binance_max_attempts:
                    await asyncio.sleep(0.5 * 2**attempt)
                    continue
                raise BinanceError("Binance service is unavailable", retryable=True)
            if response.is_error:
                try:
                    message = response.json().get("msg", "Request rejected")
                except (ValueError, AttributeError):
                    message = "Request rejected"
                status = 400 if response.status_code == 400 else 502
                raise BinanceError(
                    f"Binance HTTP {response.status_code}: {message}", status_code=status
                )
            try:
                return response.json()
            except ValueError as exc:
                raise BinanceError("Binance returned invalid JSON", retryable=True) from exc

    async def klines(
        self, symbol: str, interval: Interval, limit: int, *, end_time: int | None = None
    ) -> list[Candle]:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if end_time is not None:
            params["endTime"] = end_time
        payload = await self._get("klines", params)
        try:
            if not isinstance(payload, list):
                raise TypeError("Expected a candle list")
            candles = [Candle(open_time=row[0], close=row[4], close_time=row[6]) for row in payload]
            if any(c.close_time < c.open_time for c in candles):
                raise ValueError("Invalid candle timestamps")
            if any(a.open_time >= b.open_time for a, b in pairwise(candles)):
                raise ValueError("Candles must be ordered and unique")
            return candles
        except (
            TypeError,
            IndexError,
            KeyError,
            ValueError,
            InvalidOperation,
            ValidationError,
        ) as exc:
            raise BinanceError("Binance returned malformed candles", retryable=True) from exc

    async def symbols(self) -> list[str]:
        payload = await self._get("exchangeInfo")
        try:
            return sorted(
                {
                    item["symbol"]
                    for item in payload["symbols"]
                    if item["quoteAsset"] == "USDT" and item["status"] == "TRADING"
                }
            )
        except (KeyError, TypeError) as exc:
            raise BinanceError(
                "Binance returned malformed exchange information", retryable=True
            ) from exc
