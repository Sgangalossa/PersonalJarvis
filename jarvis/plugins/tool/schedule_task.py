"""Brain tool for creating a durable time-based reminder.

This is a narrow bridge into the existing Tasks subsystem. TaskScheduler.schedule
remains the single source of truth for persistence, heap registration and wakeup.
The tool creates an AgentAction task with a deterministic success announcement
so the reminder can reach the user after the original voice/chat turn ends.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from jarvis.core import runtime_refs
from jarvis.core.protocols import ExecutionContext, ToolResult
from jarvis.tasks.schema import AgentAction, TaskSpec, TriggerAfterDelay, TriggerAtTime

log = logging.getLogger(__name__)


class ScheduleTaskTool:
    """Create one durable reminder for the user."""

    name: ClassVar[str] = "schedule-task"
    risk_tier: ClassVar[str] = "monitor"
    description: ClassVar[str] = (
        "Create a durable reminder that runs later. Use for requests such as "
        "remind me in 2 hours or remind me tomorrow at 09:00. Give the exact "
        "short text the user should be reminded of. This creates a real Tasks "
        "entry that survives restart; do not claim a reminder was created "
        "without a successful tool result. Use exactly one of delay_seconds "
        "or at_time. at_time must be ISO-8601 and should include a timezone "
        "offset when the user supplied a local wall-clock time."
    )
    schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "minLength": 1,
                "maxLength": 256,
                "description": "Short recognizable task/reminder title.",
            },
            "reminder_text": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2048,
                "description": "Exact short text to deliver when the reminder runs.",
            },
            "delay_seconds": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 2592000,
                "description": "Seconds from now. Use for in-N-minutes/hours/days requests.",
            },
            "at_time": {
                "type": "string",
                "minLength": 10,
                "maxLength": 40,
                "description": "ISO-8601 due time, preferably with an explicit timezone offset.",
            },
        },
        "required": ["title", "reminder_text"],
        "additionalProperties": False,
        "strict": True,
        "input_examples": [
            {
                "title": "Call the dentist",
                "reminder_text": "Remember to call the dentist.",
                "delay_seconds": 7200,
            },
            {
                "title": "Morning reminder",
                "reminder_text": "Take the documents with you.",
                "at_time": "2026-10-06T09:00:00+02:00",
            },
        ],
    }

    async def execute(self, args: dict[str, Any], ctx: ExecutionContext) -> ToolResult:
        """Validate the public contract, then hand the TaskSpec to the live scheduler."""
        trace_id = str(ctx.trace_id)
        if not isinstance(args, dict):
            return ToolResult(False, None, "invalid_input: args must be an object")

        title = args.get("title")
        reminder = args.get("reminder_text")
        if not isinstance(title, str) or not title.strip():
            return ToolResult(False, None, "invalid_input: title is required")
        if len(title.strip()) > 256:
            return ToolResult(False, None, "invalid_input: title exceeds 256 characters")
        if not isinstance(reminder, str) or not reminder.strip():
            return ToolResult(False, None, "invalid_input: reminder_text is required")
        if len(reminder.strip()) > 2048:
            return ToolResult(False, None, "invalid_input: reminder_text exceeds 2048 characters")

        has_delay = "delay_seconds" in args and args.get("delay_seconds") is not None
        has_at = "at_time" in args and args.get("at_time") is not None
        if has_delay == has_at:
            return ToolResult(
                False,
                None,
                "invalid_input: provide exactly one of delay_seconds or at_time",
            )

        if has_delay:
            delay = args["delay_seconds"]
            if isinstance(delay, bool) or not isinstance(delay, (int, float)):
                return ToolResult(False, None, "invalid_input: delay_seconds must be a number")
            if delay <= 0 or delay > 30 * 24 * 3600:
                return ToolResult(
                    False,
                    None,
                    "invalid_input: delay_seconds must be > 0 and <= 2592000",
                )
            trigger = TriggerAfterDelay(delay_seconds=float(delay))
        else:
            at_time = args["at_time"]
            if not isinstance(at_time, str) or not at_time.strip():
                return ToolResult(False, None, "invalid_input: at_time must be a string")
            try:
                trigger = TriggerAtTime(iso_timestamp=at_time.strip())
                from jarvis.tasks.scheduler import parse_iso_timestamp_to_ns

                due_ns = parse_iso_timestamp_to_ns(trigger.iso_timestamp)
                if due_ns <= 0:
                    raise ValueError("timestamp is before the Unix epoch")
            except (TypeError, ValueError) as exc:
                return ToolResult(False, None, f"invalid_input: invalid ISO timestamp: {exc}")

        app = runtime_refs.get_web_app()
        scheduler = getattr(getattr(app, "state", None), "task_scheduler", None)
        if scheduler is None or not callable(getattr(scheduler, "schedule", None)):
            return ToolResult(
                False,
                None,
                "scheduler_unavailable: the Tasks scheduler is not ready",
            )

        spec = TaskSpec(
            title=title.strip(),
            trigger=trigger,
            action=AgentAction(
                prompt=(
                    "This is a scheduled reminder. Reply with exactly this reminder text "
                    "and nothing else:\n\n" + reminder.strip()
                ),
                model_tier="fast",
            ),
            created_by="brain",
            tags=("reminder",),
            announce_on_success=reminder.strip(),
        )

        try:
            task_id = await scheduler.schedule(spec, trace_id=trace_id)
        except Exception as exc:  # noqa: BLE001 - scheduler owns persistence/validation
            log.warning("schedule-task: scheduler rejected reminder %r", spec.title, exc_info=True)
            return ToolResult(
                False,
                {"title": spec.title},
                f"schedule_failed: {type(exc).__name__}: {exc}",
            )

        due_at_ns = None
        store = getattr(getattr(app, "state", None), "task_store", None)
        if store is not None and callable(getattr(store, "get", None)):
            try:
                row = await store.get(task_id)
                due_at_ns = (row or {}).get("due_at_ns")
            except Exception:
                log.debug("schedule-task: could not read persisted due time for %s", task_id, exc_info=True)
                due_at_ns = None

        return ToolResult(
            True,
            {
                "task_id": task_id,
                "title": spec.title,
                "trigger": spec.trigger.model_dump(mode="json"),
                "due_at_ns": due_at_ns,
                "created_by": spec.created_by,
                "summary": f"Scheduled reminder: {spec.title}",
            },
            None,
        )


__all__ = ["ScheduleTaskTool"]
