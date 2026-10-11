import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.binance.client import BinanceClient
from app.cache.redis_cache import RedisCache
from app.config import Settings, get_settings
from app.errors import BinanceError, CacheError
from app.indicator_models import IndicatorRequest, IndicatorsResult
from app.indicators import IndicatorDataError, calculate_indicators, utc_milliseconds
from app.models import Interval, KlinesResult, SymbolsResult
from app.service import MarketDataService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
        redis = Redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3
        )
        try:
            async with httpx.AsyncClient(timeout=settings.binance_timeout_seconds) as http:
                cache = RedisCache(redis)
                app.state.service = MarketDataService(
                    settings, BinanceClient(settings, http), cache
                )
                yield
        finally:
            await redis.aclose()

    app = FastAPI(title="Binance Market Data v1", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(BinanceError)
    async def binance_error(request: Request, exc: BinanceError):
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content={"detail": str(exc), "retry_after": exc.retry_after},
        )

    @app.exception_handler(CacheError)
    async def cache_error(request: Request, exc: CacheError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.get("/health")
    async def health(request: Request):
        await request.app.state.service.cache.ping()
        return {"status": "ok", "redis": "ok", "market": settings.binance_market}

    @app.get("/klines", response_model=KlinesResult)
    async def klines(
        request: Request,
        symbol: str = Query(default="BTCUSDT", pattern=r"^[a-zA-Z0-9]{2,30}$"),
        interval: Interval = "1h",
        limit: int = Query(default=300, ge=1, le=1000),
    ):
        return await request.app.state.service.klines(symbol, interval, limit)

    @app.post("/indicators", response_model=IndicatorsResult)
    async def indicators(body: IndicatorRequest, request: Request):
        snapshot = await request.app.state.service.klines(body.symbol, body.interval, body.limit)
        evaluated_at = utc_milliseconds(datetime.now(UTC))
        try:
            return calculate_indicators(snapshot, body, evaluated_at, settings.binance_market)
        except IndicatorDataError as exc:
            return JSONResponse(
                status_code=502,
                content={"detail": {"code": "invalid_indicator_data", "message": str(exc)}},
            )

    @app.get("/symbols", response_model=SymbolsResult)
    async def symbols(request: Request):
        return await request.app.state.service.symbols()

    return app


app = create_app()
