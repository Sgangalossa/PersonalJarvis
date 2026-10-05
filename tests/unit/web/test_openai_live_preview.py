"""OpenAI GPT-Live voice preview uses the Live transport."""

from __future__ import annotations

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from jarvis.core.config import JarvisConfig
from jarvis.ui.web import provider_routes


def test_openai_live_preview_uses_live_sampler(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(provider_routes.router)
    app.state.config = JarvisConfig()

    calls = []

    async def fake_sampler(api_key: str, *, model: str, voice: str, text: str, language: str):
        calls.append((api_key, model, voice, text, language))
        return b"\x01\x00\x02\x00", 24_000

    monkeypatch.setattr(provider_routes.cfg_mod, "get_provider_secret", lambda provider: "sk-test")
    monkeypatch.setitem(
        provider_routes._REALTIME_PREVIEW_SAMPLERS,
        "openai-live",
        fake_sampler,
    )

    client = TestClient(app)
    response = client.post(
        "/api/providers/openai-live/realtime-voice-preview",
        json={"model": "gpt-live-1", "voice": "marin", "language": "en"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert calls and calls[0][0] == "sk-test"
    assert calls[0][1:3] == ("gpt-live-1", "marin")


def test_openai_live_options_report_preview_available(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(provider_routes.router)
    app.state.config = JarvisConfig()
    monkeypatch.setattr(provider_routes.cfg_mod, "get_provider_secret", lambda provider: "sk-test")

    client = TestClient(app)
    response = client.get("/api/providers/openai-live/realtime-options")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "openai-live"
    assert body["models"][0]["id"] == "gpt-live-1"
    assert body["voices"][0]["id"] == "marin"
    assert body["preview_available"] is True


@pytest.mark.asyncio
async def test_openai_live_preview_fails_closed_on_early_session_close(monkeypatch) -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.closed = False
            self.sent: list[dict] = []
            self._events = iter(
                [
                    {"type": "session.started"},
                    {"type": "session.closed"},
                ]
            )

        async def receive(self) -> dict:
            return next(self._events)

        async def send(self, event: dict) -> None:
            self.sent.append(event)

        async def close(self) -> None:
            self.closed = True

    connection = FakeConnection()

    class FakeProvider:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "sk-test"

        async def open_session(self, _start) -> FakeConnection:
            return connection

    from jarvis.plugins.realtime import openai_live

    monkeypatch.setattr(openai_live, "OpenAILiveProvider", FakeProvider)

    with pytest.raises(RuntimeError, match="closed before the preview response completed"):
        await provider_routes._openai_live_voice_sample(
            "sk-test",
            model="gpt-live-1",
            voice="marin",
            text="Test preview",
            language="en",
        )

    assert connection.closed is True
    assert connection.sent[0]["type"] == "response.item.create"
    assert connection.sent[1]["type"] == "response.create"
