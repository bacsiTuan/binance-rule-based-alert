"""Opens real WebSocket connections to Binance and prints the klines received."""

# pytest tests/test_binance_ws_live.py -v -s
import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from app.config import Settings
from app.service.binance_client import BinanceClient

EVENTS = 3  # spot pushes a kline update every ~2s
TIMEOUT_SECONDS = 30


def fmt(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%d %H:%M:%S")


async def receive(market: str, symbol: str, interval: str, count: int):
    async with httpx.AsyncClient() as http:
        client = BinanceClient(Settings(_env_file=None, binance_market=market), http)
        print(f"\nConnecting to {client.ws_url}/{symbol.lower()}@kline_{interval}")
        events = []
        async with asyncio.timeout(TIMEOUT_SECONDS):
            async for candle, is_closed in client.stream_klines(symbol, interval):
                print(
                    f"  {symbol} {interval} open={fmt(candle.open_time)} "
                    f"close_time={fmt(candle.close_time)} close={candle.close} "
                    f"{'CLOSED' if is_closed else 'open'}"
                )
                events.append((candle, is_closed))
                if len(events) == count:
                    break
        return events


async def test_connects_and_receives_first_kline():
    events = await receive("spot", "BTCUSDT", "1h", 1)
    assert len(events) == 1


@pytest.mark.parametrize(
    ("market", "symbol", "interval"),
    [("spot", "BTCUSDT", "1h"), ("spot", "ETHUSDT", "1d"), ("futures", "BTCUSDT", "1h")],
)
async def test_receives_several_klines(market, symbol, interval):
    events = await receive(market, symbol, interval, EVENTS)

    assert len(events) == EVENTS
    for candle, _ in events:
        assert candle.close_time > candle.open_time
        assert float(candle.close) > 0
    open_times = [candle.open_time for candle, _ in events]
    assert open_times == sorted(open_times)
