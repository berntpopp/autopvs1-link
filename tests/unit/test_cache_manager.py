"""Tests for AdvancedCacheManager / CacheStatistics."""

import asyncio
import time

import pytest

from autopvs1_link.mcp.telemetry import get_call_telemetry, reset_call_telemetry
from autopvs1_link.utils.cache_manager import AdvancedCacheManager, CacheStatistics


def test_statistics_defaults() -> None:
    s = CacheStatistics()
    assert s.hits == 0
    assert s.misses == 0
    assert s.total_requests == 0
    assert s.hit_rate == 0.0
    assert s.average_time == 0.0


def test_statistics_to_dict() -> None:
    s = CacheStatistics(hits=8, misses=2, total_time=1.0)
    d = s.to_dict()
    assert d["hits"] == 8
    assert d["misses"] == 2
    assert d["total_requests"] == 10
    assert d["hit_rate"] == 0.8
    assert d["average_time_ms"] == 100.0
    assert "uptime_seconds" in d


def test_manager_get_statistics_unknown_method() -> None:
    m = AdvancedCacheManager()
    out = m.get_statistics("nonexistent")
    assert out == {"nonexistent": {"error": "Method not found"}}


def test_manager_get_statistics_all_initially_empty() -> None:
    m = AdvancedCacheManager()
    assert m.get_statistics() == {}


def test_manager_clear_statistics_method() -> None:
    m = AdvancedCacheManager()
    # Touch the dict via direct access to populate it.
    m._statistics["foo"]
    assert "foo" in m.get_statistics()
    m.clear_statistics("foo")
    # Cleared entry resets to a fresh CacheStatistics, still present.
    assert m.get_statistics("foo")["foo"]["hits"] == 0


def test_statistics_with_recent_events() -> None:
    s = CacheStatistics(hits=1, misses=0, last_hit=time.time())
    assert s.last_hit is not None


@pytest.mark.asyncio
async def test_cache_error_increments_errors_without_miss() -> None:
    manager = AdvancedCacheManager()

    @manager.enhanced_cache(key_func=lambda value: f"flaky:{value}")
    async def flaky(value: str) -> str:
        raise RuntimeError(f"boom {value}")

    with pytest.raises(RuntimeError, match="boom x"):
        await flaky("x")

    stats = manager.get_statistics("flaky")["flaky"]
    assert stats["errors"] == 1
    assert stats["misses"] == 0
    assert stats["hits"] == 0
    assert stats["total_requests"] == 0


@pytest.mark.asyncio
async def test_concurrent_same_key_callers_distinguish_miss_from_coalesced() -> None:
    """Two concurrent same-key callers MUST report distinct cache_status values.

    Failure mode addressed: external LLM tester observed concurrent
    ``search_variants`` calls reporting ``cache_status:"hit"`` with
    ``elapsed_ms`` over 5 seconds. The waiter inherited async_lru's
    coalesced future and the wrapper saw ``cache_info.hits++`` so it
    labelled the result a hit even though the call waited multi-seconds
    for someone else's miss. The honest answer is a third status:
    ``coalesced``. The first caller (which actually drives the upstream
    work) reports ``miss``; concurrent latecomers that joined the
    in-flight call report ``coalesced``; later callers that arrive after
    the value is cached report ``hit``.

    The underlying coroutine runs exactly once (``call_count == 1``),
    proving async_lru's coalescing is preserved and we are not double-
    fetching.
    """
    manager = AdvancedCacheManager()
    call_count = 0

    @manager.enhanced_cache(key_func=lambda value: f"slow:{value}")
    async def slow(value: str) -> str:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return f"v:{value}"

    async def caller() -> tuple[float | None, str | None]:
        reset_call_telemetry()
        await slow("x")
        return get_call_telemetry()

    first, second = await asyncio.gather(caller(), caller())
    statuses = sorted([first[1], second[1]])
    assert call_count == 1, "alru_cache must coalesce concurrent same-key calls"
    assert statuses == ["coalesced", "miss"]

    # And a follow-up call after the cache is populated reports a true hit.
    reset_call_telemetry()
    await slow("x")
    _, status_after = get_call_telemetry()
    assert status_after == "hit"
    assert call_count == 1, "true hits must not re-enter the underlying coroutine"


@pytest.mark.asyncio
async def test_distinct_keys_are_independent_misses() -> None:
    """Concurrent calls on DIFFERENT keys are independent misses, not coalesced.

    Sanity check: the coalesce tracker must be keyed on the cache_key, not
    on the method name. Otherwise distinct-key concurrent calls would
    incorrectly report as ``coalesced``.
    """
    manager = AdvancedCacheManager()

    @manager.enhanced_cache(key_func=lambda value: f"keyed:{value}")
    async def slow(value: str) -> str:
        await asyncio.sleep(0.05)
        return f"v:{value}"

    async def caller(value: str) -> tuple[float | None, str | None]:
        reset_call_telemetry()
        await slow(value)
        return get_call_telemetry()

    first, second = await asyncio.gather(caller("a"), caller("b"))
    assert first[1] == "miss"
    assert second[1] == "miss"


@pytest.mark.asyncio
async def test_populator_exception_clears_inflight_marker() -> None:
    """If the populator raises, the inflight marker must clear so the next
    caller can re-attempt instead of waiting forever or being mis-labelled."""
    manager = AdvancedCacheManager()
    attempts = 0

    @manager.enhanced_cache(key_func=lambda value: f"explode:{value}")
    async def explode(value: str) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("first attempt fails")
        return f"v:{value}"

    with pytest.raises(RuntimeError, match="first attempt fails"):
        await explode("x")

    # Second attempt must NOT be coalesced (no live in-flight call) and must
    # NOT be a hit (cache is empty after the exception).
    reset_call_telemetry()
    result = await explode("x")
    assert result == "v:x"
    _, status = get_call_telemetry()
    assert status == "miss"
