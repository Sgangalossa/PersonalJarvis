"""Secret-derived diagnostics must remain value-free."""

from __future__ import annotations

import pytest

from jarvis.brain import manager
from jarvis.brain.manager import BrainManager
from jarvis.core.events import SecretConfigured


def test_keyless_probe_failure_logs_no_secret_tainted_metadata(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from jarvis.brain import app_control

    def _fail(_provider: str) -> bool:
        raise RuntimeError("token=do-not-log-this")

    monkeypatch.setattr(app_control, "_keyless_credential_present", _fail)
    caplog.set_level("DEBUG", logger="jarvis.brain.manager")

    assert not manager._keyless_provider_is_rescued_by_oauth("vertex")
    assert "Keyless-credential rescue probe failed" in caplog.text
    assert "token=do-not-log-this" not in caplog.text
    assert "vertex" not in caplog.text
    assert "RuntimeError" not in caplog.text


@pytest.mark.asyncio
async def test_key_set_auto_activate_failure_logs_no_secret_tainted_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _Bus:
        def __init__(self) -> None:
            self.callbacks: dict[type[object], object] = {}

        def subscribe(self, event_type: type[object], callback: object) -> None:
            self.callbacks[event_type] = callback

    subject = BrainManager.__new__(BrainManager)
    subject._bus = None
    subject._active_name = "claude-api"
    subject.reactivate_provider = lambda _provider: None
    subject._active_has_usable_credential = lambda: False

    async def _fail_switch(_provider: str, *, persist: bool) -> None:
        assert persist
        raise RuntimeError("token=do-not-log-this")

    subject.switch = _fail_switch
    bus = _Bus()
    subject.attach_to_bus(bus)
    caplog.set_level("WARNING", logger="jarvis.brain.manager")

    callback = bus.callbacks[SecretConfigured]
    await callback(SecretConfigured(key="openai_api_key", action="set"))

    assert "auto-activate on key-set failed" in caplog.text
    assert "token=do-not-log-this" not in caplog.text
    assert "openai" not in caplog.text
    assert "RuntimeError" not in caplog.text
