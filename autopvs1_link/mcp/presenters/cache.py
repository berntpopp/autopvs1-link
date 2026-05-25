"""MCP cache statistics resource presenter."""

from __future__ import annotations

from typing import Any

from autopvs1_link.mcp.contracts import CacheStatBlock, CacheStatisticsResource

CACHE_STAT_METHODS: dict[str, dict[str, str]] = {
    "get_variant_data": {
        "cache_key_shape": "variant:{genome_build}:{variant_id}",
        "description": "Direct variant scoring by genome_build and variant_id.",
    },
    "get_cnv_data": {
        "cache_key_shape": "cnv:{genome_build}:{cnv_id}",
        "description": "Direct CNV scoring by genome_build and cnv_id.",
    },
    "search_variants": {
        "cache_key_shape": "search:{query}:{genome_build}",
        "description": "Search by normalized query and genome_build.",
    },
    "search_with_redirect_detection": {
        "cache_key_shape": "enhanced_search:{query}:{genome_build}",
        "description": "Enhanced search and HGVS redirect path used by REST or future MCP tools.",
    },
    "resolve_hgvs_notation": {
        "cache_key_shape": "hgvs:{hgvs}:{genome_build}",
        "description": "HGVS resolution path used by REST or future MCP tools.",
    },
}


def _block(method_name: str, raw: dict[str, Any] | None) -> CacheStatBlock:
    metadata = CACHE_STAT_METHODS[method_name]
    raw = raw or {}
    return CacheStatBlock(
        hits=int(raw.get("hits", 0)),
        misses=int(raw.get("misses", 0)),
        errors=int(raw.get("errors", 0)),
        evictions=int(raw.get("evictions", 0)),
        total_requests=int(raw.get("total_requests", 0)),
        hit_rate=float(raw.get("hit_rate", 0.0)),
        average_time_ms=float(raw.get("average_time_ms", 0.0)),
        last_hit=raw.get("last_hit"),
        last_miss=raw.get("last_miss"),
        uptime_seconds=float(raw.get("uptime_seconds", 0.0)),
        cache_key_shape=metadata["cache_key_shape"],
        description=metadata["description"],
    )


def present_cache_statistics(raw_statistics: dict[str, Any]) -> CacheStatisticsResource:
    """Return stable method-keyed cache statistics for the MCP resource."""
    return CacheStatisticsResource(
        statistics={
            method_name: _block(method_name, raw_statistics.get(method_name))
            for method_name in CACHE_STAT_METHODS
        }
    )
