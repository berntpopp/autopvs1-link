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

from contextvars import ContextVar
from typing import Literal

CacheStatus = Literal["hit", "miss", "coalesced", "bypass"]

_elapsed_ms: ContextVar[float | None] = ContextVar("autopvs1_upstream_elapsed_ms", default=None)
_cache_status: ContextVar[CacheStatus | None] = ContextVar("autopvs1_cache_status", default=None)


def record_upstream_call(elapsed_ms: float, cache_status: CacheStatus) -> None:
    """Record metrics for the upstream call that just completed."""
    _elapsed_ms.set(elapsed_ms)
    _cache_status.set(cache_status)


def reset_call_telemetry() -> None:
    """Clear per-call telemetry. Tools that fan out to several upstream calls
    should call this before the first to avoid echoing stale values."""
    _elapsed_ms.set(None)
    _cache_status.set(None)


def get_call_telemetry() -> tuple[float | None, CacheStatus | None]:
    """Return the (elapsed_ms, cache_status) recorded for the current call."""
    return _elapsed_ms.get(), _cache_status.get()
