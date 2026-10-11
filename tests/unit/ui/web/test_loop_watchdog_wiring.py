"""The WebServer owns the off-loop event-loop watchdog lifecycle."""

from __future__ import annotations

import asyncio

from jarvis.ui.web.server import WebServer


class _FakeWatchdog:
    instances: list["_FakeWatchdog"] = []

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.starts = 0
        self.stops = 0
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> None:
        self.stops += 1


def test_web_server_starts_and_stops_one_watchdog(monkeypatch) -> None:
    monkeypatch.setattr("jarvis.core.loop_watchdog.EventLoopWatchdog", _FakeWatchdog)
    _FakeWatchdog.instances.clear()

    server = WebServer.__new__(WebServer)
    server._loop_watchdog = None

    loop = asyncio.new_event_loop()
    try:
        server._start_loop_watchdog(loop)
        server._start_loop_watchdog(loop)

        assert len(_FakeWatchdog.instances) == 1
        watchdog = _FakeWatchdog.instances[0]
        assert watchdog.loop is loop
        assert watchdog.starts == 1

        server._stop_loop_watchdog()
        server._stop_loop_watchdog()

        assert watchdog.stops == 1
        assert server._loop_watchdog is None
    finally:
        loop.close()
