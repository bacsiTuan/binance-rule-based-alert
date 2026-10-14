import json
import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.errors import CacheError
from app.models import Rule, RuleCreate, RuleUpdate
from app.telegram_state import persist_rule

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
        "trigger_type": "once_per_bar_close",
        "message": "RSI(14) Crossing Up 30 on BTCUSDT",
        "notifications": ["app", "toasts"],
        "enabled": True,
        "created_at": "2026-10-01T08:00:00Z",
    },
    {
        "id": 2,
        "symbol": "BTCUSDT",
        "timeframe": "1d",
        "indicator": {"type": "mass_index", "length": 10},
        "operator": "cross_above",
        "target": 9.52,
        "candle_mode": "closed",
        "trigger_type": "once",
        "message": "Mass index (10) Crossing 9.52 on BTCUSDT",
        "notifications": ["app", "toasts"],
        "enabled": True,
        "created_at": "2026-10-02T09:30:00Z",
    },
    {
        "id": 3,
        "symbol": "ETHUSDT",
        "timeframe": "1d",
        "indicator": {"type": "sma", "length": 50},
        "operator": "cross_above",
        "target": {"type": "sma", "length": 200},
        "candle_mode": "closed",
        "trigger_type": "once_per_bar_close",
        "message": "SMA(50) Crossing Up SMA(200) on ETHUSDT",
        "notifications": ["app", "toasts"],
        "enabled": False,
        "created_at": "2026-10-03T10:00:00Z",
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
        rules.sort(key=lambda r: r.id, reverse=True)
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

            # Tự động tạo message nếu chưa có
            msg = payload.message
            if not msg:
                ind = payload.indicator
                left_str = "Price" if ind.type == "close" else f"{ind.type.replace('_', ' ').title()}({ind.length or ''})"
                target_obj = payload.target
                if hasattr(target_obj, "type"):
                    right_str = f"{target_obj.type.replace('_', ' ').title()}({target_obj.length})"
                else:
                    right_str = str(target_obj)
                op_map = {
                    "cross_above": "Crossing Up",
                    "cross_below": "Crossing Down",
                    "gt": "Greater Than",
                    "gte": "Greater Than or Equal",
                    "lt": "Less Than",
                    "lte": "Less Than or Equal",
                }
                op_label = op_map.get(payload.operator, payload.operator)
                msg = f"{left_str} {op_label} {right_str} on {payload.symbol.upper()}"

            rule = Rule(
                id=rule_id,
                symbol=payload.symbol.upper(),
                timeframe=payload.timeframe,
                indicator=payload.indicator,
                operator=payload.operator,
                target=payload.target,
                candle_mode=payload.candle_mode,
                trigger_type=payload.trigger_type,
                expiration=payload.expiration,
                message=msg,
                notifications=payload.notifications,
                enabled=True,
                created_at=now_str,
            )
            await persist_rule(self.redis, self.key, rule_id, None, rule)
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
            await persist_rule(self.redis, self.key, rule_id, existing, updated_rule)
            return updated_rule
        except RedisError as exc:
            raise CacheError("Cannot update rule in Redis") from exc

    async def delete_rule(self, rule_id: int) -> bool:
        try:
            existing = await self.get_rule(rule_id)
            if existing is None:
                return False
            await persist_rule(self.redis, self.key, rule_id, existing, None)
            return True
        except RedisError as exc:
            raise CacheError("Cannot delete rule from Redis") from exc
