"""Regression tests for secret-safe output from the telephony provisioning CLI."""

from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest

import scripts.telephony_provision as cli


@pytest.mark.parametrize("command", ["buy", "set_webhook", "inspect"])
def test_webhook_query_secrets_are_redacted_from_output(command, monkeypatch, capsys):
    secret = "supersecretvalue123"
    owned = SimpleNamespace(
        phone_number="+49301234567",
        sid="PN123456789",
        voice_url=f"https://jarvis.example.com/api/telephony/voice?token={secret}",
    )
    monkeypatch.setattr(cli, "_resolve_credentials", lambda _args: ("AC123", "auth-token"))
    monkeypatch.setattr(cli.provisioning, "buy_number", lambda *a, **k: owned)
    monkeypatch.setattr(cli.provisioning, "set_voice_webhook", lambda *a, **k: owned)
    monkeypatch.setattr(cli.provisioning, "inspect_number", lambda *a, **k: owned)

    args = Namespace(number=owned.phone_number, url="https://jarvis.example.com/api/telephony/voice")
    getattr(cli, f"_cmd_{command}")(args)

    output = capsys.readouterr().out
    assert secret not in output
    assert "token=<redacted:query_secret>" in output
