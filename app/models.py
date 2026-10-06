from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, field_validator

Interval = Literal["1h", "1d", "1w"]


class Candle(BaseModel):
    open_time: int
    close: str
    close_time: int

    @field_validator("close")
    @classmethod
    def validate_price(cls, value: str) -> str:
        try:
            price = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Invalid close price") from exc
        if not price.is_finite() or price < 0:
            raise ValueError("Invalid close price")
        return value


class KlinesResult(BaseModel):
    market: Literal["spot", "futures"]
    symbol: str
    interval: Interval
    source: Literal["binance", "cache", "stale"]
    stale: bool = False
    fetched_at: datetime
    cache_key: str
    warning: str | None = None
    candles: list[Candle]


class SymbolsResult(BaseModel):
    market: Literal["spot", "futures"]
    source: Literal["binance", "cache", "stale"]
    stale: bool = False
    fetched_at: datetime
    warning: str | None = None
    symbols: list[str]
