"""Tests for cache route registration."""

from __future__ import annotations


def test_cache_router_exposes_stats_and_clear_routes() -> None:
    from autopvs1_link.api.routes import cache

    paths = {route.path for route in cache.router.routes}

    assert "/api/cache/stats" in paths
    assert "/api/cache/clear" in paths
