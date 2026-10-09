"""Regression tests for secret-safe output from the telephony provisioning CLI."""

from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest

import scripts.telephony_provision as cli


@pytest.mark.parametrize("command", ["buy", "set_webhook", "inspect"])
def test_provisioning_output_omits_private_resource_data(command, monkeypatch, capsys):
    private_values = (
        "+49301234567",
        "PN123456789",
        "supersecretvalue123",
        "jarvis.example.com",
    )
    owned = SimpleNamespace(
        phone_number=private_values[0],
        sid=private_values[1],
        voice_url=(
            "https://jarvis.example.com/api/telephony/voice?"
            f"token={private_values[2]}"
        ),
    )
    monkeypatch.setattr(cli, "_resolve_credentials", lambda _args: ("AC123", "auth-token"))
    monkeypatch.setattr(cli.provisioning, "buy_number", lambda *a, **k: owned)
    monkeypatch.setattr(cli.provisioning, "set_voice_webhook", lambda *a, **k: owned)
    monkeypatch.setattr(cli.provisioning, "inspect_number", lambda *a, **k: owned)

    args = Namespace(number=owned.phone_number, url=owned.voice_url)
    getattr(cli, f"_cmd_{command}")(args)

    output = capsys.readouterr().out
    assert all(private not in output for private in private_values)
    assert "requested number" in output


def test_missing_number_output_omits_requested_number(monkeypatch, capsys):
    number = "+49301234567"
    monkeypatch.setattr(cli, "_resolve_credentials", lambda _args: ("AC123", "auth-token"))
    monkeypatch.setattr(cli.provisioning, "inspect_number", lambda *a, **k: None)

    assert cli._cmd_inspect(Namespace(number=number)) == 1

    output = capsys.readouterr().out
    assert number not in output
    assert output == "The requested number is not owned by this account.\n"
