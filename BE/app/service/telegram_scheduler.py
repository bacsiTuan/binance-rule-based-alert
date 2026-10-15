import asyncio
import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from apscheduler.events import EVENT_JOB_MAX_INSTANCES, EVENT_JOB_MISSED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from redis.exceptions import RedisError

from app.errors import BinanceError, CacheError
from app.indicator_models import IndicatorRequest
from app.indicators import calculate_indicators
from app.telegram_state import COMPARISONS, TelegramStateStore

logger = logging.getLogger(__name__)
DURATIONS = {"1h": 3600000, "1d": 86400000, "1w": 604800000}
SHUTDOWN_SECONDS = 15


def boundary_ms(now, timeframe):
    start = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    if timeframe in ("1d", "1w"):
        start = start.replace(hour=0)
    if timeframe == "1w":
        start -= timedelta(days=start.weekday())
    return int(start.timestamp()) * 1000


def skip_reason(rule, now):
    if not rule.enabled:
        return "disabled"
    if (rule.operator not in COMPARISONS or rule.candle_mode != "closed"
            or rule.indicator.type not in ("sma", "ema", "rsi")
            or type(rule.indicator.length) is not int
            or not 1 <= rule.indicator.length <= 999
            or type(rule.target) not in (float, int)):
        return "unsupported_condition"
    try:
        if not Decimal(str(rule.target)).is_finite():
            return "unsupported_condition"
    except InvalidOperation:
        return "unsupported_condition"
    if rule.expiration is not None:
        try:
            end = datetime.fromisoformat(rule.expiration)
            if end.tzinfo is None:
                return "invalid_expiration"
        except ValueError:
            return "invalid_expiration"
        if end <= now:
            return "expired"
    return None


def eligible(rule, now):
    return skip_reason(rule, now) is None


class TelegramScheduler:
    def __init__(self, service, rules, sender, *, clock=None, sleep=asyncio.sleep,
                 monotonic=time.monotonic):
        self.service = service
        self.rules = rules
        self.sender = sender
        self.clock = clock or (lambda: datetime.now(UTC))
        self.sleep = sleep
        self.monotonic = monotonic
        self.store = TelegramStateStore(rules.redis, service.prefix, rules.key)
        self.scheduler = AsyncIOScheduler(timezone=UTC)
        self.send_lock = asyncio.Lock()
        self.blocked_until = 0.0
        self.tasks = set()
        self.stopping = False
        self.stop_event = asyncio.Event()
        self.last_boundary = {}

    async def start(self):
        try:
            await self.store.bootstrap(await self.rules.list_rules())
        except (CacheError, RedisError):
            # Keep the schedule alive; reconnect resumes at a future boundary.
            logger.warning("telegram_state_unavailable_at_start")
        for timeframe, duration in DURATIONS.items():
            options = {"minute": 0, "second": 5}
            if timeframe in ("1d", "1w"):
                options["hour"] = 0
            if timeframe == "1w":
                options["day_of_week"] = "mon"
            trigger = CronTrigger(timezone=UTC, **options)
            next_boundary = boundary_ms(self.clock(), timeframe) + duration
            first = datetime.fromtimestamp(next_boundary / 1000, UTC) + timedelta(seconds=5)
            self.scheduler.add_job(
                self.scan, trigger, args=[timeframe], id=f"telegram-{timeframe}",
                max_instances=1, coalesce=True, misfire_grace_time=30,
                next_run_time=first,
            )
        self.scheduler.add_listener(self._missed, EVENT_JOB_MISSED | EVENT_JOB_MAX_INSTANCES)
        self.scheduler.start()

    @staticmethod
    def _missed(event):
        logger.warning("telegram_schedule_skipped job=%s reason=%s", event.job_id, event.code)

    async def stop(self):
        self.stopping = True
        self.stop_event.set()
        if self.scheduler.running:
            self.scheduler.pause()
        if self.tasks:
            _, pending = await asyncio.wait(tuple(self.tasks), timeout=SHUTDOWN_SECONDS)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _wait(self, seconds):
        if self.stopping:
            return False
        if seconds <= 0:
            await self.sleep(0)
            return not self.stopping
        sleeper = asyncio.create_task(self.sleep(seconds))
        stopped = asyncio.create_task(self.stop_event.wait())
        try:
            await asyncio.wait((sleeper, stopped), return_when=asyncio.FIRST_COMPLETED)
            if sleeper.done():
                sleeper.result()
            return not self.stopping
        finally:
            for task in (sleeper, stopped):
                if not task.done():
                    task.cancel()
            await asyncio.gather(sleeper, stopped, return_exceptions=True)

    async def scan(self, timeframe):
        stats = {"scanned": 0, "skipped": 0, "triggered": 0, "attempted": 0,
                     "accepted": 0, "failed": 0, "unknown": 0, "cancelled": 0}
        task = asyncio.current_task()
        self.tasks.add(task)
        try:
            await self._scan(timeframe, stats)
        except asyncio.CancelledError:
            raise
        except (CacheError, RedisError, ValueError, TimeoutError):
            logger.warning("telegram_scan_failed timeframe=%s", timeframe)
        finally:
            self.tasks.discard(task)
            logger.info("telegram_scan timeframe=%s counts=%s", timeframe, stats)
        return stats

    async def _scan(self, timeframe, stats):
        now = self.clock()
        boundary = boundary_ms(now, timeframe)
        delay = now.timestamp() - boundary / 1000
        if self.stopping or not 5 <= delay <= 35:
            logger.info("telegram_scan_skipped timeframe=%s reason=outside_schedule", timeframe)
            return
        if boundary <= self.last_boundary.get(timeframe, -1):
            logger.info("telegram_scan_skipped timeframe=%s reason=duplicate_candle", timeframe)
            return
        self.last_boundary[timeframe] = boundary
        rules = await self.rules.list_rules()
        await self.store.bootstrap(rules, recover=False)
        groups = defaultdict(list)
        for rule in rules:
            if rule.timeframe != timeframe:
                continue
            reason = skip_reason(rule, now)
            if reason is None:
                groups[rule.symbol].append(rule)
            else:
                stats["skipped"] += 1
                logger.info("telegram_rule_skipped rule_id=%s reason=%s", rule.id, reason)
        for symbol, group in groups.items():
            if self.stopping:
                return
            try:
                snapshot = await self._snapshot(symbol, timeframe, boundary)
                if snapshot is None:
                    stats["skipped"] += len(group)
                    logger.warning("telegram_target_not_ready timeframe=%s", timeframe)
                    continue
                if snapshot.stale or snapshot.source == "stale":
                    stats["skipped"] += len(group)
                    logger.warning("telegram_stale_data timeframe=%s", timeframe)
                    continue
                pairs = sorted({(r.indicator.type, r.indicator.length) for r in group})
                request = IndicatorRequest(
                    symbol=symbol, interval=timeframe, limit=1000, include_open=False,
                    indicators=[{"name": name, "period": period} for name, period in pairs],
                )
                results = calculate_indicators(
                    snapshot, request, int(self.clock().timestamp() * 1000),
                    self.service.settings.binance_market,
                )
                values = {(s.name, s.period): s.latest for s in results.results}
                for rule in group:
                    point = values[(rule.indicator.type, rule.indicator.length)]
                    if (point.status != "ok" or point.provisional
                            or point.close_time != boundary - 1):
                        stats["skipped"] += 1
                        logger.info("telegram_rule_skipped rule_id=%s reason=insufficient_history",
                                    rule.id)
                        continue
                    if not eligible(rule, self.clock()):
                        stats["skipped"] += 1
                        continue
                    try:
                        stats["scanned"] += 1
                        reserved = await self.store.observe(
                            rule, boundary, point.open_time, point.value, str(rule.target)
                        )
                        if reserved:
                            generation, event = reserved
                            stats["triggered"] += 1
                            logger.info("telegram_triggered rule_id=%s event_id=%s",
                                        rule.id, event.event_id)
                            await self.deliver(rule, generation, event, stats)
                    except (CacheError, RedisError, ValueError):
                        logger.warning("telegram_rule_failed rule_id=%s", rule.id)
            except asyncio.CancelledError:
                raise
            except (BinanceError, CacheError, RedisError, ValueError, TimeoutError):
                stats["skipped"] += len(group)
                logger.warning("telegram_group_failed timeframe=%s", timeframe)

    async def _snapshot(self, symbol, timeframe, boundary):
        deadline = boundary / 1000 + 120
        remaining = deadline - self.clock().timestamp()
        if remaining <= 0:
            return None
        async with asyncio.timeout(remaining):
            for offset in (5, 15, 30):
                if not await self._wait(max(0, boundary / 1000 + offset
                                           - self.clock().timestamp())):
                    return None
                if self.clock().timestamp() >= deadline:
                    return None
                result = await self.service.closed_klines(symbol, timeframe, boundary)
                if self.clock().timestamp() >= deadline:
                    return None
                if result is not None:
                    return result
        return None

    def _text(self, rule, value, threshold, open_ms, close_ms, message=None):
        """Return the alert text and the length of its bold title line."""
        body = (
            f"Market: {self.service.settings.binance_market}"
            f" | Symbol: {rule.symbol} | Timeframe: {rule.timeframe}\n"
            f"Indicator: {rule.indicator.type.upper()}({rule.indicator.length})\n"
            f"Value: {Decimal(value):.2f} {COMPARISONS[rule.operator][1]} {threshold}\n"
            "Candle: CLOSED | Timezone: UTC\n"
            f"Open: {datetime.fromtimestamp(open_ms / 1000, UTC):%Y-%m-%d %H:%M:%S}\n"
            f"Close: {datetime.fromtimestamp(close_ms / 1000, UTC):%Y-%m-%d %H:%M:%S}"
        )
        title = f"Rule #{rule.id}"
        if message:
            # Only the user message is trimmed to fit Telegram's 4096 limit.
            title = f"{title}: {message}"[:max(len(title), 4095 - len(body))]
        return f"{title}\n{body}", len(title)

    async def trigger_all(self):
        """Evaluate every stored rule on its latest closed candle right now.

        Sends a Telegram message for each rule whose condition currently holds.
        Unlike the scheduled scan this does not touch the dedup/latch state, so
        it never suppresses or duplicates a scheduled alert.
        """
        stats = {"scanned": 0, "skipped": 0, "triggered": 0, "accepted": 0,
                 "failed": 0, "unknown": 0}
        task = asyncio.current_task()
        self.tasks.add(task)
        try:
            now = self.clock()
            groups = defaultdict(list)
            for rule in await self.rules.list_rules():
                if skip_reason(rule, now) is None:
                    groups[(rule.symbol, rule.timeframe)].append(rule)
                else:
                    stats["skipped"] += 1
            for (symbol, timeframe), group in groups.items():
                if self.stopping:
                    break
                boundary = boundary_ms(now, timeframe)
                try:
                    snapshot = await self.service.closed_klines(symbol, timeframe, boundary)
                    if snapshot is None or snapshot.stale or snapshot.source == "stale":
                        stats["skipped"] += len(group)
                        continue
                    pairs = sorted({(r.indicator.type, r.indicator.length) for r in group})
                    request = IndicatorRequest(
                        symbol=symbol, interval=timeframe, limit=1000, include_open=False,
                        indicators=[{"name": name, "period": period} for name, period in pairs],
                    )
                    results = calculate_indicators(
                        snapshot, request, int(now.timestamp() * 1000),
                        self.service.settings.binance_market,
                    )
                    values = {(s.name, s.period): s.latest for s in results.results}
                except (BinanceError, CacheError, RedisError, ValueError, TimeoutError):
                    stats["skipped"] += len(group)
                    logger.warning("telegram_manual_group_failed timeframe=%s", timeframe)
                    continue
                for rule in group:
                    point = values[(rule.indicator.type, rule.indicator.length)]
                    if (point.status != "ok" or point.provisional
                            or point.close_time != boundary - 1):
                        stats["skipped"] += 1
                        continue
                    stats["scanned"] += 1
                    if not COMPARISONS[rule.operator][0](
                            Decimal(point.value), Decimal(str(rule.target))):
                        continue
                    stats["triggered"] += 1
                    text, bold = self._text(rule, point.value, str(rule.target),
                                            point.open_time, point.close_time, rule.message)
                    async with self.send_lock:
                        result = await self.sender.send_message(text, bold_chars=bold)
                    if result.retry_after:
                        self.blocked_until = self.monotonic() + result.retry_after
                    stats[result.status] += 1
                    logger.info("telegram_manual_delivery rule_id=%s status=%s",
                                rule.id, result.status)
        finally:
            self.tasks.discard(task)
            logger.info("telegram_manual_trigger counts=%s", stats)
        return stats

    async def deliver(self, rule, generation, event, stats=None):
        try:
            async with self.send_lock:
                proceed = await self._wait(max(0, self.blocked_until - self.monotonic()))
                current = await self.rules.get_rule(rule.id)
                if (not proceed or self.stopping or current is None
                        or not eligible(current, self.clock())
                        or not await self.store.current(rule.id, generation)):
                    await self.store.finalize(rule.id, generation, event.event_id, "cancelled")
                    if stats is not None:
                        stats["cancelled"] += 1
                    return
                text, bold = self._text(rule, event.value, event.threshold,
                                        event.candle_open_ms, event.candle_close_ms,
                                        current.message)
                if len(text) > 4096:
                    await self.store.finalize(
                        rule.id, generation, event.event_id, "failed", error_code="message_too_long"
                    )
                    if stats is not None:
                        stats["failed"] += 1
                    return
                if stats is not None:
                    stats["attempted"] += 1
                logger.info("telegram_attempt rule_id=%s event_id=%s", rule.id, event.event_id)
                result = await self.sender.send_message(text, bold_chars=bold)
                if result.retry_after:
                    self.blocked_until = self.monotonic() + result.retry_after
                if stats is not None:
                    stats[result.status] += 1
                await self.store.finalize(
                    rule.id, generation, event.event_id, result.status,
                    message_id=result.message_id, error_code=result.error_code,
                )
                logger.info("telegram_delivery rule_id=%s status=%s", rule.id, result.status)
        except asyncio.CancelledError:
            # Do not issue another Redis/network operation during cancellation.
            # The durable reservation is interpreted as unknown on recovery.
            if stats is not None:
                stats["unknown"] += 1
            logger.warning("telegram_delivery_unknown rule_id=%s reason=shutdown", rule.id)
            raise
