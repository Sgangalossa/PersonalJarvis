"""Tests for the durable Brain reminder scheduler tool."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.plugins.tool.schedule_task import ScheduleTaskTool


class _FakeScheduler:
    def __init__(self) -> None:
        self.spec = None

    async def schedule(self, spec):
        self.spec = spec
        return "task-123"


def _app(scheduler=None):
    return SimpleNamespace(
        state=SimpleNamespace(
            task_scheduler=scheduler,
            task_store=None,
        )
    )


@pytest.mark.asyncio
async def test_schedule_after_delay_creates_durable_agent_task(monkeypatch: pytest.MonkeyPatch):
    scheduler = _FakeScheduler()
    monkeypatch.setattr(
        "jarvis.core.runtime_refs.get_web_app",
        lambda: _app(scheduler),
    )

    result = await ScheduleTaskTool().execute(
        {
            "title": "Call the dentist",
            "reminder_text": "Remember to call the dentist.",
            "delay_seconds": 7200,
        },
        SimpleNamespace(),
    )

    assert result.success is True
    assert result.output["task_id"] == "task-123"
    assert result.output["created_by"] == "brain"
    assert scheduler.spec is not None
    assert scheduler.spec.trigger.type == "after_delay"
    assert scheduler.spec.trigger.delay_seconds == 7200
    assert scheduler.spec.action.kind == "agent"
    assert scheduler.spec.action.model_tier == "fast"
    assert scheduler.spec.announce_on_success == "Remember to call the dentist."


@pytest.mark.asyncio
async def test_schedule_at_time_keeps_explicit_timezone(monkeypatch: pytest.MonkeyPatch):
    scheduler = _FakeScheduler()
    monkeypatch.setattr(
        "jarvis.core.runtime_refs.get_web_app",
        lambda: _app(scheduler),
    )

    result = await ScheduleTaskTool().execute(
        {
            "title": "Morning reminder",
            "reminder_text": "Take the documents with you.",
            "at_time": "2026-10-06T09:00:00+02:00",
        },
        SimpleNamespace(),
    )

    assert result.success is True
    assert scheduler.spec.trigger.type == "at_time"
    assert scheduler.spec.trigger.iso_timestamp == "2026-10-06T09:00:00+02:00"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        {
            "title": "Invalid",
            "reminder_text": "text",
        },
        {
            "title": "Invalid",
            "reminder_text": "text",
            "delay_seconds": 60,
            "at_time": "2026-10-06T09:00:00+02:00",
        },
        {
            "title": "Invalid",
            "reminder_text": "text",
            "delay_seconds": 0,
        },
    ],
)
async def test_invalid_schedule_inputs_are_rejected_without_scheduler(
    monkeypatch: pytest.MonkeyPatch, args: dict[str, object]
):
    scheduler = _FakeScheduler()
    monkeypatch.setattr(
        "jarvis.core.runtime_refs.get_web_app",
        lambda: _app(scheduler),
    )

    result = await ScheduleTaskTool().execute(args, SimpleNamespace())

    assert result.success is False
    assert result.error.startswith("invalid_input:")
    assert scheduler.spec is None


@pytest.mark.asyncio
async def test_scheduler_unavailable_fails_closed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "jarvis.core.runtime_refs.get_web_app",
        lambda: _app(None),
    )

    result = await ScheduleTaskTool().execute(
        {
            "title": "Call the dentist",
            "reminder_text": "Remember to call the dentist.",
            "delay_seconds": 60,
        },
        SimpleNamespace(),
    )

    assert result.success is False
    assert result.error.startswith("scheduler_unavailable:")
