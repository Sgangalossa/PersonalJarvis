"""Regression tests for account-only CLI usage rebinds."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from jarvis.costs.cli_usage_index import entries, refresh


def _write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("\\n".join(lines) + "\\n").encode("utf-8"))


def _claude_line(*, uuid: str, msg_id: str) -> str:
    return json.dumps({
        "type": "assistant",
        "uuid": uuid,
        "requestId": f"req_{msg_id}",
        "sessionId": "sess-1",
        "timestamp": "2026-08-23T17:16:09.424Z",
        "cwd": "/work/personal-jarvis",
        "message": {
            "id": msg_id,
            "model": "claude-opus-5",
            "usage": {
                "input_tokens": 10,
                "cache_creation_input_tokens": 5,
                "cache_read_input_tokens": 7,
                "output_tokens": 20,
                "output_tokens_details": {"thinking_tokens": 8},
            },
        },
    })


def _claude_path(home: Path) -> Path:
    return home / ".claude" / "projects" / "-work-personal-jarvis" / "sess-1.jsonl"


def _all(data_dir: Path) -> list:
    return list(entries(data_dir=data_dir, since_ms=0, until_ms=2**62))


def test_account_rebind_does_not_rescan_unchanged_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    home = tmp_path / "home"
    _write(_claude_path(home), [_claude_line(uuid="u1", msg_id="msg_a")])

    monkeypatch.setattr(
        "jarvis.costs.cli_usage_index._account_id_for_root",
        lambda agent, root: "claude:first",
    )
    refresh(data_dir=data, home=home)

    monkeypatch.setattr(
        "jarvis.costs.cli_usage_index._account_id_for_root",
        lambda agent, root: "claude:second",
    )

    def fail_scan(*_args, **_kwargs):
        pytest.fail("account-only refresh must not rescan an unchanged transcript")

    monkeypatch.setattr("jarvis.costs.cli_usage_index._scan", fail_scan)
    refresh(data_dir=data, home=home)

    (turn,) = _all(data)
    assert turn.account_id == "claude:second"
