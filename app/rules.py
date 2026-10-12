import json
import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.errors import CacheError
from app.models import Rule, RuleCreate, RuleUpdate

logger = logging.getLogger(__name__)

DEFAULT_MOCK_RULES = [
    {
        "id": 1,
        "symbol": "BTCUSDT",
        "timeframe": "1d",
        "indicator": {"type": "rsi", "length": 14},
        "operator": "cross_above",
        "target": 30,
        "candle_mode": "closed",
        "enabled": True,
        "created_at": "2026-10-01T08:00:00Z",
    },
    {
        "id": 2,
        "symbol": "ETHUSDT",
        "timeframe": "1d",
        "indicator": {"type": "sma", "length": 50},
        "operator": "cross_above",
        "target": {"type": "sma", "length": 200},
        "candle_mode": "closed",
        "enabled": False,
        "created_at": "2026-10-02T09:30:00Z",
    },
]


class RuleStorage:
    def __init__(
        self,
        redis: Redis,
        key: str = "app:rules",
        counter_key: str = "app:rules:next_id",
    ):
        self.redis = redis
        self.key = key
        self.counter_key = counter_key

    async def init_seeds(self) -> None:
        """Khởi tạo luật mẫu ban đầu nếu Redis chưa từng có dữ liệu luật."""
        try:
            count = await self.redis.hlen(self.key)
            counter = await self.redis.get(self.counter_key)
            if count == 0 and counter is None:
                max_id = 0
                for item in DEFAULT_MOCK_RULES:
                    rule = Rule.model_validate(item)
                    await self.redis.hset(self.key, str(rule.id), rule.model_dump_json())
                    if rule.id > max_id:
                        max_id = rule.id
                await self.redis.set(self.counter_key, str(max_id))
                logger.info("Initialized %d default rules in Redis", len(DEFAULT_MOCK_RULES))
        except RedisError as exc:
            logger.warning("Could not initialize default rules in Redis: %s", exc)

    async def list_rules(self) -> list[Rule]:
        try:
            raw_rules = await self.redis.hgetall(self.key)
        except RedisError as exc:
            raise CacheError("Cannot read rules from Redis") from exc

        rules: list[Rule] = []
        for raw in raw_rules.values():
            try:
                rule_data = json.loads(raw)
                rules.append(Rule.model_validate(rule_data))
            except Exception as exc:
                logger.warning("Skipping invalid rule payload: %s", exc)
                continue
        rules.sort(key=lambda r: r.id)
        return rules

    async def get_rule(self, rule_id: int) -> Rule | None:
        try:
            raw = await self.redis.hget(self.key, str(rule_id))
        except RedisError as exc:
            raise CacheError("Cannot read rule from Redis") from exc

        if not raw:
            return None
        try:
            return Rule.model_validate_json(raw)
        except Exception:
            return None

    async def create_rule(self, payload: RuleCreate) -> Rule:
        try:
            rule_id = await self.redis.incr(self.counter_key)
            now_str = datetime.now(timezone.utc).isoformat()
            rule = Rule(
                id=rule_id,
                symbol=payload.symbol.upper(),
                timeframe=payload.timeframe,
                indicator=payload.indicator,
                operator=payload.operator,
                target=payload.target,
                candle_mode=payload.candle_mode,
                enabled=True,
                created_at=now_str,
            )
            await self.redis.hset(self.key, str(rule_id), rule.model_dump_json())
            return rule
        except RedisError as exc:
            raise CacheError("Cannot save rule to Redis") from exc

    async def update_rule(self, rule_id: int, patch: RuleUpdate) -> Rule | None:
        existing = await self.get_rule(rule_id)
        if not existing:
            return None

        update_dict = patch.model_dump(exclude_unset=True)
        if "symbol" in update_dict and update_dict["symbol"]:
            update_dict["symbol"] = update_dict["symbol"].upper()

        current_dict = existing.model_dump()
        current_dict.update(update_dict)
        updated_rule = Rule.model_validate(current_dict)

        try:
            await self.redis.hset(self.key, str(rule_id), updated_rule.model_dump_json())
            return updated_rule
        except RedisError as exc:
            raise CacheError("Cannot update rule in Redis") from exc

    async def delete_rule(self, rule_id: int) -> bool:
        try:
            deleted = await self.redis.hdel(self.key, str(rule_id))
            return deleted > 0
        except RedisError as exc:
            raise CacheError("Cannot delete rule from Redis") from exc
