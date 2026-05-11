"""Tests for the /metrics endpoint."""

import importlib

from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_prometheus_text(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_METRICS_ENABLED", "true")
    import autopvs1_link.server_manager as sm

    importlib.reload(sm)
    with TestClient(sm.app) as client:
        client.get("/health")
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        body = resp.text
        assert "autopvs1_link_http_requests_total" in body


def test_metrics_endpoint_404_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_METRICS_ENABLED", "false")
    import autopvs1_link.server_manager as sm

    importlib.reload(sm)
    with TestClient(sm.app) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 404
