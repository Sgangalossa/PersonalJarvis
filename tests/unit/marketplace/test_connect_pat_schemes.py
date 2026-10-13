"""connect_pat must validate the pasted token per auth_scheme:
  bearer        -> Authorization: Bearer <token>
  bot           -> Authorization: Bot <token>      (Discord)
  telegram_path -> token in the URL {token}, no header, body ok==true
"""

import httpx
import pytest

from jarvis.core import http_guard
from jarvis.marketplace import instance_url as instance_urls
from jarvis.marketplace.catalog import InstanceUrlSpec, PatPasteAuth, PluginSpec
from jarvis.marketplace.instance_url import InstanceUrlError
from jarvis.ui.web import marketplace_routes as mr


def _spec(scheme: str, validation_endpoint: str) -> PluginSpec:
    return PluginSpec(
        id="x",
        display_name="X",
        description="d",
        category="Communication",
        logo_slug="x",
        auth=PatPasteAuth(
            mode="pat_paste",
            token_creation_url="https://x",  # noqa: S106 -- URL field, not a token
            token_prefix="",
            validation_endpoint=validation_endpoint,
            instruction_md="md",
            auth_scheme=scheme,
        ),
    )


def _capture_transport(captured, *, body=None, status=200):
    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["host"] = request.headers.get("host")
        captured["sni"] = request.extensions.get("sni_hostname")
        return httpx.Response(status, json=body if body is not None else {"ok": True})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_bearer_scheme_uses_bearer_header():
    captured = {}
    validate = mr._make_validator(_capture_transport(captured))
    ok, status = await validate(_spec("bearer", "https://api.example/me").auth, "tok123")
    assert ok is True and status == 200
    assert captured["auth"] == "Bearer tok123"
    assert captured["url"] == "https://api.example/me"


@pytest.mark.asyncio
async def test_bot_scheme_uses_bot_header():
    captured = {}
    validate = mr._make_validator(_capture_transport(captured))
    ok, _ = await validate(
        _spec("bot", "https://discord.com/api/v10/users/@me").auth, "abc.def.ghi"
    )
    assert ok is True
    assert captured["auth"] == "Bot abc.def.ghi"


@pytest.mark.asyncio
async def test_telegram_path_splices_token_and_sends_no_header(monkeypatch):
    async def public_answer(_url, _schemes):
        return ("149.154.167.220",)

    monkeypatch.setattr(http_guard, "_public_addresses", public_answer)
    captured = {}
    validate = mr._make_validator(
        _capture_transport(captured, body={"ok": True})
    )
    ok, _ = await validate(
        _spec("telegram_path", "https://api.telegram.org/bot{token}/getMe").auth,
        "123:ABC",
    )
    assert ok is True
    assert "123:ABC" in captured["url"]
    assert captured["auth"] is None


@pytest.mark.asyncio
async def test_telegram_path_cannot_replace_the_fixed_public_authority(monkeypatch):
    async def public_answer(_url, _schemes):
        return ("149.154.167.220",)

    monkeypatch.setattr(http_guard, "_public_addresses", public_answer)
    captured = {}
    validate = mr._make_validator(
        _capture_transport(captured, body={"ok": True})
    )

    ok, _ = await validate(
        _spec("telegram_path", "https://api.telegram.org/bot{token}/getMe").auth,
        "123:ABC/../../?next=http://127.0.0.1",
    )

    assert ok is True
    assert captured["url"].startswith(
        "https://149.154.167.220/bot123:ABC%2F..%2F..%2F%3F"
    )
    assert captured["host"] == "api.telegram.org"
    assert captured["sni"] == "api.telegram.org"


@pytest.mark.asyncio
async def test_telegram_path_rejects_ok_false_even_on_200(monkeypatch):
    async def public_answer(_url, _schemes):
        return ("149.154.167.220",)

    monkeypatch.setattr(http_guard, "_public_addresses", public_answer)
    captured = {}
    validate = mr._make_validator(
        _capture_transport(captured, body={"ok": False, "error_code": 401})
    )
    ok, _ = await validate(
        _spec("telegram_path", "https://api.telegram.org/bot{token}/getMe").auth,
        "bad",
    )
    assert ok is False


@pytest.mark.asyncio
async def test_self_hosted_validation_blocks_local_process_targets_before_http() -> None:
    async def must_not_send(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("blocked destination reached the HTTP transport")

    auth = PatPasteAuth(
        mode="pat_paste",
        token_creation_url="https://example.test/tokens",  # noqa: S106 -- URL field
        token_prefix="",
        validation_endpoint="https://unused.example.test/me",
        instruction_md="md",
        instance_url=InstanceUrlSpec(
            label="Server",
            placeholder="http://server.local:8123",
            validation_path="/api/",
        ),
    )
    validate = mr._make_validator(httpx.MockTransport(must_not_send))

    with pytest.raises(InstanceUrlError, match="blocked system"):
        await validate(auth, "token", "http://127.0.0.1:8123")


@pytest.mark.asyncio
async def test_self_hosted_validation_pins_dns_and_preserves_authority(monkeypatch) -> None:
    async def private_answer(_host: str, _port: int) -> set[str]:
        return {"192.168.1.20"}

    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["host"] = request.headers.get("host")
        captured["sni"] = request.extensions.get("sni_hostname")
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(instance_urls, "_resolve_addresses", private_answer)
    auth = PatPasteAuth(
        mode="pat_paste",
        token_creation_url="https://example.test/tokens",  # noqa: S106 -- URL field
        token_prefix="",
        validation_endpoint="https://unused.example.test/me",
        instruction_md="md",
        instance_url=InstanceUrlSpec(
            label="Server",
            placeholder="https://server.example:8443",
            validation_path="/api/me",
        ),
    )

    ok, status = await mr._make_validator(httpx.MockTransport(handler))(
        auth, "token", "https://server.example:8443/dashboard"
    )

    assert ok is True and status == 200
    assert captured == {
        "url": "https://192.168.1.20:8443/api/me",
        "host": "server.example:8443",
        "sni": "server.example",
        "auth": "Bearer token",
    }
