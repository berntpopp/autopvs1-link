"""Request logging middleware for enhanced observability."""

import re
import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

# Matches the two REST paths that carry per-variant genomic identifiers
# (GDPR Art. 9 data):
#   /variant/{genome_build}/{variant_id}
#   /cnv/{genome_build}/{cnv_id}
# Group 1: prefix including the genome_build (low-sensitivity, kept for
# debugging); the final dynamic segment is redacted.
_VARIANT_PATH_RE = re.compile(r"^(/(variant|cnv)/[^/]+)/(.+)$")


def _sanitize_path(path: str) -> str:
    """Redact GDPR Art. 9 genomic identifiers from REST paths before logging.

    ``/variant/{genome_build}/{variant_id}`` and
    ``/cnv/{genome_build}/{cnv_id}`` carry patient-derived variant IDs in the
    final path segment.  This helper replaces that segment with the literal
    ``<redacted>`` so it never enters a log field.  All other paths are
    returned unchanged.
    """
    if m := _VARIANT_PATH_RE.match(path):
        return f"{m.group(1)}/<redacted>"
    return path


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with correlation IDs and performance metrics."""

    def __init__(self, app, exclude_paths: list[str] | None = None, log_client_ip: bool = False):
        """Initialize the middleware.

        Args:
            app: The FastAPI application
            exclude_paths: List of paths to exclude from logging
            log_client_ip: When True, bind the raw client IP and user agent
                into request logs. Off by default (GDPR Art. 5(1)(c) data
                minimization); wired from ``settings.debug`` so production
                never logs raw IPs.
        """
        super().__init__(app)
        self.log_client_ip = log_client_ip
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add logging."""
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Generate correlation ID
        correlation_id = str(uuid.uuid4())

        # Bind a data-minimized logging context. Variant IDs ride in the
        # REST path/query and may be patient-derived genomic data
        # (GDPR Art. 9); query_params is therefore NEVER logged, and the
        # raw client_ip/user_agent (personal data, Art. 5(1)(c)) are bound
        # only when the opt-in debug gate is set. The MCP body-arg path
        # already meets this bar; this brings REST to parity.
        bound_logger = logger.bind(**self._request_log_context(request, correlation_id))

        # Log incoming request
        bound_logger.info("Incoming request")

        # Process request with timing
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            # Log successful completion
            bound_logger.info(
                "API request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                response_size=response.headers.get("content-length"),
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log error with context.
            # ``error=str(e)`` is intentionally omitted: exception messages can
            # echo patient-derived variant identifiers from the request path.
            # ``error_type`` (exception class name) and ``exc_info=True``
            # (full traceback) provide sufficient signal for debugging without
            # leaking GDPR Art. 9 data.
            bound_logger.error(
                "API request failed",
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )

            # Re-raise the exception
            raise

    def _request_log_context(self, request: Request, correlation_id: str) -> dict[str, str]:
        """Build the data-minimized bind context for request logs.

        Default level emits only ``correlation_id``/``method``/``path``.
        The raw client IP and user agent are personal data; they are added
        only when ``log_client_ip`` is opted in. ``query_params`` is never
        bound because variant IDs in the query string may be patient-derived
        genomic data (GDPR Art. 9 / Art. 5(1)(c) data minimization).
        """
        context: dict[str, str] = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": _sanitize_path(request.url.path),
        }
        if self.log_client_ip:
            context["client_ip"] = self._extract_client_ip(request)
            context["user_agent"] = request.headers.get("user-agent", "")
        return context

    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers."""
        # Check common proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get the first IP from the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


class PerformanceLogger:
    """Context manager for logging performance metrics of operations."""

    def __init__(self, operation: str, **context):
        """Initialize the performance logger.

        Args:
            operation: Name of the operation being timed
            **context: Additional context to include in logs
        """
        self.operation = operation
        self.context = context
        self.logger = logger.bind(**context)
        self.start_time = None

    def __enter__(self):
        """Start timing the operation."""
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log completion with timing."""
        if self.start_time is None:
            return

        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is None:
            # Success
            self.logger.info(
                f"Completed {self.operation}",
                duration_ms=round(duration_ms, 2),
            )
        else:
            # Error. Log only the exception CLASS (``error_type``): ``str(exc)``
            # can embed the variant-bearing upstream URL (GDPR Art. 9 / finding
            # F-03), so it is never handed to the logger. ``exc_info`` renders a
            # traceback whose ``exception`` field is scrubbed by name in
            # ``configure_logging`` (installed on the production entrypoint), so
            # the debug signal survives without leaking the coordinate.
            self.logger.error(
                f"Failed {self.operation}",
                duration_ms=round(duration_ms, 2),
                error_type=exc_type.__name__,
                exc_info=True,
            )


def get_correlation_id() -> str:
    """Get the current request's correlation ID from structlog context.

    Returns:
        The correlation ID if available, otherwise generates a new one
    """
    try:
        # Try to get from current structlog context
        return structlog.get_logger().bind().get("correlation_id", str(uuid.uuid4()))
    except Exception:
        # Fallback to new correlation ID
        return str(uuid.uuid4())


async def log_cache_operation(operation: str, key: str, hit: bool = None, **context):
    """Log cache operations with consistent format.

    Args:
        operation: Type of cache operation (hit, miss, set, clear)
        key: Cache key involved
        hit: Whether it was a cache hit (None for non-retrieval operations)
        **context: Additional context
    """
    log_context = {"cache_operation": operation, "cache_key": key, **context}

    if hit is not None:
        log_context["cache_hit"] = hit

    bound_logger = logger.bind(**log_context)

    if operation == "hit":
        bound_logger.debug("Cache hit")
    elif operation == "miss":
        bound_logger.debug("Cache miss")
    elif operation == "set":
        bound_logger.debug("Cache set")
    elif operation == "clear":
        bound_logger.info("Cache cleared")
    else:
        bound_logger.debug(f"Cache {operation}")
