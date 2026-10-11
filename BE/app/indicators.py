import itertools
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal, DecimalException, localcontext

from app.indicator_models import (
    IndicatorPoint,
    IndicatorRequest,
    IndicatorSeries,
    IndicatorsResult,
)
from app.models import KlinesResult


class IndicatorDataError(ValueError):
    pass


def utc_milliseconds(value: datetime) -> int:
    if value.utcoffset() is None:
        raise IndicatorDataError("Snapshot time must have a timezone")
    delta = value.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000


def _values(prices: list[Decimal], name: str, period: int) -> list[Decimal | None]:
    values: list[Decimal | None] = [None] * len(prices)
    required = period + (name == "rsi")
    if len(prices) < required:
        return values
    if name == "sma":
        total = sum(prices[:period], Decimal(0))
        values[period - 1] = total / period
        for i in range(period, len(prices)):
            total += prices[i] - prices[i - period]
            values[i] = total / period
    elif name == "ema":
        previous = sum(prices[:period], Decimal(0)) / period
        values[period - 1] = previous
        alpha = Decimal(2) / (period + 1)
        for i in range(period, len(prices)):
            previous = alpha * prices[i] + (1 - alpha) * previous
            values[i] = previous
    else:
        deltas = [b - a for a, b in itertools.pairwise(prices)]
        gain = sum((max(d, Decimal(0)) for d in deltas[:period]), Decimal(0)) / period
        loss = sum((max(-d, Decimal(0)) for d in deltas[:period]), Decimal(0)) / period
        for i in range(period, len(prices)):
            if i > period:
                gain = (gain * (period - 1) + max(deltas[i - 1], Decimal(0))) / period
                loss = (loss * (period - 1) + max(-deltas[i - 1], Decimal(0))) / period
            values[i] = (
                Decimal(50)
                if gain == loss == 0
                else Decimal(100)
                if loss == 0
                else Decimal(0)
                if gain == 0
                else 100 - 100 / (1 + gain / loss)
            )
    return values


def _validate_snapshot(snapshot: KlinesResult, request: IndicatorRequest, market: str):
    if (snapshot.market, snapshot.symbol, snapshot.interval) != (
        market,
        request.symbol,
        request.interval,
    ):
        raise IndicatorDataError("Snapshot identity does not match the request")
    utc_milliseconds(snapshot.fetched_at)
    previous = None
    for candle in snapshot.candles:
        if type(candle.open_time) is not int or type(candle.close_time) is not int:
            raise IndicatorDataError("Candle timestamps must be integers")
        if candle.open_time > candle.close_time:
            raise IndicatorDataError("Candle open time exceeds close time")
        if previous and (
            candle.open_time <= previous.open_time or candle.close_time <= previous.close_time
        ):
            raise IndicatorDataError("Candles must be ordered and unique")
        if not isinstance(candle.close, str):
            raise IndicatorDataError("Close prices must be decimal strings")
        price = Decimal(candle.close)
        if not price.is_finite() or price < 0:
            raise IndicatorDataError("Close prices must be finite and nonnegative")
        previous = candle


def calculate_indicators(
    snapshot: KlinesResult, request: IndicatorRequest, evaluated_at: int, market: str
) -> IndicatorsResult:
    try:
        _validate_snapshot(snapshot, request, market)
        return _calculate(snapshot, request, evaluated_at)
    except DecimalException as exc:
        raise IndicatorDataError("Cannot calculate finite indicator values") from exc


def _calculate(
    snapshot: KlinesResult, request: IndicatorRequest, evaluated_at: int
) -> IndicatorsResult:
    cutoff = min(evaluated_at, utc_milliseconds(snapshot.fetched_at))
    candles = [c for c in snapshot.candles if request.include_open or c.close_time < cutoff]
    # Prefix counts preserve dependency flags without scanning each rolling window.
    provisional_counts = [0]
    for candle in candles:
        provisional_counts.append(provisional_counts[-1] + (candle.close_time >= cutoff))
    prices = [Decimal(c.close) for c in candles]
    nonzero = [p for p in prices if p]
    precision = (
        max(
            50,
            max(p.adjusted() for p in nonzero) - min(p.as_tuple().exponent for p in nonzero) + 33,
        )
        if nonzero
        else 50
    )
    results = []
    with localcontext() as context:
        context.prec = precision
        context.rounding = ROUND_HALF_EVEN
        for selection in request.indicators:
            values = _values(prices, selection.name, selection.period)
            points = [
                IndicatorPoint(
                    open_time=c.open_time,
                    close_time=c.close_time,
                    value=None if v is None else "0" if v == 0 else format(v, "f"),
                    status="insufficient_data" if v is None else "ok",
                    provisional=provisional_counts[i + 1]
                    > provisional_counts[
                        max(0, i + 1 - selection.period) if selection.name == "sma" else 0
                    ],
                )
                for i, (c, v) in enumerate(zip(candles, values, strict=True))
            ]
            latest = (
                points[-1]
                if points
                else IndicatorPoint(
                    open_time=None,
                    close_time=None,
                    value=None,
                    status="insufficient_data",
                    provisional=False,
                )
            )
            results.append(
                IndicatorSeries(
                    name=selection.name,
                    period=selection.period,
                    required_candles=selection.period + (selection.name == "rsi"),
                    available_candles=len(candles),
                    points=points,
                    latest=latest,
                )
            )
    return IndicatorsResult(
        market=snapshot.market,
        symbol=snapshot.symbol,
        interval=snapshot.interval,
        source=snapshot.source,
        stale=snapshot.stale,
        fetched_at=snapshot.fetched_at,
        cache_key=snapshot.cache_key,
        warning=snapshot.warning,
        evaluated_at=evaluated_at,
        include_open=request.include_open,
        input_candles=len(snapshot.candles),
        eligible_candles=len(candles),
        excluded_candles=len(snapshot.candles) - len(candles),
        series_start_time=candles[0].open_time if candles else None,
        results=results,
    )
