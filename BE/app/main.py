import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.cache.redis_cache import RedisCache
from app.config import Settings, get_settings
from app.errors import BinanceError, CacheError
from app.indicator_models import IndicatorRequest, IndicatorsResult
from app.indicators import IndicatorDataError, calculate_indicators, utc_milliseconds
from app.models import Interval, KlinesResult, Rule, RuleCreate, RuleUpdate, SymbolsResult
from app.rules import RuleStorage
from app.service import MarketDataService
from app.service.binance_client import BinanceClient
from app.service.telegram_client import TelegramClient
from app.service.telegram_scheduler import TelegramScheduler


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
                rules_storage = RuleStorage(redis)
                await rules_storage.init_seeds()
                app.state.rules = rules_storage
                async with httpx.AsyncClient(
                    timeout=settings.telegram_timeout_seconds, follow_redirects=False
                ) as telegram_http:
                    watcher = None
                    if (settings.telegram_enabled and settings.telegram_bot_token
                            and settings.telegram_chat_id):
                        watcher = TelegramScheduler(
                            app.state.service, rules_storage,
                            TelegramClient(settings, telegram_http),
                        )
                        try:
                            await watcher.start()
                        except (CacheError, ValueError, RuntimeError):
                            logging.getLogger(__name__).warning("telegram_start_failed")
                            await watcher.stop()
                            watcher = None
                    elif settings.telegram_enabled:
                        logging.getLogger(__name__).warning("telegram_disabled_missing_config")
                    app.state.telegram_watcher = watcher
                    try:
                        yield
                    finally:
                        if watcher is not None:
                            await watcher.stop()
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

    @app.get("/rules", response_model=list[Rule])
    async def list_rules(request: Request):
        return await request.app.state.rules.list_rules()

    @app.post("/rules", response_model=Rule, status_code=201)
    async def create_rule(body: RuleCreate, request: Request):
        return await request.app.state.rules.create_rule(body)

    @app.patch("/rules/{rule_id}", response_model=Rule)
    async def update_rule(rule_id: int, body: RuleUpdate, request: Request):
        rule = await request.app.state.rules.update_rule(rule_id, body)
        if not rule:
            return JSONResponse(status_code=404, content={"detail": "Rule not found"})
        return rule

    @app.delete("/rules/{rule_id}", status_code=204)
    async def delete_rule(rule_id: int, request: Request):
        deleted = await request.app.state.rules.delete_rule(rule_id)
        if not deleted:
            return JSONResponse(status_code=404, content={"detail": "Rule not found"})
        return None

    return app


app = create_app()
