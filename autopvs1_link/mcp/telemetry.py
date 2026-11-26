"""Per-call telemetry context for upstream latency and cache observability.

The cache wrapper records ``elapsed_ms`` and ``cache_status`` (``hit`` |
``miss`` | ``coalesced`` | ``bypass``) into a ``ContextVar`` for each
upstream call. ``coalesced`` is the honest label for a caller that
arrived while another caller's miss was already in flight: ``async_lru``
shares the in-flight future, the waiter's ``cache_info().hits`` counter
nominally increments, but the waiter still paid the upstream wall-clock
time. Reporting it as ``hit`` would mislead LLM consumers about cost. The
MCP envelope helper reads it back when assembling ``meta``, so every
tool response can echo the observed wall-clock cost without each tool
handler having to wire timing through return values.

ContextVars are task-local in async code: FastMCP runs each tool
handler as a separate coroutine task and copies the current context at
task creation, so writes in one tool call do not leak into the next.
The default (``None``) means cheap, no-upstream tools (``get_server_health``,
``get_server_capabilities``) leave these meta fields absent on the wire.

Why a ContextVar instead of threading a (data, telemetry) tuple back
through every adapter return: the bulk tools and prompts already
compose multiple service calls; passing telemetry through every layer
would balloon signatures. The ContextVar is overwritten by the cache
wrapper on every upstream call, which matches the contract: the
echoed ``elapsed_ms`` is the LAST upstream call's time. Single-tool
handlers fire exactly one upstream call, so the value is well-defined.
Bulk handlers should ignore the per-item telemetry and use their own
wall-clock if they want to surface bulk-level timing.
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Literal

CacheStatus = Literal["hit", "miss", "coalesced", "bypass"]

_elapsed_ms: ContextVar[float | None] = ContextVar("autopvs1_upstream_elapsed_ms", default=None)
_cache_status: ContextVar[CacheStatus | None] = ContextVar("autopvs1_cache_status", default=None)
# Response-Envelope v1.2: the oldest upstream fetch time behind this tool call.
_retrieved_at: ContextVar[str | None] = ContextVar("autopvs1_retrieved_at", default=None)
_call_started: ContextVar[float | None] = ContextVar("autopvs1_call_started", default=None)


def utc_now() -> str:
    """Now as an RFC 3339 UTC timestamp with ``Z``."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def mark_call_started() -> None:
    """Start the wall clock of one tool call and clear what the last one left."""
    reset_call_telemetry()
    _retrieved_at.set(None)
    _call_started.set(time.perf_counter())


def call_elapsed_ms() -> float:
    """Wall-clock of the current tool call (0.0 outside the MCP middleware)."""
    started = _call_started.get()
    return 0.0 if started is None else (time.perf_counter() - started) * 1000.0


def record_upstream_call(
    elapsed_ms: float, cache_status: CacheStatus, retrieved_at: str | None = None
) -> None:
    """Record metrics for the upstream call that just completed.

    ``retrieved_at`` is when the returned value was fetched from the upstream (for a
    cache hit, the fetch that filled the entry); the oldest one of a tool call is kept.
    """
    _elapsed_ms.set(elapsed_ms)
    _cache_status.set(cache_status)
    oldest = _retrieved_at.get()
    if retrieved_at is not None and (oldest is None or retrieved_at < oldest):
        _retrieved_at.set(retrieved_at)


def get_retrieved_at() -> str | None:
    """The oldest upstream fetch time recorded for the current tool call."""
    return _retrieved_at.get()


def reset_call_telemetry() -> None:
    """Clear per-call telemetry. Tools that fan out to several upstream calls
    should call this before the first to avoid echoing stale values."""
    _elapsed_ms.set(None)
    _cache_status.set(None)


def get_call_telemetry() -> tuple[float | None, CacheStatus | None]:
    """Return the (elapsed_ms, cache_status) recorded for the current call."""
    return _elapsed_ms.get(), _cache_status.get()
