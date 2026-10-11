from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, localcontext
from fractions import Fraction

import pytest

from app.indicator_models import IndicatorRequest
from app.indicators import calculate_indicators
from app.models import Candle, KlinesResult


def snapshot(prices, **updates):
    data = {
        "market": "spot",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "source": "binance",
        "fetched_at": datetime(2026, 10, 11, tzinfo=UTC),
        "cache_key": "fixture-key",
        "candles": [
            Candle(open_time=i * 1000, close=str(p), close_time=i * 1000 + 999)
            for i, p in enumerate(prices)
        ],
    }
    data.update(updates)
    return KlinesResult(**data)


def calculate(data, name="sma", period=3, **options):
    now = options.pop("evaluated_at", 1791676800000)
    request = IndicatorRequest(indicators=[{"name": name, "period": period}], **options)
    return calculate_indicators(data, request, now, "spot")


def assert_near(value, expected):
    expected = Fraction(expected)
    assert value is not None
    assert abs(Fraction(value) - expected) <= max(Fraction(1, 10**12), abs(expected) / 10**12)


@pytest.mark.parametrize(
    "name,prices,expected",
    [
        ("sma", [1, 2, 3, 6, 5], [2, Fraction(11, 3), Fraction(14, 3)]),
        ("ema", [1, 2, 3, 6, 5], [2, 4, Fraction(9, 2)]),
        ("rsi", [1, 2, 3, 2, 4, 3], [Fraction(200, 3), Fraction(250, 3), Fraction(2000, 33)]),
        ("rsi", [1, 2, 3, 4, 5], [100, 100]),
        ("rsi", [5, 4, 3, 2, 1], [0, 0]),
        ("rsi", [2, 2, 2, 2, 2], [50, 50]),
    ],
)
def test_reference_values(name, prices, expected):
    data = snapshot(prices)
    before = data.model_dump()
    result = calculate(data, name).results[0]
    warmup = 3 if name == "rsi" else 2
    assert [p.value for p in result.points[:warmup]] == [None] * warmup
    for point, value in zip(result.points[warmup:], expected, strict=True):
        assert_near(point.value, value)
        assert point.status == "ok"
    assert [p.open_time for p in result.points] == [c.open_time for c in data.candles]
    assert result.latest == result.points[-1]
    assert data.model_dump() == before


@pytest.mark.parametrize("name", ["sma", "ema", "rsi"])
@pytest.mark.parametrize("period", [1, 14, 999])
@pytest.mark.parametrize("offset", [-1000, -1, 0, 1])
def test_warmup_and_empty(name, period, offset):
    count = max(0, period + offset)
    result = calculate(snapshot(range(count)), name, period)
    series = result.results[0]
    required = period + (name == "rsi")
    assert series.required_candles == required
    assert series.available_candles == count
    assert len(series.points) == count
    assert sum(p.value is not None for p in series.points) == max(0, count - required + 1)
    assert series.latest.status == ("ok" if count >= required else "insufficient_data")
    if count == 0:
        assert series.latest.open_time is series.latest.close_time is series.latest.value is None
        assert result.series_start_time is None


@pytest.mark.parametrize(
    "change",
    [
        {"close": "NaN"},
        {"close": "Infinity"},
        {"close": "-1"},
        {"close": "bad"},
        {"open_time": 0.5},
        {"open_time": True},
        {"open_time": 0},
        {"close_time": 999},
        {"close_time": 100},
    ],
)
def test_reject_corrupt_snapshot(change):
    data = snapshot([1, 2, 3])
    data.candles[1] = data.candles[1].model_copy(update=change)
    with pytest.raises(ValueError):
        calculate(data)


@pytest.mark.parametrize(
    "change",
    [
        {"market": "futures"},
        {"symbol": "ETHUSDT"},
        {"interval": "1w"},
        {"fetched_at": datetime(2026, 10, 11, tzinfo=None)},  # noqa: DTZ001 - invalid fixture
    ],
)
def test_reject_snapshot_identity_and_naive_time(change):
    with pytest.raises(ValueError):
        calculate(snapshot([1, 2, 3]).model_copy(update=change))


def test_gaps_are_observations_not_synthetic_candles():
    data = snapshot([1, 2, 3, 4])
    data.candles.pop(1)
    assert_near(calculate(data).results[0].latest.value, Fraction(8, 3))


@pytest.mark.parametrize("cutoff,count", [(998, 0), (999, 0), (1000, 1), (2999, 2), (3000, 3)])
@pytest.mark.parametrize("clock", ["evaluation", "fetch"])
def test_closed_cutoff(cutoff, count, clock):
    fetched = cutoff if clock == "fetch" else 10000
    evaluated = cutoff if clock == "evaluation" else 10000
    data = snapshot(
        [1, 2, 3], fetched_at=datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=fetched)
    )
    result = calculate(data, period=1, evaluated_at=evaluated)
    assert result.eligible_candles == count
    assert result.excluded_candles == 3 - count
    assert all(not p.provisional for p in result.results[0].points)


@pytest.mark.parametrize("name", ["sma", "ema", "rsi"])
@pytest.mark.parametrize("stale", [False, True])
def test_open_snapshot_does_not_become_final_with_time(name, stale):
    data = snapshot(
        [1, 2, 3, 4],
        fetched_at=datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=2999),
        stale=stale,
        source="stale" if stale else "cache",
        warning="upstream" if stale else None,
    )
    before = data.model_dump()
    closed = calculate(data, name, 3, evaluated_at=10000)
    opened = calculate(data, name, 3, evaluated_at=10000, include_open=True)
    assert closed.eligible_candles == 2
    assert closed.results[0].latest.value is None
    assert opened.eligible_candles == 4
    assert [p.provisional for p in opened.results[0].points] == [False, False, True, True]
    assert opened.results[0].latest.status == "ok"
    assert (opened.stale, opened.warning, opened.fetched_at) == (
        stale,
        data.warning,
        data.fetched_at,
    )
    assert data.model_dump() == before


def test_fetch_completion_metadata_is_not_exchange_finality_proof():
    # The exchange may have sampled before close; only completion metadata is available.
    data = snapshot([1], fetched_at=datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=1001))
    result = calculate(data, period=1, evaluated_at=1002)
    assert result.eligible_candles == 1
    assert not result.results[0].latest.provisional


def weighted_average(seed, subsequent, weight):
    # Closed-form weights provide an oracle independent of the production recurrence.
    return seed * weight ** len(subsequent) + sum(
        (1 - weight) * value * weight ** (len(subsequent) - i - 1)
        for i, value in enumerate(subsequent)
    )


@pytest.mark.parametrize("scale", ["small", "large"])
def test_long_series_precision_against_fraction_oracle(scale):
    prices = [
        ("0.000000000000000000" if scale == "small" else "123456789012345678901234567890.")
        + f"{(i * 17) % 97:03d}"
        for i in range(1000)
    ]
    exact = [Fraction(p) for p in prices]
    data = snapshot(prices)
    period = 14
    for name in ("sma", "ema", "rsi"):
        actual = calculate(data, name, period).results[0].points
        for i in (14, 15, 99, 499, 999):
            if name == "sma":
                expected = sum(exact[i - period + 1 : i + 1]) / period
            elif name == "ema":
                expected = weighted_average(
                    sum(exact[:period]) / period, exact[period : i + 1], Fraction(13, 15)
                )
            else:
                changes = [exact[j] - exact[j - 1] for j in range(1, i + 1)]
                gains, losses = [max(d, 0) for d in changes], [max(-d, 0) for d in changes]
                gain = weighted_average(
                    sum(gains[:period]) / period, gains[period:], Fraction(13, 14)
                )
                loss = weighted_average(
                    sum(losses[:period]) / period, losses[period:], Fraction(13, 14)
                )
                expected = 100 * gain / (gain + loss)
                assert 0 <= Fraction(actual[i].value) <= 100
            assert_near(actual[i].value, expected)


def test_repeatability_context_isolation_and_fresh_seed():
    data = snapshot(["1.1234567890123456789", "2", "3", "2", "4"])
    before = data.model_dump()
    expected = calculate(data, "ema").model_dump()
    with localcontext() as ctx:
        ctx.prec = 6
        ctx.rounding = ROUND_DOWN
        for _ in range(100):
            assert calculate(data, "ema").model_dump() == expected
        assert ctx.prec == 6 and ctx.rounding == ROUND_DOWN
    assert data.model_dump() == before
    shortened = snapshot(["2", "3", "2", "4"])
    assert (
        calculate(shortened, "ema").results[0].latest.value
        != expected["results"][0]["latest"]["value"]
    )


def test_milliseconds_do_not_round_through_float():
    from app.indicators import utc_milliseconds

    value = datetime(2026, 10, 11, 0, 0, 0, 999999, tzinfo=UTC)
    assert utc_milliseconds(value) == 1791676800999
