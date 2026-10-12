import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.binance.client import BinanceClient
from app.cache.redis_cache import RedisCache
from app.config import Settings, get_settings
from app.errors import BinanceError, CacheError
from app.models import Interval, KlinesResult, Rule, RuleCreate, RuleUpdate, SymbolsResult
from app.rules import RuleStorage
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
                app.state.rule_storage = RuleStorage(redis)
                try:
                    await app.state.rule_storage.init_seeds()
                except Exception as exc:
                    logging.warning("Could not initialize rule storage seeds: %s", exc)
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

    @app.get("/symbols", response_model=SymbolsResult)
    async def symbols(request: Request):
        return await request.app.state.service.symbols()

    @app.get("/rules", response_model=list[Rule])
    async def get_rules(request: Request):
        return await request.app.state.rule_storage.list_rules()

    @app.post("/rules", response_model=Rule, status_code=status.HTTP_201_CREATED)
    async def create_rule(request: Request, payload: RuleCreate):
        return await request.app.state.rule_storage.create_rule(payload)

    @app.patch("/rules/{rule_id}", response_model=Rule)
    async def update_rule(request: Request, rule_id: int, patch: RuleUpdate):
        updated = await request.app.state.rule_storage.update_rule(rule_id, patch)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Rule #{rule_id} not found")
        return updated

    @app.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_rule(request: Request, rule_id: int):
        deleted = await request.app.state.rule_storage.delete_rule(rule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Rule #{rule_id} not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()
