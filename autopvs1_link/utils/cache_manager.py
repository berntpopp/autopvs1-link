"""Advanced cache management with detailed statistics and event logging."""

import time
import warnings
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

import structlog
from async_lru import AlruCacheLoopResetWarning, alru_cache

from autopvs1_link.config import settings
from autopvs1_link.mcp.telemetry import record_upstream_call

logger = structlog.get_logger()


@dataclass
class CacheStatistics:
    """Detailed cache statistics for a specific cache method."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    errors: int = 0
    total_time: float = 0.0
    last_hit: float | None = None
    last_miss: float | None = None
    created_at: float = field(default_factory=time.time)

    @property
    def total_requests(self) -> int:
        """Total number of cache requests."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def average_time(self) -> float:
        """Average time per request in seconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_time / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 4),
            "average_time_ms": round(self.average_time * 1000, 2),
            "last_hit": self.last_hit,
            "last_miss": self.last_miss,
            "uptime_seconds": round(time.time() - self.created_at, 2),
        }


class AdvancedCacheManager:
    """Advanced cache manager with detailed statistics and event logging."""

    def __init__(self) -> None:
        self._statistics: dict[str, CacheStatistics] = defaultdict(CacheStatistics)
        self._enabled = settings.cache.enabled
        self._event_logging = settings.cache.event_logging
        self._statistics_enabled = settings.cache.statistics_enabled

    def get_statistics(self, method_name: str | None = None) -> dict[str, Any]:
        """Get cache statistics for a specific method or all methods."""
        if method_name:
            stats = self._statistics.get(method_name)
            if stats:
                return {method_name: stats.to_dict()}
            return {method_name: {"error": "Method not found"}}

        return {method: stats.to_dict() for method, stats in self._statistics.items()}

    def clear_statistics(self, method_name: str | None = None) -> None:
        """Clear statistics for a specific method or all methods."""
        if method_name:
            if method_name in self._statistics:
                self._statistics[method_name] = CacheStatistics()
                if self._event_logging:
                    logger.info("Cache statistics cleared", method=method_name)
        else:
            self._statistics.clear()
            if self._event_logging:
                logger.info("All cache statistics cleared")

    def _record_hit(self, method_name: str, key: str, execution_time: float) -> None:
        """Record a cache hit."""
        if not self._statistics_enabled:
            return

        stats = self._statistics[method_name]
        stats.hits += 1
        stats.total_time += execution_time
        stats.last_hit = time.time()

        if self._event_logging:
            logger.debug(
                "Cache hit",
                method=method_name,
                key=key,
                execution_time_ms=round(execution_time * 1000, 2),
                hit_rate=round(stats.hit_rate, 4),
            )

    def _record_miss(self, method_name: str, key: str, execution_time: float) -> None:
        """Record a cache miss."""
        if not self._statistics_enabled:
            return

        stats = self._statistics[method_name]
        stats.misses += 1
        stats.total_time += execution_time
        stats.last_miss = time.time()

        if self._event_logging:
            logger.debug(
                "Cache miss",
                method=method_name,
                key=key,
                execution_time_ms=round(execution_time * 1000, 2),
                hit_rate=round(stats.hit_rate, 4),
            )

    def _record_error(self, method_name: str, key: str, error: str) -> None:
        """Record a cache error."""
        if not self._statistics_enabled:
            return

        stats = self._statistics[method_name]
        stats.errors += 1

        if self._event_logging:
            logger.error("Cache error", method=method_name, key=key, error=error)

    def _record_eviction(self, method_name: str) -> None:
        """Record a cache eviction."""
        if not self._statistics_enabled:
            return

        stats = self._statistics[method_name]
        stats.evictions += 1

        if self._event_logging:
            logger.debug("Cache eviction", method=method_name)

    def enhanced_cache(
        self,
        maxsize: int = 128,
        ttl: int | None = None,
        key_func: Callable | None = None,
    ) -> Callable:
        """Enhanced cache decorator with detailed statistics and event logging."""
        if ttl is None:
            ttl = settings.cache.ttl_seconds

        def decorator(func: Callable) -> Callable:
            # Create the base cache
            cached_func = alru_cache(maxsize=maxsize, ttl=ttl)(func)
            method_name = func.__name__

            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                if not self._enabled:
                    # Cache disabled — still surface latency to LLM callers via
                    # the telemetry CV so meta.elapsed_ms is populated regardless
                    # of whether caching is on.
                    bypass_start = time.perf_counter()
                    try:
                        result = await func(*args, **kwargs)
                    finally:
                        elapsed_ms = (time.perf_counter() - bypass_start) * 1000.0
                        record_upstream_call(elapsed_ms, "bypass")
                    return result

                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{method_name}:{hash((args, tuple(kwargs.items())))}"

                start_time = time.time()
                perf_start = time.perf_counter()

                try:
                    # Check if result is in cache
                    cache_info_before = cached_func.cache_info()
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            category=AlruCacheLoopResetWarning,
                        )
                        result = await cached_func(*args, **kwargs)
                    cache_info_after = cached_func.cache_info()

                    execution_time = time.time() - start_time
                    elapsed_ms = (time.perf_counter() - perf_start) * 1000.0

                    # Determine if this was a hit or miss
                    if cache_info_after.hits > cache_info_before.hits:
                        self._record_hit(method_name, cache_key, execution_time)
                        record_upstream_call(elapsed_ms, "hit")
                    else:
                        self._record_miss(method_name, cache_key, execution_time)
                        record_upstream_call(elapsed_ms, "miss")

                    # Check for evictions
                    if cache_info_after.misses > cache_info_before.misses + 1:
                        self._record_eviction(method_name)

                    return result

                except Exception as e:
                    execution_time = time.time() - start_time
                    self._record_error(method_name, cache_key, str(e))
                    raise

            # Add cache management methods to the wrapper
            wrapper.cache_info = cached_func.cache_info
            wrapper.cache_clear = cached_func.cache_clear
            wrapper.cache_parameters = cached_func.cache_parameters
            wrapper._cache_manager = self
            wrapper._method_name = method_name

            return wrapper

        return decorator


# Global cache manager instance
cache_manager = AdvancedCacheManager()


def cache_key_generator(*args: Any, **kwargs: Any) -> str:
    """Generate a cache key from function arguments."""
    # Convert args and kwargs to a hashable representation
    args_str = "_".join(str(arg) for arg in args)
    kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"{args_str}_{kwargs_str}" if kwargs_str else args_str


async def log_cache_event(event_type: str, method: str, key: str, **context: Any) -> None:
    """Log cache events with consistent formatting."""
    if not settings.cache.event_logging:
        return

    log_context = {"cache_event": event_type, "method": method, "key": key, **context}

    bound_logger = logger.bind(**log_context)

    if event_type == "hit":
        bound_logger.debug("Cache hit")
    elif event_type == "miss":
        bound_logger.debug("Cache miss")
    elif event_type == "set":
        bound_logger.debug("Cache set")
    elif event_type == "clear":
        bound_logger.info("Cache cleared")
    elif event_type == "eviction":
        bound_logger.debug("Cache eviction")
    elif event_type == "error":
        bound_logger.error("Cache error")
    else:
        bound_logger.debug(f"Cache {event_type}")
