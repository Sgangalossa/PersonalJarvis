"""SocietyBus: observer isolation and timeout cleanup."""

from __future__ import annotations

import asyncio

import pytest

from jarvis.society import bus as bus_module
from jarvis.society.bus import SocietyBus
from jarvis.society.events import MsgType, SocietyEnvelope


def _event() -> SocietyEnvelope:
    return SocietyEnvelope(
        msg_type=MsgType.SAY,
        from_agent="scout",
        to_agent="jarvis",
        trace_id="trace",
        payload={"text": "hello"},
    )


@pytest.mark.asyncio
async def test_timed_out_observer_is_unsubscribed(monkeypatch):
    monkeypatch.setattr(bus_module, "_HANDLER_TIMEOUT_S", 0.01)
    bus = SocietyBus()

    async def stuck(_env: SocietyEnvelope) -> None:
        await asyncio.Event().wait()

    bus.subscribe_all(stuck)
    await bus.publish(_event())

    assert bus.active_subs == 0
    # A later append must not start another doomed task for the abandoned observer.
    await bus.publish(_event())
    assert bus.active_subs == 0
