"""Adversarial route-level tests for REST data-leakage hardening (finding F-03).

Proves the legacy REST variant/gene routes:
  * reject hostile/oversize identifiers BEFORE any upstream call,
  * return FIXED caller-safe error messages (never str(exc), never the id),
  * hand the logger only error class/code -- never the genomic identifier, the
    upstream response body, or the raw exception prose.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import structlog.testing
from httpx import ASGITransport, AsyncClient

from autopvs1_link.server_manager import app
from autopvs1_link.services.service_manager import get_managed_service

# Grammar-valid variant that passes route validation and reaches the mocked
# service; used as a leak tracer for the upstream-error paths.
_VALID_VARIANT = "X-83508928-A-T"
# Upstream exception prose that embeds the variant-bearing URL -- the exact
# str(exc) surface the pre-fix routes reflected into logs and responses.
_UPSTREAM_URL = f"https://autopvs1.bgi.com/api/variant/hg38/{_VALID_VARIANT}"
_EXC_PROSE = f"Server error '500 Internal Server Error' for url '{_UPSTREAM_URL}'"


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
def mock_service():
    service = AsyncMock()
    app.dependency_overrides[get_managed_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.clear()


def _no_field_contains(records, needle: str) -> bool:
    return all(needle not in str(value) for record in records for value in record.values())


async def test_hostile_variant_rejected_before_upstream_call(async_client, mock_service) -> None:
    with structlog.testing.capture_logs() as records:
        resp = await async_client.get("http://test/variant/hg38/IGNORE_PREVIOUS_INSTRUCTIONS")

    assert resp.status_code == 400
    mock_service.get_variant_data.assert_not_called()
    mock_service.resolve_hgvs_notation.assert_not_called()
    detail = str(resp.json()["detail"])
    assert "IGNORE_PREVIOUS_INSTRUCTIONS" not in detail
    assert _no_field_contains(records, "IGNORE_PREVIOUS_INSTRUCTIONS")


async def test_hostile_gene_rejected_before_upstream_call(async_client, mock_service) -> None:
    with structlog.testing.capture_logs() as records:
        resp = await async_client.get(
            "http://test/gene/search", params={"q": "DROP TABLE variants; --"}
        )

    assert resp.status_code == 400
    mock_service.search_variants.assert_not_called()
    detail = str(resp.json()["detail"])
    assert "DROP TABLE" not in detail
    assert _no_field_contains(records, "DROP TABLE")


async def test_upstream_error_prose_never_reaches_response_or_logs(
    async_client, mock_service
) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_service.get_variant_data.side_effect = httpx.HTTPStatusError(
        message=_EXC_PROSE,
        request=httpx.Request("GET", _UPSTREAM_URL),
        response=mock_response,
    )

    with structlog.testing.capture_logs() as records:
        resp = await async_client.get(f"http://test/variant/hg38/{_VALID_VARIANT}")

    # Fixed, caller-safe response -- no upstream prose, no genomic identifier.
    assert resp.status_code == 502
    detail = str(resp.json()["detail"])
    assert _VALID_VARIANT not in detail
    assert "autopvs1.bgi.com" not in detail
    assert "Server error" not in detail

    # Logs carry only class/code -- never the identifier, URL, or exception prose.
    assert records, "expected at least one log record"
    assert _no_field_contains(records, _VALID_VARIANT)
    assert _no_field_contains(records, "autopvs1.bgi.com")
    assert _no_field_contains(records, _EXC_PROSE)
    assert any(r.get("error_type") == "HTTPStatusError" for r in records)
    assert all("error" not in r for r in records), "raw exception prose must not be logged"


async def test_not_found_returns_fixed_message(async_client, mock_service) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_service.get_variant_data.side_effect = httpx.HTTPStatusError(
        message=f"Not found for {_VALID_VARIANT}",
        request=httpx.Request("GET", _UPSTREAM_URL),
        response=mock_response,
    )

    resp = await async_client.get(f"http://test/variant/hg38/{_VALID_VARIANT}")

    assert resp.status_code == 404
    detail = str(resp.json()["detail"])
    assert "not found" in detail.lower()
    assert _VALID_VARIANT not in detail


async def test_server_error_returns_fixed_message_no_prose(async_client, mock_service) -> None:
    secret = f"secret upstream detail {_VALID_VARIANT}"
    mock_service.get_variant_data.side_effect = RuntimeError(secret)

    with structlog.testing.capture_logs() as records:
        resp = await async_client.get(f"http://test/variant/hg38/{_VALID_VARIANT}")

    assert resp.status_code == 500
    detail = str(resp.json()["detail"])
    assert "Internal server error" in detail
    assert _VALID_VARIANT not in detail
    assert "secret upstream detail" not in detail
    assert _no_field_contains(records, "secret upstream detail")
    assert any(r.get("error_type") == "RuntimeError" for r in records)
