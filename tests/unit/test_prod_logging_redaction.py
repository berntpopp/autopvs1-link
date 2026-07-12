"""Adversarial tests for the F-03 residual: production-path log redaction.

Codex gate (F-03 residual): "the production gunicorn entrypoint imports
server_manager WITHOUT configure_logging, while the service/client/
PerformanceLogger layers still log raw variant_id / query / hgvs / url and
str(exc)."

The GDPR Art. 9 field-name redaction pipeline lives in ``configure_logging``.
It is only effective if (a) it is actually installed on the process that serves
production traffic, and (b) the lower layers never smuggle an identifier past the
name-based scrub via a rendered ``str(exc)`` under a fragile field name. These
tests drive the *entrypoint*, the *PerformanceLogger*, the *cache manager*, and
the *service layer* (NOT the REST routes -- those were covered earlier) and prove
both conditions hold.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from unittest.mock import AsyncMock

import pytest
import structlog
import structlog.testing

from autopvs1_link.logging_config import configure_logging, redact_sensitive_fields

# Encoding-invariant patient-variant tracer. The stem has no URL-special
# characters, so it survives every percent-encoding scheme unchanged -- the most
# reliable single leak tracer across log fields and rendered exception strings.
_SENTINEL_STEM = "NMSENTINELF03"
_SENTINEL = f"{_SENTINEL_STEM}:c.1A>G"
_UPSTREAM_URL = f"https://autopvs1.bgi.com/api/variant/hg19/{_SENTINEL}"
_EXC_PROSE = f"Server error '500 Internal Server Error' for url '{_UPSTREAM_URL}'"


def test_production_entrypoint_installs_redaction_pipeline() -> None:
    """gunicorn/uvicorn serve ``autopvs1_link.server_manager:app``; importing
    that module MUST install the redaction pipeline.

    Simulate a cold production worker: reset structlog to its unconfigured
    defaults (as if nothing has called ``configure_logging`` yet), then reload
    the module the process factory imports. If the import does not wire the
    field-name scrub, every raw ``variant_id``/``url``/``str(exc)`` the lower
    layers log reaches production logs unredacted -- the exact F-03 residual.
    """
    import autopvs1_link.server_manager as server_manager

    structlog.reset_defaults()
    assert redact_sensitive_fields not in structlog.get_config()["processors"], (
        "precondition: a freshly reset structlog must not have the scrub wired"
    )

    importlib.reload(server_manager)

    assert redact_sensitive_fields in structlog.get_config()["processors"], (
        "importing server_manager:app must install the GDPR Art. 9 redaction "
        "pipeline so production (gunicorn/uvicorn worker) logs are scrubbed"
    )


def test_performance_logger_logs_error_class_not_prose() -> None:
    """PerformanceLogger's failure branch must hand the logger only the
    exception CLASS -- never ``str(exc)``, which can embed the variant-bearing
    upstream URL.

    Uses ``capture_logs`` (which bypasses the processor chain) to inspect the
    exact kwargs the call site emits: an ``error`` field would carry the raw
    prose regardless of the downstream scrub.
    """
    from autopvs1_link.middleware.logging_middleware import PerformanceLogger

    with (
        structlog.testing.capture_logs() as records,
        pytest.raises(RuntimeError),
        PerformanceLogger("variant_data_fetch", variant_id=_SENTINEL),
    ):
        raise RuntimeError(_EXC_PROSE)

    errors = [r for r in records if r.get("log_level") == "error"]
    assert errors, "PerformanceLogger must emit an error record on failure"
    rec = errors[0]

    assert rec.get("error_type") == "RuntimeError"
    assert "error" not in rec, "PerformanceLogger must not log str(exc) prose"
    # The sentinel may only appear under the bound ``variant_id`` field, which the
    # production processor scrubs by name (capture_logs bypasses that scrub).
    for key, value in rec.items():
        if key == "variant_id":
            continue
        assert _SENTINEL_STEM not in str(value), f"sentinel leaked via field {key!r}"


async def test_cache_manager_error_logs_class_not_prose(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing cache-wrapped call must log the exception CLASS, not ``str(exc)``.

    The cache manager wraps every service method; on error it previously logged
    ``error=str(e)``, which embeds the variant-bearing upstream URL. Drive the
    public decorator path (robust to the private signature) and assert the
    'Cache error' record carries ``error_type`` only.
    """
    from autopvs1_link.utils import cache_manager as cm

    monkeypatch.setattr(cm.settings.cache, "enabled", True)
    monkeypatch.setattr(cm.settings.cache, "statistics_enabled", True)
    monkeypatch.setattr(cm.settings.cache, "event_logging", True)
    manager = cm.AdvancedCacheManager()

    @manager.enhanced_cache(key_func=lambda variant_id: f"variant:hg19:{variant_id}")
    async def _boom(variant_id: str) -> None:
        raise RuntimeError(_EXC_PROSE)

    with structlog.testing.capture_logs() as records, pytest.raises(RuntimeError):
        await _boom(_SENTINEL)

    cache_errors = [r for r in records if r.get("event") == "Cache error"]
    assert cache_errors, "expected a 'Cache error' log record"
    rec = cache_errors[0]

    assert rec.get("error_type") == "RuntimeError"
    assert "error" not in rec, "cache error must log the exception class, not str(exc)"
    # The cache ``key`` embeds the raw variant; its field name is hashed by the
    # production processor (capture_logs shows it raw), so exclude it here.
    for key, value in rec.items():
        if key == "key":
            continue
        assert _SENTINEL_STEM not in str(value), f"sentinel leaked via field {key!r}"


def test_service_layer_under_prod_config_never_renders_variant(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive the SERVICE layer under the production logging config with a client
    whose exception embeds the patient variant, and assert no rendered log record
    leaks the sentinel -- while the failure path still fires (redaction is not
    suppression).

    Exercises ``AutoPVS1Service.get_variant_data`` -> ``PerformanceLogger`` ->
    ``logger.info`` end to end, the layers Codex flagged as still logging raw
    ``variant_id`` and ``str(exc)``.
    """
    configure_logging()

    import autopvs1_link.middleware.logging_middleware as mw_mod
    import autopvs1_link.services.autopvs1_service as svc_mod
    import autopvs1_link.utils.cache_manager as cm_mod

    # Post-config loggers so the redaction pipeline is guaranteed in effect
    # regardless of module-import / logger-cache ordering.
    monkeypatch.setattr(svc_mod, "logger", structlog.get_logger("test.svc"))
    monkeypatch.setattr(mw_mod, "logger", structlog.get_logger("test.mw"))
    # Bypass the cache so the call deterministically reaches the mocked client
    # via the service's PerformanceLogger path (the layer under test).
    monkeypatch.setattr(cm_mod.cache_manager, "_enabled", False)

    fake_client = AsyncMock()
    fake_client.get_variant_data.side_effect = RuntimeError(_EXC_PROSE)
    service = svc_mod.AutoPVS1Service(fake_client)

    with caplog.at_level(logging.DEBUG), pytest.raises(RuntimeError):
        asyncio.run(service.get_variant_data("hg19", _SENTINEL))

    assert caplog.records, "expected at least one rendered log record"
    for record in caplog.records:
        message = record.getMessage()
        assert _SENTINEL_STEM not in message, (
            f"variant sentinel leaked in rendered production log: {message!r}"
        )
    # Redaction != suppression: the failure path must still have logged.
    assert any("variant_data_fetch" in r.getMessage() for r in caplog.records), (
        "expected the PerformanceLogger failure record to still be emitted"
    )
