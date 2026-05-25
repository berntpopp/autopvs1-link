"""Tests for stable MCP cache statistics resource presentation."""

from autopvs1_link.mcp.presenters.cache import CACHE_STAT_METHODS, present_cache_statistics

EXPECTED_CACHE_STAT_KEYS = {
    "get_variant_data",
    "get_cnv_data",
    "search_variants",
    "search_with_redirect_detection",
    "resolve_hgvs_notation",
}


def test_present_cache_statistics_includes_all_configured_keys_when_empty() -> None:
    resource = present_cache_statistics({})

    assert set(resource.statistics) == EXPECTED_CACHE_STAT_KEYS
    assert set(CACHE_STAT_METHODS) == EXPECTED_CACHE_STAT_KEYS
    for method_name, block in resource.statistics.items():
        assert block.hits == 0
        assert block.misses == 0
        assert block.errors == 0
        assert block.total_requests == 0
        assert block.cache_key_shape == CACHE_STAT_METHODS[method_name]["cache_key_shape"]
        assert block.description == CACHE_STAT_METHODS[method_name]["description"]


def test_present_cache_statistics_merges_raw_counters() -> None:
    resource = present_cache_statistics(
        {
            "get_variant_data": {
                "hits": 3,
                "misses": 2,
                "errors": 1,
                "evictions": 0,
                "total_requests": 5,
                "hit_rate": 0.6,
                "average_time_ms": 12.5,
                "last_hit": 100.0,
                "last_miss": 90.0,
                "uptime_seconds": 30.0,
            }
        }
    )

    block = resource.statistics["get_variant_data"]
    assert block.hits == 3
    assert block.misses == 2
    assert block.errors == 1
    assert block.hit_rate == 0.6
    assert block.cache_key_shape == "variant:{genome_build}:{variant_id}"
