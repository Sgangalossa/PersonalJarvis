"""Normalize the base address of a self-hosted service.

Home Assistant, Jellyfin, Nextcloud, Paperless and Immich have no fixed public
endpoint — the address is the user's own. People type it the way they see it in
their browser, which means a trailing slash, a path they happened to be on, a
missing scheme, or a copied URL with a query string. All of those are the same
server, and none of them should fail a connection.

Deliberately does NOT resolve or reach anything: it only shapes the string. The
connect flow finds out whether the address is real by actually calling it.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

# A plain hostname without a scheme is far more likely to be a LAN box reached
# over http than a public https host, but guessing wrong costs a confusing
# failure. https is the safer default: a user running plain http can type it,
# whereas silently downgrading to http would send their long-lived token in the
# clear.
_DEFAULT_SCHEME = "https"


class InstanceUrlError(ValueError):
    """The entered address cannot be a service base URL."""


_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data.ec2.internal",
    }
)
_BLOCKED_IPS = frozenset(
    {
        ipaddress.ip_address("100.100.100.200"),  # Alibaba metadata
        ipaddress.ip_address("168.63.129.16"),  # Azure platform virtual IP
        ipaddress.ip_address("fd00:ec2::254"),  # AWS IMDS IPv6
        ipaddress.ip_address("fd20:ce::254"),  # Google metadata IPv6
    }
)


def _safe_service_address(value: str) -> bool:
    """Whether an address can represent a user-owned service.

    RFC1918/ULA addresses are deliberately allowed: private Home Assistant,
    Jellyfin and similar instances are the feature. Machine-local, link-local,
    metadata, multicast and reserved destinations are never valid instances.
    """
    ip = ipaddress.ip_address(value.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip in _BLOCKED_IPS
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


async def _resolve_addresses(host: str, port: int) -> set[str]:
    try:
        infos = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(
                host, port, type=socket.SOCK_STREAM
            ),
            timeout=5.0,
        )
    except (OSError, TimeoutError) as exc:
        raise InstanceUrlError("address host could not be resolved") from exc
    return {str(info[4][0]) for info in infos}


def normalize_instance_url(raw: str) -> str:
    """Return ``scheme://host[:port]`` with no trailing slash.

    Raises :class:`InstanceUrlError` when the input cannot be an address at all,
    so the caller can say something useful instead of failing later with a
    confusing HTTP error.
    """
    value = (raw or "").strip()
    if not value:
        raise InstanceUrlError("no address given")

    # `urlsplit` reads a scheme-less "homeassistant.local:8123" as scheme
    # "homeassistant.local" — the port looks like a scheme to it. Add the
    # scheme first so the whole string is parsed as an authority.
    if "//" not in value:
        value = f"{_DEFAULT_SCHEME}://{value}"

    parts = urlsplit(value)
    if parts.scheme not in ("http", "https"):
        raise InstanceUrlError(
            f"address must start with http:// or https:// (got {parts.scheme!r})"
        )
    if not parts.hostname:
        raise InstanceUrlError("address is missing a host name")
    if parts.username is not None or parts.password is not None:
        raise InstanceUrlError("address must not contain user information")
    try:
        _ = parts.port
    except ValueError as exc:
        raise InstanceUrlError("address contains an invalid port") from exc

    # Drop whatever page the user happened to copy from, plus any query or
    # fragment: what we need is the server root.
    return urlunsplit((parts.scheme, parts.netloc, "", "", "")).rstrip("/")


async def validate_instance_destination(raw: str) -> str:
    """Normalize and reject sensitive system destinations before validation.

    Self-hosted plugins must be able to reach private LAN/ULA addresses, so a
    public-internet-only SSRF guard would break their core contract. This guard
    instead excludes destinations that can target Jarvis itself, cloud metadata
    services or non-host endpoints. Every resolved address must pass so a mixed
    DNS answer cannot fall through to a blocked address.
    """
    normalized = normalize_instance_url(raw)
    parts = urlsplit(normalized)
    host = parts.hostname or ""
    canonical_host = host.rstrip(".").casefold()
    if canonical_host in _BLOCKED_HOSTNAMES or canonical_host.endswith(".localhost"):
        raise InstanceUrlError("address targets a blocked system host")

    literal_candidate = ":" in host or bool(host) and all(
        character in "0123456789." for character in host
    )
    if literal_candidate:
        try:
            literal_safe = _safe_service_address(host)
        except ValueError as exc:
            raise InstanceUrlError("address contains an invalid IP address") from exc
        if not literal_safe:
            raise InstanceUrlError("address targets a blocked system network")
        return normalized

    port = parts.port or (443 if parts.scheme == "https" else 80)
    addresses = await _resolve_addresses(host, port)
    if not addresses or not all(_safe_service_address(address) for address in addresses):
        raise InstanceUrlError("address resolves to a blocked system network")
    return normalized
