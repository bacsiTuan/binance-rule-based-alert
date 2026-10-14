import hashlib
import json
import logging
import operator
import time
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from redis.exceptions import RedisError, WatchError

from app.errors import CacheError

META_KEY = "app:rules:telegram_meta"
logger = logging.getLogger(__name__)
CONDITION_FIELDS = ("symbol", "timeframe", "indicator", "operator", "target", "candle_mode")
COMPARISONS = {"gt": (operator.gt, ">"), "gte": (operator.ge, ">="),
               "lt": (operator.lt, "<"), "lte": (operator.le, "<=")}
UtcMilliseconds = Annotated[int, Field(strict=True, ge=0)]


def finite_decimal(value):
    try:
        valid = Decimal(value).is_finite()
    except InvalidOperation:
        valid = False
    if not valid:
        raise ValueError("Expected finite decimal string")
    return value


def now_ms():
    return time.time_ns() // 1_000_000


class Delivery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    candle_open_ms: UtcMilliseconds
    candle_close_ms: UtcMilliseconds
    value: str
    threshold: str
    reserved_at_ms: UtcMilliseconds
    delivery_status: Literal[
        "attempt_reserved", "accepted", "failed", "unknown", "cancelled"
    ] = "attempt_reserved"
    completed_at_ms: UtcMilliseconds | None = None
    message_id: Annotated[int, Field(strict=True, ge=0)] | None = None
    error_code: Annotated[str, Field(pattern=r"^[a-z_]+$")] | None = None

    @field_validator("value", "threshold")
    @classmethod
    def finite_decimal(cls, value):
        return finite_decimal(value)

    @model_validator(mode="after")
    def validate_result(self):
        if self.candle_close_ms < self.candle_open_ms:
            raise ValueError("Candle timestamps are reversed")
        if (self.delivery_status == "accepted") != (self.message_id is not None):
            raise ValueError("Only accepted delivery has a message ID")
        return self


class MonitorState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    generation: str
    rule_id: Annotated[int, Field(strict=True, ge=1)]
    condition: Literal["unknown", "below", "latched"] = "unknown"
    last_processed_close_ms: UtcMilliseconds | None = None
    last_value: str | None = None
    last_event: Delivery | None = None
    updated_at_ms: UtcMilliseconds

    @field_validator("generation")
    @classmethod
    def valid_generation(cls, value):
        UUID(value)
        return value

    @field_validator("last_processed_close_ms", "updated_at_ms", mode="before")
    @classmethod
    def valid_timestamp(cls, value):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Expected UTC milliseconds")
        return value

    @field_validator("last_value")
    @classmethod
    def finite_decimal(cls, value):
        return finite_decimal(value) if value is not None else None


class MonitorMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    generation: str = Field(default_factory=lambda: str(uuid4()))
    activated_at_ms: UtcMilliseconds = Field(default_factory=lambda: now_ms())
    condition_fingerprint: str
    provisioned_namespaces: list[str] = Field(default_factory=list)

    @field_validator("generation")
    @classmethod
    def valid_generation(cls, value):
        UUID(value)
        return value


def fingerprint(rule):
    data = rule.model_dump(include=set(CONDITION_FIELDS))
    if type(rule.target) in (int, float):
        number = Decimal(str(rule.target))
        text = format(number, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        data["target"] = "0" if number.is_zero() else text
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


async def persist_rule(redis, key, rule_id, previous, updated):
    """Commit the public rule and its monitoring revision together."""
    field = str(rule_id)
    try:
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.watch(key, META_KEY)
            raw = await pipe.hget(key, field)
            if (json.loads(raw) if raw else None) != (
                previous.model_dump() if previous else None
            ):
                raise CacheError("Rule changed concurrently; reload and retry")
            meta_raw = await pipe.hget(META_KEY, field)
            meta = MonitorMetadata.model_validate_json(meta_raw) if meta_raw else None
            old_namespaces = meta.provisioned_namespaces if meta else []
            reset = updated is not None and (
                meta is None or previous is None
                or previous.enabled != updated.enabled
                or fingerprint(previous) != fingerprint(updated)
            )
            if reset:
                meta = MonitorMetadata(condition_fingerprint=fingerprint(updated))
            pipe.multi()
            if updated is None:
                pipe.hdel(key, field)
                pipe.hdel(META_KEY, field)
            else:
                pipe.hset(key, field, updated.model_dump_json())
                pipe.hset(META_KEY, field, meta.model_dump_json())
            if updated is None or reset:
                for namespace in old_namespaces:
                    pipe.hdel(namespace, field)
            await pipe.execute()
    except (RedisError, ValueError) as exc:
        raise CacheError("Cannot commit rule monitoring metadata") from exc


class TelegramStateStore:
    def __init__(self, redis, market_prefix, rules_key="app:rules"):
        self.redis = redis
        self.rules_key = rules_key
        self.key = market_prefix.replace("binance:", "telegram:", 1) + ":state"

    async def bootstrap(self, rules, *, recover=True):
        for rule in rules:
            field = str(rule.id)
            try:
                async with self.redis.pipeline(transaction=True) as pipe:
                    await pipe.watch(self.rules_key, META_KEY, self.key)
                    raw = await pipe.hget(self.rules_key, field)
                    if raw is None or json.loads(raw) != rule.model_dump():
                        continue
                    meta_raw = await pipe.hget(META_KEY, field)
                    meta = (
                        MonitorMetadata.model_validate_json(meta_raw) if meta_raw
                        else MonitorMetadata(condition_fingerprint=fingerprint(rule))
                    )
                    if self.key in meta.provisioned_namespaces:
                        raw_state = await pipe.hget(self.key, field)
                        if raw_state:
                            state = MonitorState.model_validate_json(raw_state)
                            if (recover and state.last_event and
                                    state.last_event.delivery_status == "attempt_reserved"):
                                state.last_event.delivery_status = "unknown"
                                pipe.multi()
                                pipe.hset(self.key, field, state.model_dump_json())
                                await pipe.execute()
                        continue
                    meta.provisioned_namespaces.append(self.key)
                    state = MonitorState(
                        generation=meta.generation, rule_id=rule.id, updated_at_ms=now_ms()
                    )
                    pipe.multi()
                    pipe.hset(META_KEY, field, meta.model_dump_json())
                    pipe.hset(self.key, field, state.model_dump_json())
                    await pipe.execute()
            except WatchError:
                continue
            except ValueError:
                logger.warning("telegram_state_unavailable rule_id=%s", rule.id)
                continue
            except RedisError as exc:
                raise CacheError("Cannot initialize monitoring state") from exc

    async def observe(self, rule, boundary, opened, value, threshold):
        field = str(rule.id)
        for _ in range(3):
            try:
                async with self.redis.pipeline(transaction=True) as pipe:
                    await pipe.watch(self.rules_key, META_KEY, self.key)
                    raw = await pipe.hget(self.rules_key, field)
                    if raw is None or json.loads(raw) != rule.model_dump():
                        return None
                    meta_raw = await pipe.hget(META_KEY, field)
                    state_raw = await pipe.hget(self.key, field)
                    if not meta_raw or not state_raw:
                        logger.warning("telegram_state_unavailable rule_id=%s", rule.id)
                        return None
                    meta = MonitorMetadata.model_validate_json(meta_raw)
                    state = MonitorState.model_validate_json(state_raw)
                    if (
                        not rule.enabled or boundary <= meta.activated_at_ms
                        or meta.generation != state.generation
                        or state.rule_id != rule.id
                        or meta.condition_fingerprint != fingerprint(rule)
                        or (state.last_processed_close_ms is not None
                            and boundary - 1 <= state.last_processed_close_ms)
                    ):
                        return None
                    try:
                        actual, target = Decimal(value), Decimal(threshold)
                    except InvalidOperation:
                        return None
                    if not actual.is_finite() or not target.is_finite():
                        return None
                    event = None
                    comparison = COMPARISONS.get(rule.operator)
                    if comparison is None:
                        return None
                    if not comparison[0](actual, target):
                        # Preserve the persisted schema: "below" means condition false.
                        state.condition = "below"
                    elif state.condition != "latched":
                        state.condition = "latched"
                        event = Delivery(
                            event_id=hashlib.sha256(
                                f"{self.key}:{field}:{meta.generation}:{boundary}".encode()
                            ).hexdigest(),
                            candle_open_ms=opened, candle_close_ms=boundary - 1,
                            value=value, threshold=threshold, reserved_at_ms=now_ms(),
                        )
                        state.last_event = event
                    state.last_processed_close_ms = boundary - 1
                    state.last_value = value
                    state.updated_at_ms = now_ms()
                    pipe.multi()
                    pipe.hset(self.key, field, state.model_dump_json())
                    await pipe.execute()
                    return (meta.generation, event) if event else None
            except WatchError:
                continue
            except (RedisError, ValueError) as exc:
                raise CacheError("Monitoring state unavailable") from exc
        return None

    async def current(self, rule_id, generation):
        raw = await self.redis.hget(META_KEY, str(rule_id))
        return bool(raw and MonitorMetadata.model_validate_json(raw).generation == generation)

    async def finalize(self, rule_id, generation, event_id, status, **details):
        for _ in range(3):
            try:
                async with self.redis.pipeline(transaction=True) as pipe:
                    await pipe.watch(self.key)
                    raw = await pipe.hget(self.key, str(rule_id))
                    if not raw:
                        return
                    state = MonitorState.model_validate_json(raw)
                    if (state.generation != generation or not state.last_event
                            or state.last_event.event_id != event_id):
                        return
                    state.last_event = Delivery.model_validate({
                        **state.last_event.model_dump(),
                        "delivery_status": status, "completed_at_ms": now_ms(),
                        "message_id": details.get("message_id"),
                        "error_code": details.get("error_code"),
                    })
                    pipe.multi()
                    pipe.hset(self.key, str(rule_id), state.model_dump_json())
                    await pipe.execute()
                    return
            except WatchError:
                continue
        raise CacheError("Cannot finalize Telegram delivery after contention")
