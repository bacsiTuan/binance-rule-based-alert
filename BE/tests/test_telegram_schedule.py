import asyncio
from datetime import UTC, datetime

import pytest

from app.service.telegram_scheduler import DURATIONS


@pytest.mark.parametrize("start,frames", [
    ("2030-01-08T10:59:00+00:00", {"1h"}),
    ("2030-01-08T23:59:00+00:00", {"1h", "1d"}),
    ("2030-01-06T23:59:00+00:00", {"1h", "1d", "1w"}),
    ("2029-12-31T23:59:00+00:00", {"1h", "1d"}),
])
async def test_executor_dispatches_calendar_boundaries(telegram_harness, scheduler_clock, start, frames):
    from apscheduler.events import EVENT_JOB_EXECUTED

    h = telegram_harness
    h.clock.now = datetime.fromisoformat(start)
    for frame in DURATIONS:
        await h.create(timeframe=frame)
    events = []
    h.watcher.scheduler.add_listener(events.append, EVENT_JOB_EXECUTED)
    scheduler_clock.attach(h.watcher)
    await h.watcher.start()
    await scheduler_clock.tick(h.watcher)
    h.clock.advance(64)
    await scheduler_clock.tick(h.watcher)
    assert not h.calls
    h.clock.advance(1)
    await scheduler_clock.tick(h.watcher)
    assert {e.job_id for e in events} == {f"telegram-{frame}" for frame in frames}
    assert len(events) == len(frames)
    for field in ("triggered", "attempted", "accepted"):
        assert sum(e.retval[field] for e in events) == len(frames)
    assert sorted(frame for _, frame, _, _ in h.calls) == sorted(frames)
    await scheduler_clock.tick(h.watcher)
    assert len(events) == len(frames)
    h.clock.advance(3600)
    await scheduler_clock.tick(h.watcher)
    assert len(events) == len(frames) + 1
    assert events[-1].job_id == "telegram-1h"
    assert events[-1].retval["triggered"] == 0


@pytest.mark.parametrize("minute,second", [(30, 0), (0, 3)])
async def test_executor_startup_waits_next_boundary(telegram_harness, scheduler_clock, minute, second):
    h = telegram_harness
    h.clock.now = datetime(2030, 1, 7, 0, minute, second, tzinfo=UTC)
    await h.create()
    scheduler_clock.attach(h.watcher)
    await h.watcher.start()
    await scheduler_clock.tick(h.watcher)
    await scheduler_clock.tick(h.watcher, datetime(2030, 1, 7, 1, 0, 4, tzinfo=UTC))
    assert not h.calls
    h.clock.advance(1)
    await scheduler_clock.tick(h.watcher)
    h.sender.send_message.assert_awaited_once()


async def test_executor_misfire_not_replayed(telegram_harness, scheduler_clock):
    from apscheduler.events import EVENT_JOB_MISSED

    h = telegram_harness
    await h.create()
    events = []
    h.watcher.scheduler.add_listener(events.append, EVENT_JOB_MISSED)
    scheduler_clock.attach(h.watcher)
    await h.watcher.start()
    await scheduler_clock.tick(h.watcher)
    h.clock.advance(96)
    await scheduler_clock.tick(h.watcher)
    assert {e.job_id for e in events} == {"telegram-1h", "telegram-1d", "telegram-1w"}
    assert not h.calls
    await scheduler_clock.tick(h.watcher)
    assert len(events) == 3
    h.clock.advance(3569)
    await scheduler_clock.tick(h.watcher)
    assert len(h.calls) == 1
    h.sender.send_message.assert_awaited_once()


async def test_executor_max_instances_skips_without_replay(telegram_harness, scheduler_clock):
    from apscheduler.events import EVENT_JOB_MAX_INSTANCES

    h = telegram_harness
    await h.create()
    entered, release = asyncio.Event(), asyncio.Event()
    fetch = h.market.closed_klines.side_effect

    async def blocked(*args):
        entered.set()
        await release.wait()
        return await fetch(*args)

    h.market.closed_klines.side_effect = blocked
    events = []
    h.watcher.scheduler.add_listener(events.append, EVENT_JOB_MAX_INSTANCES)
    scheduler_clock.attach(h.watcher)
    await h.watcher.start()
    await scheduler_clock.tick(h.watcher)
    h.clock.advance(65)
    await scheduler_clock.tick(h.watcher, wait=False)
    await asyncio.wait_for(entered.wait(), timeout=2)
    try:
        h.clock.advance(3600)
        await scheduler_clock.tick(h.watcher, wait=False)
        assert [e.job_id for e in events] == ["telegram-1h"]
    finally:
        release.set()
        await scheduler_clock.tick(h.watcher)
    h.sender.send_message.assert_not_awaited()
    await scheduler_clock.tick(h.watcher)
    assert len(events) == 1
    h.clock.advance(3600)
    await scheduler_clock.tick(h.watcher)
    h.sender.send_message.assert_awaited_once()


async def test_coincident_frames_and_duplicate_callbacks(telegram_harness):
    h = telegram_harness
    for frame in DURATIONS:
        await h.create(timeframe=frame)
    h.clock.advance(65)
    await asyncio.gather(*(h.watcher.scan(frame) for frame in DURATIONS))
    assert sorted(frame for _, frame, _, _ in h.calls) == sorted(DURATIONS)
    assert h.sender.send_message.await_count == 3
    await asyncio.gather(*(h.watcher.scan(frame) for frame in DURATIONS))
    assert h.sender.send_message.await_count == 3


@pytest.mark.parametrize("offset", [0, 4, 36, 200])
async def test_not_early_or_misfired(telegram_harness, offset):
    h = telegram_harness
    await h.create()
    h.clock.advance(60 + offset)
    await h.watcher.scan("1h")
    assert not h.calls


async def test_readiness_is_bounded_and_uses_fixed_boundary(telegram_harness):
    h = telegram_harness
    await h.create()
    h.market.closed_klines.side_effect = None
    h.market.closed_klines.return_value = None
    h.clock.advance(65)
    stats = await h.watcher.scan("1h")
    assert h.market.closed_klines.await_count == 3
    targets = [call.args[2] for call in h.market.closed_klines.await_args_list]
    assert len(set(targets)) == 1
    assert h.clock.now.second == 30
    assert stats["triggered"] == 0
    await h.watcher.scan("1h")
    assert h.market.closed_klines.await_count == 3


async def test_data_after_deadline_is_not_used(telegram_harness):
    h = telegram_harness
    await h.create()
    original = h.market.closed_klines.side_effect
    async def too_late(*args):
        snapshot = await original(*args)
        h.clock.advance(121)
        return snapshot
    h.market.closed_klines.side_effect = too_late
    h.clock.advance(65)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_not_awaited()


async def test_hanging_fetch_is_cancelled_by_deadline(telegram_harness, monkeypatch):
    from app.service import telegram_scheduler
    h = telegram_harness
    await h.create()
    real_timeout = asyncio.timeout
    budgets = []
    def short_timeout(seconds):
        budgets.append(seconds)
        return real_timeout(0.01)
    monkeypatch.setattr(telegram_scheduler.asyncio, "timeout", short_timeout)
    cancelled = asyncio.Event()
    async def hanging(*args):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    h.market.closed_klines.side_effect = hanging
    h.clock.advance(65)
    await h.watcher.scan("1h")
    assert budgets == [115]
    assert cancelled.is_set()
    h.sender.send_message.assert_not_awaited()
    h.sender.send_message.assert_not_awaited()


async def test_only_matching_frame_and_activation_after_boundary(telegram_harness):
    h = telegram_harness
    await h.create(timeframe="1d")
    h.clock.now = datetime(2030, 1, 7, 1, 0, 5, tzinfo=UTC)
    await h.watcher.scan("1h")
    assert not h.calls
    await h.create(timeframe="1h")
    await h.watcher.scan("1h")
    h.sender.send_message.assert_not_awaited()
    h.clock.advance(3600)
    await h.watcher.scan("1h")
    h.sender.send_message.assert_awaited_once()


async def test_cron_has_single_instance_and_no_backfill(telegram_harness):
    h = telegram_harness
    await h.create()
    await h.watcher.start()
    jobs = h.watcher.scheduler.get_jobs()
    assert len(jobs) == 3
    for job in jobs:
        assert job.max_instances == 1 and job.coalesce
        assert job.misfire_grace_time == 30
        assert job.next_run_time > h.clock.now
    assert not h.calls
