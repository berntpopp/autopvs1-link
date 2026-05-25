"""Tests for AdvancedCacheManager / CacheStatistics."""

import time

import pytest

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
