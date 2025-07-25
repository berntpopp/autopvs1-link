"""Request logging middleware for enhanced observability."""
import time
import uuid
from typing import Callable, List

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from autopvs1_link.config import settings

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with correlation IDs and performance metrics."""

    def __init__(self, app, exclude_paths: List[str] = None):
        """Initialize the middleware.
        
        Args:
            app: The FastAPI application
            exclude_paths: List of paths to exclude from logging
        """
        super().__init__(app)
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
        
        # Extract request context
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else None
        client_ip = self._extract_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Bind correlation ID to logging context
        bound_logger = logger.bind(
            correlation_id=correlation_id,
            method=method,
            path=path,
            query_params=query_params,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        
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
            
            # Log error with context
            bound_logger.error(
                "API request failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            
            # Re-raise the exception
            raise

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
            # Error
            self.logger.error(
                f"Failed {self.operation}",
                duration_ms=round(duration_ms, 2),
                error=str(exc_val),
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
    log_context = {
        "cache_operation": operation,
        "cache_key": key,
        **context
    }
    
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