"""Self-hosted services live at an address only the user knows.

People type that address the way they see it in their browser: with a trailing
slash, with whatever page they were on, sometimes without a scheme. All of those
are the same server, and none of them should fail a connection.
"""

from __future__ import annotations

import pytest

from jarvis.marketplace import instance_url as instance_urls
from jarvis.marketplace.instance_url import (
    InstanceUrlError,
    normalize_instance_url,
    validate_instance_destination,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://ha.example.test", "https://ha.example.test"),
        ("https://ha.example.test/", "https://ha.example.test"),
        ("  https://ha.example.test/  ", "https://ha.example.test"),
        # Copied from the address bar while on some page of the app.
        ("https://ha.example.test/lovelace/0", "https://ha.example.test"),
        ("https://ha.example.test/profile?foo=1#bar", "https://ha.example.test"),
        # Explicit http for a LAN box stays http — never silently upgraded, or
        # the connection would simply fail for everyone on a plain-http server.
        ("http://192.168.1.20:8123", "http://192.168.1.20:8123"),
        ("http://192.168.1.20:8123/", "http://192.168.1.20:8123"),
    ],
)
def test_shapes_what_a_person_would_actually_paste(raw: str, expected: str) -> None:
    assert normalize_instance_url(raw) == expected


def test_a_bare_host_with_a_port_is_not_mistaken_for_a_scheme() -> None:
    """`urlsplit` reads "homeassistant.local:8123" as scheme
    "homeassistant.local" — the port looks like a scheme to it. Getting this
    wrong would reject the single most common way a Home Assistant user writes
    their address."""
    assert (
        normalize_instance_url("homeassistant.local:8123")
        == "https://homeassistant.local:8123"
    )


def test_a_scheme_less_host_defaults_to_https() -> None:
    """Defaulting to http would send a long-lived token in the clear. A user on
    plain http can say so; a user on https must not be downgraded silently."""
    assert normalize_instance_url("ha.example.test") == "https://ha.example.test"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "ftp://ha.example.test",
        "https://",
        "http://admin:secret@192.168.1.20:8123",
        "http://192.168.1.20:99999",
    ],
)
def test_rejects_what_cannot_be_an_address(raw: str) -> None:
    with pytest.raises(InstanceUrlError):
        normalize_instance_url(raw)


@pytest.mark.asyncio
async def test_destination_guard_keeps_private_self_hosted_services() -> None:
    assert (
        await validate_instance_destination("http://192.168.1.20:8123/lovelace")
        == "http://192.168.1.20:8123"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [
        "http://127.0.0.1:8123",
        "http://[::1]:8123",
        "http://169.254.169.254/latest/meta-data",
        "http://100.100.100.200/latest/meta-data",
        "http://168.63.129.16/machine",
        "http://[fd00:ec2::254]/latest/meta-data",
        "http://metadata.google.internal/computeMetadata/v1",
        "http://jarvis.localhost:8123",
    ],
)
async def test_destination_guard_rejects_system_and_metadata_targets(raw: str) -> None:
    with pytest.raises(InstanceUrlError, match="blocked system"):
        await validate_instance_destination(raw)


@pytest.mark.asyncio
async def test_destination_guard_requires_every_dns_answer_to_be_safe(monkeypatch) -> None:
    async def mixed_answers(_host: str, _port: int) -> set[str]:
        return {"192.168.1.20", "127.0.0.1"}

    monkeypatch.setattr(instance_urls, "_resolve_addresses", mixed_answers)
    with pytest.raises(InstanceUrlError, match="blocked system"):
        await validate_instance_destination("https://homeassistant.example")


@pytest.mark.asyncio
async def test_destination_guard_accepts_a_dns_name_with_safe_answers(monkeypatch) -> None:
    async def private_answers(_host: str, _port: int) -> set[str]:
        return {"192.168.1.20", "fd12:3456::20"}

    monkeypatch.setattr(instance_urls, "_resolve_addresses", private_answers)
    assert (
        await validate_instance_destination("homeassistant.example:8123/dashboard")
        == "https://homeassistant.example:8123"
    )
