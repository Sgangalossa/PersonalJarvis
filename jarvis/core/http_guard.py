"""Keep an https-only download https-only, redirect after redirect.

Several places fetch a URL that came from the community registry: the index
itself, a skill's ``SKILL.md``, a plugin's files. Each of them checks the URL
is ``https://`` before fetching, and each says why in a comment — the fetch
runs on the user's machine, so a plaintext or internal address would let a
published entry aim the backend at the loopback API, the router's admin page,
or a cloud metadata endpoint.

That check covers the FIRST url only. With ``follow_redirects=True`` the
server on the other end picks the next one, and a publisher who controls
``https://their-host/skill.md`` controls its ``Location`` header too. So the
guard has to travel with the request rather than stand in front of it.

Usage — one keyword argument on the client::

    async with httpx.AsyncClient(follow_redirects=True, **https_only_async()) as c:
        resp = await c.get(url)

    with httpx.Client(follow_redirects=True, **https_only()) as c:
        resp = c.get(url)

A redirect to anything but https raises :class:`InsecureRedirect`, which is an
``httpx.HTTPError`` — the exception every one of these call sites already
handles as "the download failed".
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Any

import httpx

__all__ = [
    "BlockedDestination",
    "InsecureRedirect",
    "fetch_public_text_async",
    "https_only",
    "https_only_async",
    "public_only_async",
]


class InsecureRedirect(httpx.HTTPError):
    """A redirect tried to leave https.

    Subclasses ``httpx.HTTPError`` on purpose: every download this guards is
    already wrapped in ``except httpx.HTTPError``, so a refused redirect
    surfaces as the ordinary "could not fetch" the caller knows how to report.
    """


def _check(response: httpx.Response) -> None:
    if not response.has_redirect_location:
        return
    location = response.headers.get("location")
    if not location:
        return
    # Resolved against the current URL: a relative Location keeps the scheme it
    # already had, and only an absolute one can change it.
    target = response.url.join(location)
    if target.scheme != "https":
        raise InsecureRedirect(f"refusing a non-https redirect from {response.url} to {target}")


async def _check_async(response: httpx.Response) -> None:
    _check(response)


def https_only() -> dict[str, Any]:
    """Client kwargs that refuse any redirect leaving https (sync client)."""
    return {"event_hooks": {"response": [_check]}}


def https_only_async() -> dict[str, Any]:
    """The same, for ``httpx.AsyncClient`` — its hooks must be awaitable."""
    return {"event_hooks": {"response": [_check_async]}}


# ---------------------------------------------------------------------------
# Public-destination guard: for a URL the USER pasted (not a registry entry),
# plain http is fine, but the fetch runs server-side, so it must never reach
# the loopback API, the LAN, or a cloud metadata endpoint. It runs as a
# REQUEST hook, so every redirect hop is checked before it is sent.
# ---------------------------------------------------------------------------


class BlockedDestination(httpx.HTTPError):
    """The request targeted a non-public address or a disallowed scheme.

    An ``httpx.HTTPError`` for the same reason as :class:`InsecureRedirect`:
    call sites already report that as "the download failed".
    """


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value.split("%", 1)[0])  # drop an IPv6 zone id
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


async def _check_public_request(request: httpx.Request, schemes: frozenset[str]) -> None:
    url = request.url
    if url.scheme not in schemes:
        raise BlockedDestination(f"refusing a {url.scheme!r} URL")
    host = url.host
    if not host:
        raise BlockedDestination("refusing a URL without a host")
    try:
        # A literal address needs no lookup.
        literal_ok = _is_public_ip(host)
    except ValueError:  # not an IP literal, so it is a hostname and DNS resolution below decides
        literal_ok = None
    if literal_ok is not None:
        if not literal_ok:
            raise BlockedDestination(f"refusing non-public address {host}")
        return
    port = url.port or (443 if url.scheme == "https" else 80)
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise BlockedDestination(f"cannot resolve {host}") from exc
    addresses = {info[4][0] for info in infos}
    # Every address must be public: a name that resolves to both a public and a
    # private address could otherwise be connected to on the private one.
    if not addresses or not all(_is_public_ip(str(a)) for a in addresses):
        raise BlockedDestination(f"refusing {host}: it resolves to a non-public address")


async def _public_addresses(url: httpx.URL, schemes: frozenset[str]) -> tuple[str, ...]:
    """Resolve ``url`` once and return only globally routable addresses."""
    if url.scheme not in schemes:
        raise BlockedDestination(f"refusing a {url.scheme!r} URL")
    if url.username or url.password:
        raise BlockedDestination("refusing URL credentials")
    host = url.host
    if not host:
        raise BlockedDestination("refusing a URL without a host")
    try:
        if not _is_public_ip(host):
            raise BlockedDestination(f"refusing non-public address {host}")
        return (host,)
    except ValueError:  # Hostname rather than literal: DNS validation below decides.
        pass
    port = url.port or (443 if url.scheme == "https" else 80)
    try:
        infos = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=5.0,
        )
    except (OSError, TimeoutError) as exc:
        raise BlockedDestination(f"cannot resolve {host}") from exc
    addresses = {str(info[4][0]).split("%", 1)[0] for info in infos}
    if not addresses or not all(_is_public_ip(address) for address in addresses):
        raise BlockedDestination(f"refusing {host}: it resolves to a non-public address")
    return tuple(sorted(addresses, key=lambda value: int(ipaddress.ip_address(value))))


async def fetch_public_text_async(
    url: str,
    *,
    schemes: tuple[str, ...] = ("https",),
    request_timeout: float = 20.0,
    max_bytes: int = 1024 * 1024,
    max_redirects: int = 5,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    """Fetch text while pinning every connection to a validated public IP.

    Resolving in a request hook still leaves a DNS-rebinding window because
    the transport performs a second lookup.  This downloader resolves once,
    validates every answer, and connects to one of those exact IPs.  The
    original host remains in ``Host`` and TLS SNI for certificate validation
    and virtual hosting.  Redirects repeat the validation and pinning.
    """
    allowed = frozenset(item.lower() for item in schemes)
    try:
        target = httpx.URL(url)
    except httpx.InvalidURL as exc:
        raise BlockedDestination("refusing an invalid URL") from exc
    # Environment proxies would replace the exact validated connection target,
    # defeating DNS pinning.  Skill imports therefore connect directly.
    async with httpx.AsyncClient(
        timeout=request_timeout,
        transport=transport,
        trust_env=False,
    ) as client:
        for redirect_count in range(max_redirects + 1):
            addresses = await _public_addresses(target, allowed)
            host = target.host
            assert host is not None  # guaranteed by _public_addresses
            pinned = target.copy_with(host=addresses[0])
            default_port = 443 if target.scheme == "https" else 80
            authority_host = f"[{host}]" if ":" in host else host
            authority = (
                authority_host
                if target.port in (None, default_port)
                else f"{authority_host}:{target.port}"
            )
            request = client.build_request("GET", pinned, headers={"host": authority})
            request.extensions["sni_hostname"] = host
            response = await client.send(request, follow_redirects=False)
            if response.has_redirect_location:
                if redirect_count == max_redirects:
                    raise BlockedDestination("too many redirects")
                location = response.headers.get("location")
                if not location:
                    raise BlockedDestination("redirect without a location")
                target = target.join(location)
                continue
            response.raise_for_status()
            if len(response.content) > max_bytes:
                raise BlockedDestination(f"response exceeds {max_bytes} bytes")
            return response.text
    raise BlockedDestination("download did not produce a response")


def public_only_async(*, schemes: tuple[str, ...] = ("https",)) -> dict[str, Any]:
    """``httpx.AsyncClient`` kwargs that refuse non-public destinations.

    Every request — the first and each redirect hop — must use one of
    ``schemes`` and resolve only to globally routable addresses. The lookup
    happens just before httpx connects; this narrows but does not fully close a
    DNS-rebinding window, which is acceptable for a user-initiated download.
    """
    allowed = frozenset(s.lower() for s in schemes)

    async def _hook(request: httpx.Request) -> None:
        await _check_public_request(request, allowed)

    return {"event_hooks": {"request": [_hook]}}
