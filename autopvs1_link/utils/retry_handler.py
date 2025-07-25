"""Enhanced retry handling with exponential backoff and circuit breaker patterns."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from autopvs1_link.config import settings

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying again
    success_threshold: int = 3  # Successes needed to close circuit
    timeout: float = 30.0  # Request timeout


class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

    def _should_attempt_request(self) -> bool:
        """Determine if a request should be attempted."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if enough time has passed to transition to half-open
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(
                    "Circuit breaker transitioning to half-open", name=self.name
                )
                return True
            return False
        else:  # HALF_OPEN
            return True

    def _record_success(self) -> None:
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed", name=self.name)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker opened",
                    name=self.name,
                    failure_count=self.failure_count,
                )
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened", name=self.name)

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute a function with circuit breaker protection."""
        if not self._should_attempt_request():
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


class RetryableHTTPError(Exception):
    """HTTP error that should be retried."""

    pass


class NonRetryableHTTPError(Exception):
    """HTTP error that should not be retried."""

    pass


def is_retryable_http_error(exception: Exception) -> bool:
    """Determine if an HTTP error should be retried."""
    if isinstance(exception, httpx.HTTPStatusError):
        # Retry on server errors and some client errors
        status_code = exception.response.status_code

        # Always retry these status codes
        retryable_codes = {
            # Server errors
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
            # Some client errors that might be temporary
            408,  # Request Timeout
            429,  # Too Many Requests
        }

        return status_code in retryable_codes

    # Retry on connection/timeout errors
    if isinstance(
        exception,
        (
            httpx.RequestError,
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.ConnectTimeout,
        ),
    ):
        return True

    return False


def classify_http_error(exception: Exception) -> Exception:
    """Classify HTTP errors for retry logic."""
    if is_retryable_http_error(exception):
        retryable_error = RetryableHTTPError(str(exception))
        retryable_error.__cause__ = exception
        return retryable_error
    else:
        non_retryable_error = NonRetryableHTTPError(str(exception))
        non_retryable_error.__cause__ = exception
        return non_retryable_error


class EnhancedRetryHandler:
    """Enhanced retry handler with circuit breaker and intelligent backoff."""

    def __init__(self) -> None:
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.default_circuit_config = CircuitBreakerConfig(
            failure_threshold=settings.api.max_retries,
            recovery_timeout=60.0,
            success_threshold=2,
            timeout=settings.api.request_timeout,
        )

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                name, self.default_circuit_config
            )
        return self.circuit_breakers[name]

    def get_all_circuit_breaker_status(self) -> dict[str, Any]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self.circuit_breakers.items()
        }

    async def retry_with_backoff(
        self,
        func: Callable,
        *args: Any,
        max_attempts: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        circuit_breaker_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic and optional circuit breaker."""
        max_attempts = max_attempts or settings.api.max_retries
        base_delay = base_delay or settings.api.retry_delay
        max_delay = max_delay or 60.0

        # Setup retry configuration
        retry_config = AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=base_delay, min=base_delay, max=max_delay),
            retry=retry_if_exception_type(RetryableHTTPError),
            before_sleep=before_sleep_log(logger, 40),  # WARNING level
            reraise=True,
        )

        async def _execute() -> Any:
            try:
                if circuit_breaker_name:
                    circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)
                    return await circuit_breaker.call(func, *args, **kwargs)
                else:
                    return await func(*args, **kwargs)
            except Exception as e:
                # Classify the error for retry logic
                classified_error = classify_http_error(e)
                raise classified_error

        try:
            async for attempt in retry_config:
                with attempt:
                    return await _execute()
        except RetryError as e:
            # Extract the original exception from the last attempt
            if e.last_attempt and e.last_attempt.exception():
                original_exception = e.last_attempt.exception()
                if (
                    hasattr(original_exception, "__cause__")
                    and original_exception.__cause__
                ):
                    raise original_exception.__cause__
                raise original_exception
            raise

    async def http_request_with_retry(
        self, client: httpx.AsyncClient, method: str, url: str, **request_kwargs: Any
    ) -> httpx.Response:
        """Make HTTP request with retry logic and circuit breaker."""

        async def _make_request() -> httpx.Response:
            try:
                response = await client.request(method, url, **request_kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "HTTP error occurred",
                    method=method,
                    url=url,
                    status_code=e.response.status_code,
                    response_text=e.response.text[:500],  # First 500 chars
                )
                raise
            except httpx.RequestError as e:
                logger.warning(
                    "Request error occurred", method=method, url=url, error=str(e)
                )
                raise

        # Use domain as circuit breaker name
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
        circuit_breaker_name = f"http_client_{domain}"

        return await self.retry_with_backoff(
            _make_request, circuit_breaker_name=circuit_breaker_name
        )


# Global retry handler instance
retry_handler = EnhancedRetryHandler()
