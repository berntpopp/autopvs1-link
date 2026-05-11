"""Async retry helper for HTTP operations.

Replaces the previous tenacity-based wrapper with a small, dependency-free
exponential-backoff loop that only retries on transient httpx errors.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx
import structlog

logger = structlog.get_logger(__name__)

RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.PoolTimeout,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.RemoteProtocolError,
)


async def async_retry[T](
    op: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
) -> T:
    """Run an async operation with exponential backoff on transient errors."""
    delay = base_delay
    last_error: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await op()
        except RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            if attempt == max_attempts:
                logger.warning("retry.exhausted", attempt=attempt, error=str(exc))
                raise
            logger.info(
                "retry.transient_error",
                attempt=attempt,
                next_delay_seconds=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
    raise RuntimeError("async_retry exited without return") from last_error
