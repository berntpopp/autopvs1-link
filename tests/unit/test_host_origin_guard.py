"""Security contract for strict Host and Origin validation.

fastmcp >=3.4.4 re-enables DNS-rebinding protection natively. The app pins the
proxied Host/Origin via an explicit allowlist (default loopback) and installs an
outer ``HostOriginGuardMiddleware(mode="strict")`` so every route -- the
FastAPI-native ``/health``/``/api`` handlers and the mounted ``/mcp`` sub-app --
rejects an untrusted Host with 421 and an untrusted Origin with 403.
"""

from __future__ import annotations

import inspect
from importlib.metadata import version

import pytest
from fastapi.testclient import TestClient
from fastmcp import FastMCP
from packaging.version import Version
from pydantic import ValidationError

from autopvs1_link import server_manager
from autopvs1_link.config import ServerConfig, settings

PUBLIC_HOST = "autopvs1-link.example.org"
PUBLIC_ORIGIN = f"https://{PUBLIC_HOST}"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        settings.server,
        "allowed_hosts",
        ["localhost", "127.0.0.1", "::1", PUBLIC_HOST],
    )
    monkeypatch.setattr(settings.server, "allowed_origins", [PUBLIC_ORIGIN])
    return TestClient(server_manager.create_app(), raise_server_exceptions=False)


def test_fastmcp_supports_native_strict_guard_configuration() -> None:
    assert Version(version("fastmcp")) >= Version("3.4.4")
    source = inspect.getsource(server_manager)
    assert "host_origin_protection=True" in source
    assert "allowed_hosts=settings.server.allowed_hosts" in source
    assert "allowed_origins=settings.server.allowed_origins" in source


def test_create_app_passes_exact_lists_to_native_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    original_http_app = FastMCP.http_app

    def spy_http_app(self: FastMCP, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return original_http_app(self, *args, **kwargs)

    monkeypatch.setattr(FastMCP, "http_app", spy_http_app)
    server_manager.create_app()

    assert captured["host_origin_protection"] is True
    assert captured["allowed_hosts"] is settings.server.allowed_hosts
    assert captured["allowed_origins"] is settings.server.allowed_origins


@pytest.mark.parametrize(
    "host",
    ["localhost", "localhost:8000", "127.0.0.1:8000", "[::1]", "[::1]:8000"],
)
def test_loopback_hosts_are_allowed(client: TestClient, host: str) -> None:
    assert client.get("/health", headers={"Host": host}).status_code == 200


@pytest.mark.parametrize("host", [PUBLIC_HOST, f"{PUBLIC_HOST}:8443"])
def test_configured_public_host_is_allowed(client: TestClient, host: str) -> None:
    assert client.get("/health", headers={"Host": host}).status_code == 200


@pytest.mark.parametrize("path", ["/health", "/mcp"])
def test_unlisted_host_is_rejected_on_every_route(client: TestClient, path: str) -> None:
    assert client.get(path, headers={"Host": "attacker.example"}).status_code == 421


@pytest.mark.parametrize("path", ["/health", "/mcp"])
def test_unlisted_origin_is_rejected_on_every_route(client: TestClient, path: str) -> None:
    response = client.get(
        path,
        headers={"Host": "localhost", "Origin": "https://attacker.example"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("origin", [None, PUBLIC_ORIGIN])
def test_absent_or_configured_origin_is_allowed(client: TestClient, origin: str | None) -> None:
    headers = {"Host": "localhost"}
    if origin is not None:
        headers["Origin"] = origin
    assert client.get("/health", headers=headers).status_code == 200


def test_untrusted_preflight_is_rejected_by_outer_guard(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Host": "attacker.example",
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 421


def test_default_allowlists_are_loopback_only_and_origin_empty() -> None:
    configured = ServerConfig(_env_file=None)
    assert configured.allowed_hosts == ["localhost", "127.0.0.1", "::1"]
    assert configured.allowed_origins == []


@pytest.mark.parametrize(
    ("field", "entry"),
    [
        ("allowed_hosts", "*"),
        ("allowed_hosts", "*.example.org"),
        ("allowed_hosts", "host?.example.org"),
        ("allowed_hosts", "host[0].example.org"),
        ("allowed_origins", "https://*.example.org"),
    ],
)
def test_wildcard_allowlist_entries_are_rejected(field: str, entry: str) -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        ServerConfig(_env_file=None, **{field: [entry]})


def test_allowlists_load_from_prefixed_json_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_SERVER_ALLOWED_HOSTS", '["api.example.org"]')
    monkeypatch.setenv("AUTOPVS1_LINK_SERVER_ALLOWED_ORIGINS", '["https://app.example.org"]')
    configured = ServerConfig(_env_file=None)
    assert configured.allowed_hosts == ["api.example.org"]
    assert configured.allowed_origins == ["https://app.example.org"]
