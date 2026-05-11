"""Logging configuration for AutoPVS1 Link."""

import logging
import sys

import structlog
from structlog.types import Processor

from autopvs1_link.config import settings


def add_service_context(logger, method_name, event_dict) -> dict:
    """Add service context to all log events."""
    event_dict["service"] = "autopvs1-link"
    event_dict["version"] = settings.version
    event_dict["environment"] = settings.environment
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
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
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
