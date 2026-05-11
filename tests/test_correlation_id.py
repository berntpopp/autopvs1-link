"""Tests for asgi-correlation-id integration."""

from fastapi.testclient import TestClient

from autopvs1_link.server_manager import app


def test_response_includes_request_id_header() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"]


def test_supplied_request_id_is_echoed() -> None:
    with TestClient(app) as client:
        # asgi-correlation-id's default validator requires a real UUID v4 shape.
        supplied = "12345678-1234-4234-8234-123456789012"
        resp = client.get("/health", headers={"X-Request-ID": supplied})
        assert resp.headers["X-Request-ID"] == supplied
