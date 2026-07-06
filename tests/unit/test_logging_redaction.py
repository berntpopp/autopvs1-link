"""Field-name log redaction (finding M2 / decision D3).

Patient variant coordinates, CNV ids, HGVS, free-text queries and full
upstream URLs are GDPR Art. 9 data and MUST NOT reach any log record --
at *any* level (INFO/DEBUG included, not just prod ERROR/WARNING).  These
tests pin the redaction to the *field name* so a leak cannot slip back in
by lowering a call's log level.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest
import structlog

import autopvs1_link.api.autopvs1_client as client_mod
from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.config import settings
from autopvs1_link.logging_config import configure_logging, redact_sensitive_fields

# A recognisable patient-derived HGVS coordinate used as a leak tracer.
_SENTINEL = "NM_SENTINEL7f3a:c.1A>G"


def test_redact_processor_scrubs_every_sensitive_field_by_name() -> None:
    """The processor drops each patient/free-text field regardless of value."""
    event = {
        "event": "Fetching variant data",
        # Kept for traceability / observability:
        "correlation_id": "cid-123",
        "genome_build": "hg19",
        "status": "miss",
        "status_code": 500,
        "duration_ms": 12.3,
        "method": "search_variants",
        # Sensitive -- every one carries the sentinel:
        "variant_id": _SENTINEL,
        "cnv_id": _SENTINEL,
        "query": _SENTINEL,
        "hgvs": _SENTINEL,
        "input_id": _SENTINEL,
        "resolved_variant": _SENTINEL,
        "gene": _SENTINEL,
        "url": f"https://autopvs1.example/variant/hg19/{_SENTINEL}",
        "original_url": f"https://autopvs1.example/search?q={_SENTINEL}",
        "final_url": f"https://autopvs1.example/variant/hg19/{_SENTINEL}",
    }

    out = redact_sensitive_fields(None, "info", dict(event))

    # Non-sensitive fields survive verbatim.
    assert out["correlation_id"] == "cid-123"
    assert out["genome_build"] == "hg19"
    assert out["status"] == "miss"
    assert out["status_code"] == 500
    assert out["duration_ms"] == 12.3
    assert out["method"] == "search_variants"
    assert out["event"] == "Fetching variant data"

    # The sentinel must not survive in ANY field value.
    for field, value in out.items():
        assert _SENTINEL not in str(value), f"sentinel leaked via field {field!r}: {value!r}"


def test_redact_processor_hashes_cache_key() -> None:
    """Cache-key logs must be hashed, not dropped -- keeps correlation, kills PII."""
    key = f"search:{_SENTINEL}:hg19"
    out = redact_sensitive_fields(
        None, "debug", {"event": "Cache miss", "method": "search_variants", "key": key}
    )

    assert _SENTINEL not in str(out["key"])
    assert str(out["key"]).startswith("sha256:")
    # Method name is a safe, stable identifier -- keep it.
    assert out["method"] == "search_variants"


def test_upstream_failure_never_logs_variant_or_url(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive a real failing upstream fetch and assert no rendered record leaks
    the sentinel -- exercises both the INFO ("Fetching variant data") and the
    ERROR ("Failed to fetch variant data") paths, which log ``url`` and
    ``variant_id``.
    """
    configure_logging()

    # Use a fresh, post-config logger so the redaction pipeline is guaranteed
    # to be in effect regardless of module-import / logger-cache ordering.
    monkeypatch.setattr(client_mod, "logger", structlog.get_logger("test.redaction"))
    # Fail fast: one attempt, no backoff sleeps.
    monkeypatch.setattr(settings.api, "max_retries", 1)

    async def _boom(*_args: object, **_kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("httpx.AsyncClient.get", _boom)

    async def _drive() -> None:
        client = AutoPVS1Client()
        try:
            await client.get_variant_data("hg19", _SENTINEL)
        finally:
            await client.close()

    with caplog.at_level(logging.DEBUG), pytest.raises(httpx.ConnectError):
        asyncio.run(_drive())

    assert caplog.records, "expected at least one log record to be emitted"

    for record in caplog.records:
        assert _SENTINEL not in record.getMessage(), (
            f"sentinel leaked in rendered log record: {record.getMessage()!r}"
        )

    # The prod ERROR path must still have fired (redaction != suppression).
    assert any("Failed to fetch variant data" in r.getMessage() for r in caplog.records), (
        "expected the error-path log record to still be emitted"
    )
