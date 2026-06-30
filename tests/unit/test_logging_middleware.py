"""Tests for RequestLoggingMiddleware."""

from unittest.mock import MagicMock

import structlog.testing
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autopvs1_link.middleware.logging_middleware import RequestLoggingMiddleware

_VARIANT_ID = "17-43045712-G-A"
_GENOME = "hg38"


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/work")
    async def work() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("fail")

    return app


def test_middleware_logs_normal_request() -> None:
    with TestClient(_build_app()) as client:
        r = client.get("/work")
        assert r.status_code == 200
        assert r.headers.get("X-Correlation-ID")


def test_middleware_skips_excluded_paths() -> None:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200


def test_middleware_propagates_exception_after_logging() -> None:
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        r = client.get("/boom")
        assert r.status_code == 500


def test_extract_client_ip_uses_x_forwarded_for() -> None:
    mw = RequestLoggingMiddleware(app=MagicMock())
    request = MagicMock()
    request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
    request.client = None
    assert mw._extract_client_ip(request) == "1.2.3.4"


def test_extract_client_ip_falls_back_to_request_client() -> None:
    mw = RequestLoggingMiddleware(app=MagicMock())
    request = MagicMock()
    request.headers = {}
    request.client.host = "10.0.0.1"
    assert mw._extract_client_ip(request) == "10.0.0.1"


def test_request_log_context_omits_pii_by_default() -> None:
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/variant/17-43045712-G-A"
    request.query_params = "genome=hg38"
    request.headers = {"user-agent": "secret-agent", "x-forwarded-for": "8.8.8.8"}
    request.client.host = "10.0.0.1"

    mw = RequestLoggingMiddleware(app=MagicMock())
    ctx = mw._request_log_context(request, "cid-123")

    assert ctx == {
        "correlation_id": "cid-123",
        "method": "GET",
        "path": "/variant/17-43045712-G-A",
    }
    assert "query_params" not in ctx
    assert "client_ip" not in ctx
    assert "user_agent" not in ctx


def test_request_log_context_includes_client_ip_when_opted_in() -> None:
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/variant/17-43045712-G-A"
    request.headers = {"user-agent": "ua-x", "x-forwarded-for": "8.8.8.8"}
    request.client = None

    mw = RequestLoggingMiddleware(app=MagicMock(), log_client_ip=True)
    ctx = mw._request_log_context(request, "cid-123")

    assert ctx["client_ip"] == "8.8.8.8"
    assert ctx["user_agent"] == "ua-x"


def test_error_path_does_not_log_variant_id() -> None:
    """Regression: variant ID in /variant/{genome}/{id} path MUST NOT appear in
    any log record on the ERROR path.

    ERROR >= WARNING so the error branch fires in production even at the default
    WARNING log level.  Before the fix, ``_request_log_context`` bound
    ``path=/variant/hg38/<variant_id>`` verbatim and ``error=str(e)`` could
    echo the variant string — both are GDPR Art. 9 leaks (#41).
    """
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/variant/{genome_build}/{variant_id}")
    async def fail_variant(genome_build: str, variant_id: str) -> dict[str, str]:
        # Exception message echoes the variant to cover the error=str(e) surface too.
        raise RuntimeError(f"upstream error processing {variant_id}")

    with (
        structlog.testing.capture_logs() as records,
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        client.get(f"/variant/{_GENOME}/{_VARIANT_ID}")

    assert records, "Expected at least one log record to be emitted"

    for record in records:
        for field, value in record.items():
            assert _VARIANT_ID not in str(value), (
                f"Variant ID '{_VARIANT_ID}' leaked in log field '{field}': {record}"
            )

    # correlation_id must still be present for downstream traceability
    assert any("correlation_id" in r for r in records), "No correlation_id found in any log record"


def test_sanitize_path_redacts_variant_segment() -> None:
    """Unit test for the _sanitize_path helper."""
    from autopvs1_link.middleware.logging_middleware import _sanitize_path

    assert _sanitize_path(f"/variant/{_GENOME}/{_VARIANT_ID}") == f"/variant/{_GENOME}/<redacted>"
    assert _sanitize_path("/cnv/hg19/1-100000-200000-DEL") == "/cnv/hg19/<redacted>"
    assert _sanitize_path("/health") == "/health"
    assert _sanitize_path("/api/v1/something") == "/api/v1/something"
