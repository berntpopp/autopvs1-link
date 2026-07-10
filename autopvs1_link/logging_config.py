"""Logging configuration for AutoPVS1 Link."""

import hashlib
import logging
import sys

import structlog
from asgi_correlation_id.context import correlation_id
from structlog.types import Processor

from autopvs1_link.config import settings

# GDPR Art. 9 field-name redaction (finding M2 / decision D3).
#
# Variant coordinates, CNV ids, HGVS, free-text queries and full upstream
# URLs are patient-derived genomic data.  They leak into logs through named
# structlog fields across the client/service/route/validation layers, at
# every level (INFO/DEBUG as well as the ERROR/WARNING branches that fire in
# production).  A single processor scrubs them by field NAME on every emitted
# event so redaction never depends on the call site remembering to omit them,
# nor on the active log level.
#
# ``key``/``cache_key`` are *hashed* rather than dropped: the cache key is
# derived from the query/variant, so it is equally sensitive, but a stable
# hash preserves hit/miss correlation for debugging without exposing the
# plaintext.
#
# Rendered exception strings and tracebacks are a *second* leak class: an
# ``httpx.HTTPStatusError`` stringifies to ``... for url '<upstream-url>' ...``
# and that URL embeds the variant/CNV/HGVS coordinate.  ``error=str(exc)`` and
# the ``exception`` field produced by ``format_exc_info`` (``exc_info=True``)
# therefore smuggle GDPR Art. 9 data past the name-based scrub above even
# though the coordinate never appears under a "sensitive" key.  They are
# scrubbed by name too; log ``error_type`` (the exception class) when the
# signal is needed -- the class name is safe and is intentionally NOT redacted.
_REDACTED = "<redacted>"

_SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "variant_id",
        "cnv_id",
        "query",
        "hgvs",
        "input_id",
        "resolved_variant",
        "gene",
        "url",
        "original_url",
        "final_url",
        "client_ip",
        "user_agent",
    }
)

# Fields whose values are rendered exception text and can embed the upstream
# URL (and thus the variant).  ``exception`` is what ``format_exc_info`` emits.
_EXCEPTION_FIELDS: frozenset[str] = frozenset({"error", "exception", "exc"})

_HASHED_FIELDS: frozenset[str] = frozenset({"key", "cache_key"})


def redact_sensitive_fields(logger, method_name, event_dict) -> dict:
    """Scrub patient/free-text fields from every log event by field name.

    Non-``None`` values under a sensitive field name -- including rendered
    exception strings/tracebacks (``error``/``exception``/``exc``), which can
    embed the variant-bearing upstream URL -- are replaced with ``<redacted>``;
    cache-key fields are replaced with a truncated SHA-256 digest
    (``sha256:<hex>``).  All other fields -- correlation id, method /
    operation, ``error_type``, status, timing -- are left untouched for
    observability.
    """
    for field in (*_SENSITIVE_FIELDS, *_EXCEPTION_FIELDS):
        if event_dict.get(field) is not None:
            event_dict[field] = _REDACTED

    for field in _HASHED_FIELDS:
        value = event_dict.get(field)
        if isinstance(value, str) and value:
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
            event_dict[field] = f"sha256:{digest}"

    return event_dict


def add_service_context(logger, method_name, event_dict) -> dict:
    """Add service context to all log events."""
    event_dict["service"] = "autopvs1-link"
    event_dict["version"] = settings.version
    event_dict["environment"] = settings.environment
    return event_dict


def bind_correlation_id(logger, method_name, event_dict) -> dict:
    """Bind the active asgi-correlation-id into every log event."""
    cid = correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def configure_logging() -> None:
    """Configure structured logging for the application."""
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_context,
        bind_correlation_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Field-name redaction MUST be the last processor before rendering so
        # it sees the fully-merged event (bound context + contextvars) and
        # scrubs GDPR Art. 9 data regardless of level (finding M2 / D3).
        redact_sensitive_fields,
    ]

    if settings.logging.json_format:
        try:
            import orjson

            processors.append(structlog.processors.JSONRenderer(serializer=orjson.dumps))
        except ImportError:
            # Fallback to standard JSON if orjson not available
            processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.logging.level.upper()),
    )

    # Suppress noisy third-party loggers if configured
    if settings.logging.suppress_third_party:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger_for_module(module_name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger bound to a specific module.

    Args:
        module_name: Name of the module requesting the logger

    Returns:
        Bound logger with module context
    """
    return structlog.get_logger().bind(module=module_name)
