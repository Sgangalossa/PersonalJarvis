"""Room turns use the restricted chat contract."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from jarvis.society import chat_binding
from jarvis.society.runtime import SocietyRuntime


class _FakeStore:
    def incoming_message(self, session_id: str, message_id: str):
        return None


class _FakeService:
    supports_turn_completion = True

    def __init__(self) -> None:
        self.store = _FakeStore()
        self.sent: dict[str, object] = {}
        self.queue = object()

    def is_running(self, session_id: str) -> bool:
        return False

    def subscribe(self, session_id: str):
        return self.queue

    def unsubscribe(self, session_id: str, queue: object) -> None:
        return None

    async def send(self, session_id: str, text: str, *, incoming, direct_user, read_only):
        self.sent = {
            "session_id": session_id,
            "text": text,
            "incoming": incoming,
            "direct_user": direct_user,
            "read_only": read_only,
        }
        return "turn-1"


class _FakeRooms:
    def __init__(self) -> None:
        self.bound: tuple[str, str, str] | None = None

    async def bind_turn(self, room_id: str, claim_id: str, turn_id: str):
        self.bound = (room_id, claim_id, turn_id)


@pytest.mark.asyncio
async def test_room_dispatch_forces_read_only_chat_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = SocietyRuntime.__new__(SocietyRuntime)
    service = _FakeService()
    rooms = _FakeRooms()
    runtime._get_chat = lambda: service
    runtime._get_cfg = lambda: None
    runtime._watchers = set()
    runtime.rooms = rooms

    def fake_ensure_session(svc, cfg, target):
        return SimpleNamespace(session_id="society:scout")

    async def fake_room_prompt(room, target):
        return "bounded prompt"

    async def fake_watch(*_args):
        return None

    monkeypatch.setattr(chat_binding, "ensure_session", fake_ensure_session)
    monkeypatch.setattr(runtime, "_room_prompt", fake_room_prompt)
    monkeypatch.setattr(runtime, "_watch_room_turn", fake_watch)

    target = SimpleNamespace(agent_id="scout", name="Scout", session_id="society:scout")
    room = SimpleNamespace(
        room_id="room-1",
        opened_by="jarvis",
        topic="Discuss the plan.",
        trace_id="room:room-1",
    )

    result = await runtime._dispatch_room_turn(target, room, "claim-1")
    await asyncio.sleep(0)

    assert result == "room:room-1:turn-1"
    assert service.sent["read_only"] is True
    assert service.sent["direct_user"] is False
    incoming = service.sent["incoming"]
    assert incoming.message_id == "claim-1"
    assert incoming.trace_id == "room:room-1"
    assert rooms.bound == ("room-1", "claim-1", "turn-1")


@pytest.mark.asyncio
async def test_room_settlement_projects_exact_open_receipt_and_trace(monkeypatch) -> None:
    runtime = SocietyRuntime.__new__(SocietyRuntime)
    notices: list[tuple[str, dict[str, object]]] = []
    attention_calls: list[dict[str, object]] = []

    class _Store:
        def __init__(self) -> None:
            self.notice_events: list[dict[str, object]] = []

        async def events_for_trace(self, trace_id: str):
            return [
                SimpleNamespace(
                    msg_type=runtime_msg_type("ROOM_OPEN"),
                    event_id="room-open-42",
                    trace_id=trace_id,
                    from_agent="jarvis",
                    to_agent=None,
                    text="Discuss the release.",
                    payload={
                        "live": True,
                        "members": ["scout", "archivist"],
                        "reply_policy": "always",
                        "reply_surface": "chat",
                        "reply_session_id": "jarvis-session-7",
                        "room_id": "room-42",
                    },
                ),
                SimpleNamespace(
                    msg_type=runtime_msg_type("SAY"),
                    event_id="say-1",
                    trace_id=trace_id,
                    from_agent="scout",
                    to_agent=None,
                    text="The release is ready.",
                    payload={},
                ),
            ]

        def list_sessions(self, *, limit: int, surface: str):
            return []

        def list_events(self, session_id: str):
            return list(self.notice_events)

        def get_session(self, session_id: str):
            return SimpleNamespace(session_id=session_id, surface="jarvis")

    chat_store = _Store()

    class _Chat:
        store = chat_store

        async def post_notice_once(
            self, session_id: str, payload: dict[str, object], *, dedupe_key: str
        ) -> bool:
            if chat_store.notice_events:
                return False
            notices.append((session_id, payload))
            persisted = dict(payload)
            persisted["_dedupe_key"] = dedupe_key
            chat_store.notice_events.append({"kind": "notice", "payload": persisted})
            return True

    def runtime_msg_type(name: str):
        from jarvis.society.events import MsgType
        return getattr(MsgType, name)

    runtime.store = _Store()
    async def _get_agent(agent_id: str):
        return _agent(agent_id)

    runtime.roster = SimpleNamespace(get=_get_agent)
    runtime._get_chat = lambda: _Chat()
    runtime._publish_event = None

    async def _attention(**kwargs):
        attention_calls.append(kwargs)

    monkeypatch.setattr(runtime, "publish_attention", _attention)

    def _agent(agent_id: str):
        return SimpleNamespace(name={"scout": "Scout", "archivist": "Archivist"}[agent_id])

    from jarvis.society.events import MsgType, SocietyEnvelope

    settlement = SocietyEnvelope(
        msg_type=MsgType.ROOM_SETTLE,
        from_agent="scheduler",
        to_agent=None,
        trace_id="room-trace-42",
        event_id="room-settle-42",
        payload={"room_id": "room-42", "reason": "round_cap"},
    )
    await runtime._room_settled(settlement)
    # Simulate an upgrade restart replaying the exact durable terminal event
    # against the legacy notice persisted by the first call.
    await runtime._room_settled(settlement)

    assert len(notices) == 1
    assert len(attention_calls) == 2
    session_id, payload = notices[0]
    assert session_id == "jarvis-session-7"
    assert payload["kind"] == "society_room_result"
    assert payload["room_id"] == "room-42"
    assert payload["trace_id"] == "room-trace-42"
    assert payload["room_open_id"] == "room-open-42"
    assert payload["settle_event_id"] == settlement.event_id
    assert payload["agent_ids"] == ["scout", "archivist"]
    assert "Scout: The release is ready." in payload["report"]


@pytest.mark.asyncio
async def test_result_recovery_replays_missing_notice_without_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = SocietyRuntime.__new__(SocietyRuntime)
    from jarvis.society.events import MsgType, SocietyEnvelope

    request = SocietyEnvelope(
        msg_type=MsgType.ASSIGN,
        from_agent="jarvis",
        to_agent="scout",
        trace_id="trace-recover",
        event_id="assign-1",
        payload={"text": "Check the release.", "reply_policy": "always"},
    )
    result = SocietyEnvelope(
        msg_type=MsgType.RESULT,
        from_agent="scout",
        to_agent="jarvis",
        trace_id="trace-recover",
        parent_event_id="assign-1",
        event_id="result-1",
        payload={"run_id": "run-1", "status": "done", "done": "Release checked.", "output": ["report"]},
    )

    class _Store:
        async def events_since(self, seq: int, *, limit: int):
            return [request, result] if seq == 0 else []

    class _ChatStore:
        def get_session(self, session_id: str):
            return SimpleNamespace(session_id=session_id, surface="jarvis")

        def list_sessions(self, *, limit: int, surface: str):
            return [SimpleNamespace(session_id="jarvis-session")]

    class _Chat:
        def __init__(self) -> None:
            self.store = _ChatStore()
            self.notices: list[dict[str, object]] = []

        async def post_notice_once(self, session_id: str, payload: dict[str, object], *, dedupe_key: str) -> bool:
            if any(item["dedupe_key"] == dedupe_key for item in self.notices):
                return False
            self.notices.append({"session_id": session_id, "payload": payload, "dedupe_key": dedupe_key})
            return True

    chat = _Chat()
    runtime.store = _Store()
    runtime.roster = SimpleNamespace(get=lambda agent_id: _agent(agent_id))
    runtime._get_chat = lambda: chat
    runtime._publish_event = None
    attention_calls: list[dict[str, object]] = []

    async def _attention(**kwargs):
        attention_calls.append(kwargs)

    monkeypatch.setattr(runtime, "publish_attention", _attention)

    async def _agent(agent_id: str):
        return SimpleNamespace(agent_id=agent_id, name="Scout", session_id="society:scout")

    await runtime.recover_result_reports()
    await runtime.recover_result_reports()

    assert len(chat.notices) == 1
    assert chat.notices[0]["dedupe_key"] == "society_result:assign-1"
    assert len(attention_calls) == 2
