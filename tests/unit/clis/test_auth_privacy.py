from __future__ import annotations

import logging

import pytest

from jarvis.clis.auth import CliAuthManager
from jarvis.clis.spec import AuthConfig, CliSpec, InstallMethods, RiskConfig


def _api_key_spec() -> CliSpec:
    return CliSpec(
        name="private-cli",
        display_name="Private CLI",
        description="privacy regression",
        homepage="",
        binary_name="private-cli",
        check_command=("private-cli", "--version"),
        version_parse_regex=r"(\d+)",
        install=InstallMethods(manual_url="https://example.invalid"),
        auth=AuthConfig(
            type="api_key",
            secret_keys=("expected_key",),
            env_vars=("EXPECTED_KEY",),
        ),
        risk=RiskConfig(),
    )


@pytest.mark.asyncio
async def test_unexpected_secret_field_is_not_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    stored: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "jarvis.clis.auth.set_secret",
        lambda key, value: stored.append((key, value)) or True,
    )
    crafted_field = "token=field-secret"
    crafted_value = "value-secret"

    with caplog.at_level(logging.WARNING, logger="jarvis.clis.auth"):
        ok, error = await CliAuthManager().connect_api_key(
            _api_key_spec(),
            {"expected_key": "expected-value", crafted_field: crafted_value},
            validate=False,
        )

    assert ok is True
    assert error is None
    assert stored == [("expected_key", "expected-value")]
    assert crafted_field not in caplog.text
    assert crafted_value not in caplog.text
