from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.models import Interval

IndicatorName = Literal["sma", "ema", "rsi"]
Period = Annotated[int, Field(strict=True, ge=1, le=999)]


class IndicatorSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: IndicatorName
    period: Period = 14


class IndicatorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(default="BTCUSDT", pattern=r"^[a-zA-Z0-9]{2,30}$")
    interval: Interval = "1h"
    limit: int = Field(default=300, strict=True, ge=1, le=1000)
    include_open: StrictBool = False
    indicators: list[IndicatorSelection] = Field(min_length=1, max_length=2997)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def unique_selections(self):
        pairs = [(item.name, item.period) for item in self.indicators]
        if len(set(pairs)) != len(pairs):
            raise ValueError("Duplicate indicator name and period")
        return self


class IndicatorPoint(BaseModel):
    open_time: int | None
    close_time: int | None
    value: str | None
    status: Literal["ok", "insufficient_data"]
    provisional: bool


class IndicatorSeries(BaseModel):
    name: IndicatorName
    period: Period
    required_candles: int
    available_candles: int
    points: list[IndicatorPoint]
    latest: IndicatorPoint

    @model_validator(mode="after")
    def validate_point_times(self):
        if any(p.open_time is None or p.close_time is None for p in self.points):
            raise ValueError("Series points require candle timestamps")
        return self


class IndicatorsResult(BaseModel):
    market: Literal["spot", "futures"]
    symbol: str
    interval: Interval
    source: Literal["binance", "cache", "stale"]
    stale: bool
    fetched_at: datetime
    cache_key: str
    warning: str | None
    evaluated_at: int
    include_open: bool
    input_candles: int
    eligible_candles: int
    excluded_candles: int
    series_start_time: int | None
    results: list[IndicatorSeries]
