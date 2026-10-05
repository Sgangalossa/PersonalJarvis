"""Unit tests for TaskScheduler — heap, event dispatch, cancel."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from jarvis.control.cancel import CancelToken
from jarvis.core.bus import EventBus
from jarvis.core.events import MessageSent, MissionCompleted
from jarvis.tasks.scheduler import TaskScheduler, _match_filter
from jarvis.tasks.schema import (
    SpeakAction,
    TaskSpec,
    TriggerAfterDelay,
    TriggerAtTime,
    TriggerOnEvent,
    TriggerWebhook,
)
from jarvis.tasks.store import TaskStore


class FakeRunner:
    """Haelt eine Liste aller ``run()``-Calls fest."""

    def __init__(self) -> None:
        self.dispatched: list[str] = []
        self.gate = asyncio.Event()

    async def run(self, task_id: str, *_args: Any, **_kwargs: Any) -> None:
        self.dispatched.append(task_id)
        self.gate.set()


@pytest.fixture
async def store(tmp_path: Path):
    s = TaskStore(tmp_path / "sched.db")
    await s.init()
    try:
        yield s
    finally:
        await s.close()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()


# ----------------------------------------------------------------------
# after_delay
# ----------------------------------------------------------------------

async def test_after_delay_fires_after_sleep(
    store: TaskStore, bus: EventBus, runner: FakeRunner
) -> None:
    scheduler = TaskScheduler(store=store, bus=bus, runner=runner)
    spec = TaskSpec(
        title="schnell",
        trigger=TriggerAfterDelay(delay_seconds=0.1),
        action=SpeakAction(text="x"),
    )
    token = CancelToken()
    loop_task = asyncio.create_task(scheduler.run(token))
    await scheduler.schedule(spec)

    # Warte bis Runner gelaufen ist (max 1 s)
    try:
        await asyncio.wait_for(runner.gate.wait(), timeout=1.0)
    finally:
        token.cancel("test_done")
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass

    assert runner.dispatched == [str(spec.id)]


# ----------------------------------------------------------------------
# at_time
# ----------------------------------------------------------------------

async def test_at_time_fires_at_iso_timestamp(
    store: TaskStore, bus: EventBus, runner: FakeRunner
) -> None:
    scheduler = TaskScheduler(store=store, bus=bus, runner=runner)
    # 150ms in die Zukunft
    iso = (datetime.now(UTC) + timedelta(milliseconds=150)).isoformat()
    spec = TaskSpec(
        title="genau gleich",
        trigger=TriggerAtTime(iso_timestamp=iso),
        action=SpeakAction(text="x"),
    )
    token = CancelToken()
    loop_task = asyncio.create_task(scheduler.run(token))
    await scheduler.schedule(spec)

    try:
        await asyncio.wait_for(runner.gate.wait(), timeout=1.5)
    finally:
        token.cancel("test_done")
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass

    assert runner.dispatched == [str(spec.id)]


# ----------------------------------------------------------------------
# on_event
# ----------------------------------------------------------------------

async def test_on_event_dispatches_when_event_published(
    store: TaskStore, bus: EventBus, runner: FakeRunner
) -> None:
    scheduler = TaskScheduler(store=store, bus=bus, runner=runner)
    scheduler.bind_bus()

    spec = TaskSpec(
        title="email",
        trigger=TriggerOnEvent(event_name="MessageSent", filter_expr=None),
        action=SpeakAction(text="x"),
    )
    await scheduler.schedule(spec)

    await bus.publish(MessageSent(thread_id="t1", role="user", text="hi"))

    # runner.run ist awaited direkt im subscribe_all-Handler, also synchron.
    assert runner.dispatched == [str(spec.id)]


async def test_on_event_subject_dedup_survives_scheduler_restart(
    tmp_path: Path,
) -> None:
    db = tmp_path / "event-dedup.db"
    bus1 = EventBus()
    store1 = TaskStore(db)
    await store1.init()
    runner1 = FakeRunner()
    scheduler1 = TaskScheduler(store=store1, bus=bus1, runner=runner1)
    scheduler1.bind_bus()
    spec = TaskSpec(
        title="mission-once",
        trigger=TriggerOnEvent(event_name="MissionCompleted", filter_expr=None),
        action=SpeakAction(text="x"),
    )
    await scheduler1.schedule(spec)
    event = MissionCompleted(mission_id="mission-42", status="approved")
    await bus1.publish(event)
    assert runner1.dispatched == [str(spec.id)]
    await store1.close()

    bus2 = EventBus()
    store2 = TaskStore(db)
    await store2.init()
    runner2 = FakeRunner()
    scheduler2 = TaskScheduler(store=store2, bus=bus2, runner=runner2)
    try:
        await scheduler2.hydrate()
        scheduler2.bind_bus()
        await bus2.publish(event)
        assert runner2.dispatched == []
    finally:
        await store2.close()


async def test_hook_delivery_claim_allows_only_one_concurrent_runner(
    store: TaskStore, bus: EventBus, runner: FakeRunner
) -> None:
    scheduler = TaskScheduler(store=store, bus=bus, runner=runner)
    spec = TaskSpec(
        title="hook-once",
        trigger=TriggerWebhook(conditions={}),
        action=SpeakAction(text="x"),
    )
    tid = await scheduler.schedule(spec)
    assert await scheduler.receive_hook(tid, {"value": 1}, "delivery-1") == "queued"
    rows = await store.hooks.pending()
    assert len(rows) == 1

    await asyncio.gather(scheduler._run_hook(rows[0]), scheduler._run_hook(rows[0]))

    assert runner.dispatched == [tid]
    row = await store.hooks._one(
        "SELECT status FROM task_hook_deliveries WHERE task_id=? AND delivery_id=?",
        (tid, "delivery-1"),
    )
    assert row is not None
    assert row[0] == "done"


async def test_on_event_filter_expr_blocks_non_match(
    store: TaskStore, bus: EventBus, runner: FakeRunner
) -> None:
    scheduler = TaskScheduler(store=store, bus=bus, runner=runner)
    scheduler.bind_bus()

    spec = TaskSpec(
        title="email-user",
        trigger=TriggerOnEvent(event_name="MessageSent", filter_expr="role == 'user'"),
        action=SpeakAction(text="x"),
    )
    await scheduler.schedule(spec)

    # assistant message → should NOT be dispatched
    await bus.publish(MessageSent(thread_id="t1", role="assistant", text="hi"))
    assert runner.dispatched == []

    # user-Message → dispatch
    await bus.publish(MessageSent(thread_id="t1", role="user", text="hi"))
    assert runner.dispatched == [str(spec.id)]


# ----------------------------------------------------------------------
# cancel
# ----------------------------------------------------------------------

async def test_cancel_before_fire_prevents_run(
    store: TaskStore, bus: EventBus, runner: FakeRunner
) -> None:
    scheduler = TaskScheduler(store=store, bus=bus, runner=runner)
    spec = TaskSpec(
        title="lang",
        trigger=TriggerAfterDelay(delay_seconds=10.0),
        action=SpeakAction(text="x"),
    )
    token = CancelToken()
    loop_task = asyncio.create_task(scheduler.run(token))
    tid = await scheduler.schedule(spec)

    # Kurz warten, dann cancellen
    await asyncio.sleep(0.05)
    ok = await scheduler.cancel_task(tid)
    assert ok is True

    # Wait briefly, should NOT be dispatched
    await asyncio.sleep(0.2)
    assert runner.dispatched == []

    row = await store.get(tid)
    assert row is not None
    assert row["state"] == "cancelled"

    token.cancel("test_done")
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass


async def test_hydrate_restores_scheduled_tasks(
    tmp_path: Path, bus: EventBus, runner: FakeRunner
) -> None:
    db = tmp_path / "hydrate.db"
    # Setup: store with one scheduled task
    store1 = TaskStore(db)
    await store1.init()
    spec = TaskSpec(
        title="survive",
        trigger=TriggerAfterDelay(delay_seconds=0.1),
        action=SpeakAction(text="x"),
    )
    await store1.insert(spec)
    await store1.close()

    # Neuer Store + Scheduler — simulierter App-Neustart
    store2 = TaskStore(db)
    await store2.init()
    try:
        scheduler = TaskScheduler(store=store2, bus=bus, runner=runner)
        await scheduler.hydrate()

        token = CancelToken()
        loop_task = asyncio.create_task(scheduler.run(token))
        try:
            await asyncio.wait_for(runner.gate.wait(), timeout=1.0)
        finally:
            token.cancel("test_done")
            loop_task.cancel()
            try:
                await loop_task
            except asyncio.CancelledError:
                pass
        assert runner.dispatched == [str(spec.id)]
    finally:
        await store2.close()


# ----------------------------------------------------------------------
# Filter-Expression — sicherer AST-Subset
# ----------------------------------------------------------------------

def test_filter_expr_rejects_dangerous_input() -> None:
    evt = MessageSent(thread_id="t", role="user", text="hi")

    # None / empty → always true
    assert _match_filter(evt, None) is True
    assert _match_filter(evt, "") is True

    # Function calls are not allowed
    assert _match_filter(evt, "__import__('os').system('dir')") is False

    # Attribute access is not allowed
    assert _match_filter(evt, "role.upper() == 'USER'") is False

    # Einfache Vergleiche funktionieren
    assert _match_filter(evt, "role == 'user'") is True
    assert _match_filter(evt, "role == 'assistant'") is False
    assert _match_filter(evt, "role == 'user' and text == 'hi'") is True
    assert _match_filter(evt, "role == 'user' or text == 'bye'") is True
    assert _match_filter(evt, "not role == 'admin'") is True


# ----------------------------------------------------------------------
# Running-task cancellation (deep-dive 2026-07-15, H-03)
# ----------------------------------------------------------------------

async def test_pause_race_does_not_remove_running_task(
    store: TaskStore, bus: EventBus, runner: FakeRunner
) -> None:
    scheduler = TaskScheduler(store=store, bus=bus, runner=runner)
    spec = TaskSpec(
        title="pause-race",
        trigger=TriggerEvery(interval_seconds=60),
        action=SpeakAction(text="x"),
    )
    tid = await scheduler.schedule(spec)
    assert tid
    task = await store.get(tid)
    assert task is not None
    assert await store.update_state(tid, "running", expected_state="scheduled")
    with pytest.raises(TaskStateConflict):
        await scheduler.pause(tid)
    row = await store.get(tid)
    assert row is not None
    assert row["state"] == "running"


async def test_cancel_task_fires_the_running_runs_token(
    store: TaskStore, bus: EventBus
) -> None:
    """cancel_task() on a RUNNING task must fire that run's cancel token —
    production used to pass no token at all, so a running harness action
    (e.g. a Computer-Use mission) was unstoppable per-task."""

    class BlockingRunner:
        def __init__(self) -> None:
            self.token: Any = None
            self.started = asyncio.Event()

        async def run(self, task_id: str, cancel_token: Any = None, **_kw: Any) -> None:
            self.token = cancel_token
            self.started.set()
            # Behave like the real runner: wait until cancelled.
            await cancel_token.wait_until_cancelled()

    blocking = BlockingRunner()
    scheduler = TaskScheduler(store=store, bus=bus, runner=blocking)

    spec = TaskSpec(
        title="long harness run",
        trigger=TriggerAfterDelay(delay_seconds=0.01),
        action=SpeakAction(text="x"),
    )
    tid = await scheduler.schedule(spec)
    await scheduler._dispatch_runner(tid)
    await asyncio.wait_for(blocking.started.wait(), timeout=2.0)

    assert blocking.token is not None
    assert not blocking.token.is_cancelled()

    ok = await scheduler.cancel_task(tid, reason="user_cancel")
    assert ok is True
    assert blocking.token.is_cancelled()
    assert blocking.token.reason == "user_cancel"
    await scheduler.shutdown()
