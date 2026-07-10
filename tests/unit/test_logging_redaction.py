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
from urllib.parse import quote

import httpx
import pytest
import structlog

import autopvs1_link.api.autopvs1_client as client_mod
from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.config import settings
from autopvs1_link.logging_config import configure_logging, redact_sensitive_fields

# A recognisable patient-derived HGVS coordinate used as a leak tracer.
_SENTINEL = "NM_SENTINEL7f3a:c.1A>G"
# The distinctive prefix has no URL-special characters, so it survives every
# percent-encoding scheme unchanged -- the most reliable single leak tracer.
_SENTINEL_STEM = "NM_SENTINEL7f3a"


def test_redactor_scrubs_client_network_metadata() -> None:
    result = redact_sensitive_fields(
        None,
        "info",
        {
            "event": "Incoming request",
            "client_ip": "203.0.113.7",
            "user_agent": "patient-workstation/1",
        },
    )
    assert result["client_ip"] == "<redacted>"
    assert result["user_agent"] == "<redacted>"


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


def test_redact_processor_scrubs_rendered_exception_strings() -> None:
    """Rendered exception strings/tracebacks embed the upstream URL -- and that
    URL carries the patient variant. ``error=str(exc)`` and the ``exception``
    field produced by ``format_exc_info`` therefore leak GDPR Art. 9 data even
    though the coordinate never appears under a 'sensitive' key. The redactor
    MUST scrub these by name; only the safe exception *class* (``error_type``)
    survives.
    """
    url = f"https://autopvs1.example/variant/hg19/{_SENTINEL}"
    rendered = f"Server error '500 Internal Server Error' for url '{url}'"
    out = redact_sensitive_fields(
        None,
        "error",
        {
            "event": "Failed to fetch variant data",
            "method": "get_variant_data",
            # Safe class name -- kept for observability.
            "error_type": "HTTPStatusError",
            # Every one of these can carry the rendered URL:
            "error": rendered,
            "exception": f"Traceback (most recent call last):\n...\nhttpx.HTTPStatusError: {rendered}",
            "exc": rendered,
        },
    )

    assert out["error"] == "<redacted>"
    assert out["exception"] == "<redacted>"
    assert out["exc"] == "<redacted>"
    # The exception class name is safe and MUST survive.
    assert out["error_type"] == "HTTPStatusError"
    assert out["method"] == "get_variant_data"

    for field, value in out.items():
        assert _SENTINEL_STEM not in str(value), f"sentinel leaked via field {field!r}: {value!r}"


def test_upstream_failure_never_logs_variant_or_url(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive a real failing upstream fetch whose ``HTTPStatusError`` embeds the
    variant URL, and assert no rendered record leaks the sentinel -- in raw OR
    URL-encoded form.

    ``response.raise_for_status()`` stringifies to
    ``... for url '<variant-url>' ...``; that URL carries the patient variant,
    so it must never survive into a log value -- neither via ``error=str(exc)``
    nor via any ``url``/``variant_id`` field. Exercises both the INFO
    ("Fetching variant data") and ERROR ("Failed to fetch variant data") paths.
    """
    configure_logging()

    # Use a fresh, post-config logger so the redaction pipeline is guaranteed
    # to be in effect regardless of module-import / logger-cache ordering.
    monkeypatch.setattr(client_mod, "logger", structlog.get_logger("test.redaction"))
    # Fail fast: one attempt, no backoff sleeps.
    monkeypatch.setattr(settings.api, "max_retries", 1)

    async def _http_500(
        self: object, url: object, *_args: object, **_kwargs: object
    ) -> httpx.Response:
        # A real 500 whose request URL carries the sentinel variant; the client's
        # own ``raise_for_status()`` then builds an HTTPStatusError whose str()
        # embeds that URL -- the exact leak vector under test.
        request = httpx.Request("GET", str(url))
        return httpx.Response(status_code=500, request=request, text="upstream boom")

    monkeypatch.setattr("httpx.AsyncClient.get", _http_500)

    async def _drive() -> None:
        client = AutoPVS1Client()
        try:
            await client.get_variant_data("hg19", _SENTINEL)
        finally:
            await client.close()

    with caplog.at_level(logging.DEBUG), pytest.raises(httpx.HTTPStatusError):
        asyncio.run(_drive())

    assert caplog.records, "expected at least one log record to be emitted"

    # Raw sentinel, its URL-encoded form, and the encoding-invariant stem must
    # all be absent from every rendered log record.
    forbidden = (_SENTINEL, quote(_SENTINEL, safe=""), _SENTINEL_STEM)
    for record in caplog.records:
        message = record.getMessage()
        for fragment in forbidden:
            assert fragment not in message, (
                f"sentinel fragment {fragment!r} leaked in rendered log record: {message!r}"
            )

    # The prod ERROR path must still have fired (redaction != suppression).
    assert any("Failed to fetch variant data" in r.getMessage() for r in caplog.records), (
        "expected the error-path log record to still be emitted"
    )
